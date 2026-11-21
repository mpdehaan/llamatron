# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The two kinds of step a tutorial's plan yields: one key pressed, or one sentence said."""

from typing import NamedTuple


class Press(NamedTuple):
    """One key to press into the screen that is open, named as interface/tracker/keys.py names it, whether it types into a prompt, which goes twice as fast as other keys and is never called out, and what is called out as it is pressed, or None."""

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
