# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Accent row, a toggle drawn with the dot: an accented step plays louder by the accent of the track that plays it."""

from llamatron.tui import keybindings
from llamatron.tui.components.toggle_row import ToggleRow


class AccentRow(ToggleRow):
    """Space toggles the accent, and Bksp turns it off, on a step with a note."""

    KEYS = keybindings.AccentRow

    __slots__ = ()
