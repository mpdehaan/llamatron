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

"""The Keyswitch row of the pattern editor: which of its instrument's keyswitches a step's note is played with (the user's design).

A cell is blank for none and otherwise says how many are on. Enter opens the dialog that picks
them, the same one the piano roll opens, and Bksp clears them. A step with no note takes none.
"""

from llamatron.composition.file_format import Row
from llamatron.strings.marks import MSG_NONE_SHOWN
from llamatron.strings.messages import MSG_KEYSWITCH_DIALOG_TITLE
from llamatron.tui.components.pattern_row import PatternRow
from llamatron.tui.dialogs.keyswitch_dialog import KeyswitchDialog
from llamatron.tui.drawing import NOTHING
from llamatron.tui.keyswitch_text import keyswitch_note_text, keyswitches_of
from llamatron.tui import keybindings


def pick_keyswitches(*, editor, step):
    """Open the dialog that picks a step's keyswitches on a step of the pattern editor, and store what it answers on the step's Keyswitch row: the Keyswitch row's Enter and the roll's keyswitch key."""
    instrument, said = editor.keyswitch_instrument()
    setlist = editor.document().setlist()
    keyswitches = keyswitches_of(instrument)
    dialog = KeyswitchDialog(
        title=MSG_KEYSWITCH_DIALOG_TITLE.format(step=step + 1), heading=said,
        names=[MSG_NONE_SHOWN if keyswitch.name is None else keyswitch.name for keyswitch in keyswitches],
        notes=[NOTHING if keyswitch.note is None else keyswitch_note_text(setlist=setlist, note=keyswitch.note) for keyswitch in keyswitches],
        picked=editor.value(row=Row.KEYSWITCH, step=step) or (),
    )
    editor.ask(dialog=dialog, then=lambda slots: editor.set_value(value=slots or None, row=Row.KEYSWITCH, step=step))


class KeyswitchRow(PatternRow):
    """Enter opens the dialog that picks the step's keyswitches, and Bksp clears them."""

    KEYS = keybindings.KeyswitchRow

    __slots__ = ()

    def keys(self):
        return [
            self.bind(self.KEYS.CHOOSE, action=lambda: pick_keyswitches(editor=self.editor, step=self.editor.step)),
            self.bind(self.KEYS.CLEAR, action=lambda: self.set_value(None)),
        ]

    def cell_text(self, *, step):
        value = self.value(step=step)
        return NOTHING if not value else str(len(value))
