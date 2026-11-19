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

"""The Keyswitch row of the pattern editor: which of its instrument's keyswitches a step's note is played with.

A cell is blank for none and otherwise says how many are on. Enter opens the dialog that picks
them, the same one the piano roll opens, and Bksp clears them. A step with no note takes none.
"""

from llamatron.composition.file_format import Row
from llamatron.strings import marks, messages
from llamatron.composition import instrument as instrument_values
from llamatron.tui.components.toggle_row import ToggleRow
from llamatron.tui.dialogs.keyswitch_dialog import KeyswitchDialog
from llamatron.tui.drawing import NOTHING
from llamatron.tui.keyswitch_text import keyswitch_note_text, keyswitches_of, slot_name
from llamatron.tui import keybindings

# What the rows view calls the row of one slot.
SLOT_ROW_NAME = 'keyswitch slot {slot}'


def pick_keyswitches(*, editor, step):
    """Open the dialog that picks a step's keyswitches on a step of the pattern editor, and store what it answers on the step's Keyswitch row: the roll's keyswitch key."""
    instrument, said = editor.keyswitch_instrument()
    setlist = editor.document().setlist()
    keyswitches = keyswitches_of(instrument)
    dialog = KeyswitchDialog(
        title=messages.MSG_KEYSWITCH_DIALOG_TITLE.format(step=step + 1), heading=said,
        names=[marks.MSG_NONE_SHOWN if keyswitch.name is None else keyswitch.name for keyswitch in keyswitches],
        notes=[NOTHING if keyswitch.note is None else keyswitch_note_text(setlist=setlist, note=keyswitch.note) for keyswitch in keyswitches],
        picked=editor.value(row=Row.KEYSWITCH, step=step) or (),
    )
    editor.ask(dialog=dialog, then=lambda slots: editor.set_value(value=slots or None, row=Row.KEYSWITCH, step=step))


def slot_row_name(slot):
    """Return what the rows view calls a slot's row, which is no row of a pattern's file: every slot's row reads and writes the one Keyswitch row."""
    return SLOT_ROW_NAME.format(slot=slot)


def slot_rows(editor):
    """Return the slots the Keyswitch section has a row for, and the hint that says where they come from.

    When one instrument is known to play the pattern, the slots are those its Keyswitch Map
    gives a name or a note, and any other slot a step already uses. Otherwise only the slots
    the steps use, by number, and the hint says why.
    """
    instrument, said = editor.keyswitch_instrument()
    used = {slot for step in range(editor.pattern().get_steps()) for slot in editor.value(row=Row.KEYSWITCH, step=step) or ()}
    if instrument is None:
        return sorted(used), said
    mapped = {slot for slot, keyswitch in enumerate(instrument.get_keyswitches()) if keyswitch != instrument_values.NO_KEYSWITCH}
    return sorted(mapped | used), messages.MSG_KEYSWITCH_SECTION_HINT.format(instrument=said)


class KeyswitchSlotRow(ToggleRow):
    """One slot's row in the Keyswitch section: a dot on each step that plays its note with the slot's keyswitch, switched with Space or Enter.

    Its name is the Keyswitch row's, the one row of the file that holds every slot of a step,
    so that everything that asks the cursor's row reads that row.
    """

    KEYS = keybindings.KeyswitchSlotRow

    __slots__ = ('slot',)

    def __init__(self, *, editor, slot):
        super().__init__(editor=editor, name=Row.KEYSWITCH)
        self.slot = slot

    def label(self):
        return slot_name(keyswitches=keyswitches_of(self.editor.keyswitch_instrument()[0]), slot=self.slot)

    def value(self, *, step=None):
        return self.slot in (self.editor.value(row=Row.KEYSWITCH, step=step) or ())

    def set_value(self, value):
        slots = set(self.editor.value(row=Row.KEYSWITCH) or ())
        slots = slots | {self.slot} if value else slots - {self.slot}
        self.editor.set_value(value=sorted(slots) or None, row=Row.KEYSWITCH)
