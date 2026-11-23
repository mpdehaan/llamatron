# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A tracker that raises an error nothing catches a moment after it opens, run headless, for the test of how a crash's traceback
is printed (tests/interface/tracker/test_tui_quitting.py). The error's message is the first argument."""

import sys

from llamatron.interface.tracker.app import LlamatronApp

# How long after opening the error is raised, in seconds.
CRASH_AFTER = 0.2


class CrashingTracker(LlamatronApp):
    """The tracker, raising an error a moment after it opens."""

    def on_mount(self):
        super().on_mount()
        self.set_timer(CRASH_AFTER, self.crash)

    def crash(self):
        raise RuntimeError(sys.argv[1])


if __name__ == '__main__':
    CrashingTracker().run(headless=True)
    sys.exit(1)
