# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The visualizer's modes, in the order its key steps through them, and the clips come back after the last."""

from llamatron.visualizers import cycle
from llamatron.visualizers.cycle import Cycle

# Every mode the key steps through, the mode of modes last.
MODES = (*cycle.CYCLED, Cycle)


def mode_options():
    """Return each mode's name on the command line, in order."""
    return [mode.OPTION for mode in MODES]


def mode_called(option):
    """Return the mode the command line names, or None."""
    return next((mode for mode in MODES if mode.OPTION == option), None)
