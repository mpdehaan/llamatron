# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Tie row: a toggle on the empty steps after a note, each tied step marked like any toggle that's on.

A tie is stored only on an empty step, which holds the note before it to the step's end. The
plain toggle mark was chosen over a bar running through the dividers, which read
badly and broke the beat lines. A note's own step can't take a tie, so its cell is blocked
like any cell that can't take a value: a note never draws a tie
of its own, since ties are optional and only ever added on the steps after a note, in place of a
longer gate.
"""

from llamatron.tui import keybindings
from llamatron.tui.components.toggle_row import ToggleRow


class TieRow(ToggleRow):
    """A toggle on empty steps only: a step with a note can't hold a tie, since a tie holds the note before it, so it's blocked there."""

    KEYS = keybindings.TieRow

    __slots__ = ()

    def on_rests(self):
        return True

    def blocked(self, *, step=None):
        return self.is_note(step=step)

    def tied(self, step):
        return 0 <= step < self.editor.step_count() and bool(self.value(step=step))
