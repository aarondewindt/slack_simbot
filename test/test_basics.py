import unittest
from time import sleep
import sys

from slack_simbot import SimBot


class TestBasics(unittest.TestCase):
    def test_send_msg(self):
        simbot = SimBot(debug=True)
        simbot.send_msg("Hello")

    def test_name_parsing(self):
        simbot = SimBot(debug=True)
        simbot.send_msg("Sup @adewindt")

    def test_batch(self):
        simbot = SimBot(debug=True)

        cases = ["case_{}".format(i) for i in range(2)]

        slack_batch = simbot.start_batch("Random test batch", len(cases),
                                         "This is a random batch of cases used to test the simulations slack bot.",
                                         result_dir="test_dir",
                                         clear_result_dir=False)

        try:
            for i, case in enumerate(cases):
                slack_batch.update(case)
                sleep(1)
                # if i == 6:
                #     raise Exception("Random exception")
        except KeyboardInterrupt:
            slack_batch.finish(3, slack_batch.CANCELLED)
        except:
            slack_batch.finish(3, slack_batch.EXCEPTION, sys.exc_info())
        else:
            slack_batch.finish(6)

    def test_long_term_update(self):
        from time import sleep
        import datetime
        simbot = SimBot(debug=True)

        msg_handle = simbot.send_msg("This is a test")

        def qwerty():
            i = 0
            while True:
                yield i

        t0 = datetime.datetime.now()
        r = None
        for i in qwerty():
            sleep(3)
            a = "Update {} {}".format(i, datetime.datetime.now() - t0)
            print(a)
            r = simbot.update_msg(msg_handle, a)
            if not r['ok']:
                break
        print(t0)
        print(datetime.datetime.now())
        print(datetime.datetime.now() - t0)
        print(r)
