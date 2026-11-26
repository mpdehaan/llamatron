# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later


"""Start the Realtime Sender Process with sys.stderr replaced, as Textual replaces it while the tracker runs, and print the word below.

tests/realtime/test_realtime.py runs this in an interpreter of its own, because spawn's resource tracker is started
once per interpreter, with sys.stderr's file descriptor passed to it, and only the first start in an
interpreter can fail the way the tracker's once did: Textual's capture answers -1 for its
file descriptor, and the spawn failed with "bad value(s) in fds_to_keep".
"""

import sys

from llamatron.realtime.sender_process.process import RealtimeMIDISenderProcess

STARTED = 'started'
INVALID_DESCRIPTOR = -1
PORT = 'a port'


class CaptureLikeTextuals:
    """What Textual puts in place of sys.stderr while an app runs: it writes nowhere useful and has no file descriptor."""

    __slots__ = ()

    def write(self, text):
        pass

    def flush(self):
        pass

    def fileno(self):
        return INVALID_DESCRIPTOR


def main():
    sys.stderr = CaptureLikeTextuals()
    sender = RealtimeMIDISenderProcess(ports=[PORT], recording=True)
    sender.start()
    started, _ = sender.close()
    print(STARTED if started is not None else repr(started))


if __name__ == '__main__':
    main()
