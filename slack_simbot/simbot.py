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
from slack_simbot.slackbot_base import SlackBotBase


class SimBot(SlackBotBase):
    def __init__(self, default_channel="#sim_notifications", debug=False, active=True):
        super().__init__()

        token=os.environ["SIMBOT_TOKEN"],
        default_channel=default_channel,
        debug=debug,
        active=active


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
