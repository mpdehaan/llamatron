# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Slide row: a step that ramps its CC values to the next ones, which a rest can do too."""

from llamatron.tui import keybindings
from llamatron.tui.components.toggle_row import ToggleRow


class SlideRow(ToggleRow):
    """A toggle on every step, since the CC rows it ramps can be set on a rest."""

    KEYS = keybindings.SlideRow

    __slots__ = ()

    def on_rests(self):
        return True
