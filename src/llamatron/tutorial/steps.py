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

"""The two kinds of step a tutorial's plan yields: one key pressed, or one sentence said."""

from typing import NamedTuple


class Press(NamedTuple):
    """One key to press into the screen that is open, named as tui/keys.py names it, whether it types into a prompt, which goes twice as fast as other keys and is never called out, and what is called out as it is pressed, or None."""

    key: str
    in_dialog: bool = False
    called: str = None


class Gap(NamedTuple):
    """An empty caption, which sets what follows apart, with no pause of its own."""


class Wait(NamedTuple):
    """Wait until something is true, asked again and again, and then some seconds more when the tutorial has a pace, as after the song has played."""

    until: object
    seconds: float = 0.0


class Say(NamedTuple):
    """One sentence to say at this point of the build, for a caption."""

    text: str
