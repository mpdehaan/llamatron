# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Glide row, a toggle drawn with the dot like Tie: the dot was chosen over a bar into the next step, since the bar didn't read well."""

from llamatron.tui import keybindings
from llamatron.tui.components.toggle_row import ToggleRow


class GlideRow(ToggleRow):
    """Space toggles the glide, and Bksp turns it off, on a step with a note."""

    KEYS = keybindings.GlideRow

    __slots__ = ()
