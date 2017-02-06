import datetime
import os
import shutil
import sys
import time
from traceback import format_exception

from slack_simbot.msg_handle import MsgHandle
from slack_simbot.exception_guard import guard
from scp import SCPClient


class RunningAverage:
    def __init__(self, initial=None, weight=0.8):
        self.value = initial
        self.weight = weight

    def update(self, value):
        if self.value is None:
            self.value = value
        else:
            self.value = ((1-self.weight) * self.value + self.weight * value)
        return self.value

    def reset(self):
        self.value = None


class BatchMsgHandle(MsgHandle):
    COMPLETED = 0
    CANCELLED = 1
    EXCEPTION = 2

    def __init__(self, simbot, title, n_cases, result_dir, description, *, channel=None, clear_result_dir=True):
        self.simbot = simbot
        self.debug = simbot.debug
        self.channel = channel or self.simbot.default_channel
        self.title = title
        self.n_cases = n_cases
        self.result_dir = result_dir
        self.start_time = datetime.datetime.now()
        self.done = 0
        self.running = True
        self.cases = []
        self.eta = None
        self.last_update_time = None
        self.case_dt = RunningAverage()
        self.description = description

        r = self.start(clear_result_dir=clear_result_dir)
        super().__init__(r['ts'], r['channel'])

    @guard
    def start(self, clear_result_dir=True):
        # Clear the results directory if necessary by deleting and recreating it.
        if clear_result_dir and self.result_dir is not None:
            result_dir = os.path.abspath(self.result_dir)
            if os.path.isdir(self.result_dir):
                shutil.rmtree(self.result_dir)
            os.mkdir(self.result_dir)

        # Send msg to slack
        r = self.simbot.slack_client.api_call(
            "chat.postMessage",
            channel=self.channel,
            text="Starting simulation batch '{}' with {} {}.".format(
                self.title, self.n_cases, "case" if self.n_cases == 1 else "cases"
            ),
            as_user="1",
            parse="full",
            link_names="1"
        )
        return r

    @guard
    def update(self, case_name, update_slack=True):
        self.cases.append(case_name)
        now = datetime.datetime.now()

        if self.last_update_time is not None:
            dt = now - self.last_update_time
            dt = self.case_dt.update(dt)
            self.eta = now + dt * (self.n_cases - len(self.cases) + 1)

        self.last_update_time = now

        if len(self.cases) <= self.n_cases:
            text = "*running* {}\n*progress* {}/{}\n*eta* {}".format(
                            self.cases[-1],
                            len(self.cases),
                            self.n_cases,
                            "tbd" if self.eta is None else self.eta.strftime("%d-%b-%Y %H:%M:%S")
                        )
        else:
            text = "*done*"

        text = "_{}_\n".format(self.description) + text

        self.simbot.slack_client.api_call(
            "chat.update",
            ts=self.ts,
            channel=self.channel,
            # text=msg,
            parse="full",
            link_names="1",
            as_user="1",
            attachments=[
                {
                    "fallback": text,
                    "color": "#3AA3E3",
                    "title": self.title,
                    "text": text,
                    "mrkdwn_in": ["text"]
                }
            ]
        )


    @guard
    def update_done(self):
        text = "_{}_\n*Done*\nPostprocessing and uploading results".format(
            self.description)

        self.simbot.slack_client.api_call(
            "chat.update",
            ts=self.ts,
            channel=self.channel,
            # text=msg,
            parse="full",
            link_names="1",
            as_user="1",
            attachments=[
                {
                    "fallback": text,
                    "color": "#3AA3E3",
                    "title": self.title,
                    "text": text,
                    "mrkdwn_in": ["text"]
                }
            ]
        )

    @guard
    def finish(self,
               succesfull,
               status=None,
               exc_info=None,
               remote_path="/var/www/html/data",
               url="http://daresim.tk/data"):
        self.update_done()

        status = status or self.COMPLETED

        # Compress the target directory.
        if self.result_dir is not None:
            self.simbot.connect_ssh()
            zip_path = self.simbot.compress_directory(self.result_dir)

            # Generate the name the file will have on the server.
            _, dir_name = os.path.split(self.result_dir)
            remote_file_name = "{}_{}.zip".format(
                self.title.lower().replace(" ", "_"),
                datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))

            # Generate the full path of the file on the server
            remote_path = os.path.join(remote_path, remote_file_name)

            # Generate url pointing to the file.
            url = "{}/{}".format(url, remote_file_name)

            # Upload file to server
            with SCPClient(self.simbot.ssh_client.get_transport()) as scp:
                scp.put(zip_path, remote_path)
        else:
            url = ""

        if len(self.cases) > 7:
            cases_text = ", ".join([x.strip() for x in self.cases[0:3]]) + ", ... ," + \
                    ", ".join([x.strip() for x in self.cases[-3:]])
        else:
            cases_text = ", ".join([x.strip() for x in self.cases])

        successful_text = "{} out of {}".format(succesfull, self.n_cases)

        fields = [
            {
                "title": self.title,
                "value": self.description,
                "short": False
            },
            {
                "title": "Successful",
                "value": successful_text,
                "short": True
            },
            {
                "title": "Cases",
                "value": cases_text,
                "short": True
            },

            {
                "title": "Download",
                "value": url,
                "short": False
            } if self.result_dir is not None else {},
        ]

        if succesfull == self.n_cases:
            color = "good"  # green
        elif succesfull > 0:
            color = "warning"  # orange
        else:
            color = "danger"  # danger

        if status == self.COMPLETED:
            attachment_title = "Simulation batch completed"
        elif status == self.CANCELLED:
            attachment_title = "Simulation batch cancelled"
            color = ""
        else:
            attachment_title = "Error while running the simulation batch"
            color = "danger"
            if exc_info is not None:
                fields.append({
                    "title": "Exception",
                    "value": "```{}```".format("".join(format_exception(*exc_info))),
                    "short": False
                })

        # Delete the old msg
        self.simbot.delete_msg(self)

        # Send notification on slack
        r = self.simbot.slack_client.api_call(
            "chat.postMessage",
            channel=self.channel,
            text="@channel",
            as_user="1",
            parse="full",
            link_names="1",
            attachments=[
                {
                    "fallback": self.title,
                    "color": color,
                    "title": attachment_title,
                    # "text": "*{}* {}".format(self.title, self.description),
                    "fields": fields,
                    "mrkdwn_in": ["text", 'fields']
                }
            ]
        )

        if r['ok']:
            self.ts = r['ts']
            self.channel = r['channel']

