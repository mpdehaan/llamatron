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
"""The visualizer's modes, in the order its key steps through them, and the clips come back after the last."""

from llamatron.visualizers.cycle import CYCLED, Cycle

# Every mode the key steps through, the mode of modes last.
MODES = (*CYCLED, Cycle)


def mode_options():
    """Return each mode's name on the command line, in order."""
    return [mode.OPTION for mode in MODES]


def mode_called(option):
    """Return the mode the command line names, or None."""
    return next((mode for mode in MODES if mode.OPTION == option), None)
