# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A draw's Reset row in the Use Draws section: a step that sends the draw back to its start, or a serial draw to a new round, before it draws."""

from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.components.toggle_row import ToggleRow


class DrawResetRow(ToggleRow):
    """A toggle on every step, since a step with no note can reset a draw for the steps after it."""

    KEYS = keybindings.DrawResetRow

    __slots__ = ()

    def on_rests(self):
        return True
