import os
import shutil
from collections import namedtuple
from contextlib import closing

from io import BytesIO
import zipfile

from slackclient import SlackClient
from scp import SCPClient

import paramiko
import paramiko.client

import datetime

import time


from slack_simbot.msg_handle import MsgHandle
from slack_simbot.batch_msg_handle import BatchMsgHandle
from slack_simbot.exception_guard import guard


class SimBot:
    def __init__(self, default_channel="#sim_notifications", debug=False, active=True):
        self.debug = debug
        self.token = os.environ.get('SIMBOT_TOKEN')
        self.default_channel = "#simbot_testing" if debug else default_channel
        self._active = active


        if self.token is None:
            print("Warning: No access to simbot.")

        self.slack_client = SlackClient(self.token)

        self.ssh_client = None

    @property
    def active(self):
        # return False
        return self.token is not None and self._active

    @guard
    def send_msg(self, msg, channel=None) -> MsgHandle:
        if self.active:
            channel = channel or self.default_channel
            r = self.slack_client.api_call(
                "chat.postMessage",
                channel=channel,
                text=msg,
                as_user="1",
                parse="full",
                link_names="1"
            )

            if r['ok']:
                return MsgHandle(r['ts'], r['channel'])
            else:
                return None

    @guard
    def update_msg(self, handle: MsgHandle, msg):
        if self.active:
            return self.slack_client.api_call(
                "chat.update",
                ts=handle.ts,
                channel=handle.channel,
                text=msg,
                parse="full",
                link_names="1",
                as_user="1",
            )

    @guard
    def delete_msg(self, handle: MsgHandle):
        if self.active:
            return self.slack_client.api_call(
                "chat.delete",
                channel=handle.channel,
                ts=handle.ts
            )

    @guard
    def get_channel_list(self):
        return self.slack_client.api_call("channels.list")

    @guard
    def connect_ssh(self, hostname="daresim.tk", username="daresimserver", key_filename=None, password=None):
        if self.active:
            try:
                if self.ssh_client is None:
                    ssh_client = paramiko.SSHClient()
                    ssh_client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
                    ssh_client.load_system_host_keys()
                    ssh_client.connect(hostname, username=username, key_filename=key_filename, password=password)
                    self.ssh_client = ssh_client
                return

            except paramiko.BadHostKeyException:
                pass
            except paramiko.AuthenticationException:
                pass
            except paramiko.SSHException:
                pass
            self.ssh_client = None

    @guard
    def compress_directory(self, dir_path):
        _, dir_name = os.path.split(dir_path)

        if os.path.isdir(dir_path):
            zip_path = os.path.abspath(os.path.join(dir_path, "../{}.zip".format(dir_name)))
            # Open zip file.
            with zipfile.ZipFile(zip_path, "w") as zf:
                # Walk through target directory
                for dir_name, sub_dirs, files in os.walk(dir_path):
                    # Path of this directory inside the zip file.
                    arc_dir_name = os.path.relpath(dir_name, os.path.normpath(os.path.join(dir_path, '..')))
                    try:
                        # Create directory inside zip file
                        zf.write(dir_name, arc_dir_name)
                        # Loop through all files in the directory and put them in the zip file.
                        for filename in files:
                            zf.write(os.path.join(dir_name, filename), os.path.join(arc_dir_name, filename))
                    except:
                        pass
            return zip_path
        else:
            return None

    @guard
    def upload_directory(self,
                         title,
                         description,
                         dir_path,
                         remote_path="/var/www/html/data",
                         url="http://daresim.tk/data"):
        self.connect_ssh()
        zip_path = self.compress_directory(dir_path)

        # Generate the name the file will have on the server.
        _, dir_name = os.path.split(dir_path)
        remote_file_name = "{}_{}.zip".format(
        dir_name,
        datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))

        # Generate the full path of the file on the server
        remote_path = os.path.join(remote_path, remote_file_name)

        # Generate url pointing to the file.
        url = "{}/{}".format(url, remote_file_name)

        # Upload file to server
        with SCPClient(self.ssh_client.get_transport()) as scp:
            scp.put(zip_path, remote_path)

        fields = [
            {
                "title": title,
                "value": description,
                "short": False
            },
            {
                "title": "Download",
                "value": url,
                "short": False
            },
        ]

        r = self.slack_client.api_call(
            "chat.postMessage",
            channel=self.default_channel,
            text="@channel",
            as_user="1",
            parse="full",
            link_names="1",
            attachments=[
                {
                    "fallback": title,
                    "color": "good",
                    "title": "Directory uploaded",
                    # "text": "*{}* {}".format(self.title, self.description),
                    "fields": fields,
                    "mrkdwn_in": ["text", 'fields']
                }
            ]
        )

        if r['ok']:
            return MsgHandle(r['ts'], r['channel'])
        else:
            return None


    @guard
    def start_batch(self, title, n_cases, description, *, result_dir=None, channel=None, clear_result_dir=True):
        return BatchMsgHandle(self, title, n_cases, result_dir, description, channel=channel,
                              clear_result_dir=clear_result_dir)


if __name__ == "__main__":
    pass
    # results = simbot.get_channel_list()

    # if results['ok']:
    #     for channel in results['channels']:
    #         for field in channel:
    #             print(field, channel[field])
    #         print()

    # result = simbot.slack_client.api_call(
    #     "channels.info",
    #     channel="C3RFFTJ9W"
    # )
    # print(result)

    # simbot.connect_ssh()
    # simbot.compress_and_upload_folder("test_dir")

    # handle = simbot.send_msg("Hello from Python! :tada:")

    # print(simbot.join_channel("C3RFFTJ9W"))

    # handle = MsgHandle(1484148469.000008, "C3Q69ER8U")
    #
    # print(handle)
    #
    # simbot.update_msg(handle, "Newer msg")
