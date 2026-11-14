# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


"""Start the Realtime Sender Process with sys.stderr replaced, as Textual replaces it while the tracker runs, and print the word below.

test/test_realtime.py runs this in an interpreter of its own, because spawn's resource tracker is started
once per interpreter, with sys.stderr's file descriptor passed to it, and only the first start in an
interpreter can fail the way the tracker's did on 2026-11-10: Textual's capture answers -1 for its
file descriptor, and the spawn failed with "bad value(s) in fds_to_keep".
"""

import sys

from llamatron.realtime.sender_process import RealtimeMIDISenderProcess

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
