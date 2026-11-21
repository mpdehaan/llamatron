# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The dialog that picks a step's keyswitches: the instrument's ten slots, numbered from 0, each on or off.

Up and Down move, Space turns the slot under the cursor on or off, and a digit turns its own slot
on or off wherever the cursor is. Enter is OK, answering with the slots picked, and Esc is CANCEL,
changing nothing; the two are drawn as buttons. Each slot shows the name and the note its
instrument gives it, where the instrument is known for certain, and a line above the slots names
the instrument or says why none is named. A slot with no note can still be picked: it plays
nothing until the instrument gives it one."""

from rich.text import Text

from llamatron.model.schema import file_format
from llamatron.tui import drawing, keybindings, keys as keys_values, keyswitch_text
from llamatron.tui.components.button_row import button_row
from llamatron.tui.dialogs.pick_many_dialog import PickManyDialog
from llamatron.tui.drawing import cursor_mark, fit, legend, Style
from llamatron.user_strings import labels, marks

# The OK button is the one Enter presses, so it is the one drawn selected.
OK = 0
BUTTON_BINDINGS = (keybindings.KeyswitchDialog.DONE, keybindings.KeyswitchDialog.CANCEL)


class KeyswitchDialog(PickManyDialog):
    """Answers with the slots picked, in order, an empty list for none, or None when cancelled."""

    KEYS = keybindings.KeyswitchDialog
    SHOWN = file_format.KEYSWITCH_SLOT_COUNT

    def __init__(self, *, title, heading, names, notes, picked):
        super().__init__(title=title, options=list(file_format.KEYSWITCH_SLOTS), names=names, picked=picked)
        # The line over the slots, the instrument's name or why none is named, and each slot's note as text, nothing where it has none.
        self.said = heading
        self.notes = notes

    def keys(self):
        return [*super().keys(), self.bind(self.KEYS.TOGGLE_SLOT, action=self.toggle_slot, wants_key=True)]

    def toggle_slot(self, name):
        """Turn the slot a digit names on or off, and put the cursor on it."""
        self.cursor.set_place(keys_values.DIGITS.index(name))
        self.toggle()

    def legend_lines(self, width):
        """Return the keys listed under the slots, leaving out OK and CANCEL, which the buttons name."""
        return legend(keys=[item for item in self.keys() if item.shown], width=width)

    def slot_line(self, *, slot, width):
        picked = slot in self.picked
        start = cursor_mark(slot == self.cursor.get_place()) + marks.MSG_KEYSWITCH_SLOT_ROW.format(slot=slot, toggle=marks.MSG_TOGGLE_ON if picked else marks.MSG_FIELD_TOGGLE_OFF)
        line = Text(start, style=Style.BOLD if picked else Style.PLAIN, no_wrap=True)
        line.append(fit(text=self.names[slot], width=max(width - len(start) - keyswitch_text.KEYSWITCH_NOTE_WIDTH, 0)), style=Style.PLAIN if self.notes[slot] or picked else Style.DIM)
        line.append(fit(text=self.notes[slot], width=keyswitch_text.KEYSWITCH_NOTE_WIDTH), style=Style.DIM)
        return line

    def lines(self, width):
        buttons = [(binding.name, label) for label, binding in zip(labels.MSG_OK_CANCEL_BUTTONS, BUTTON_BINDINGS)]
        return [
            Text(fit(text=self.said, width=width), style=Style.DIM), Text(drawing.NOTHING),
            *[self.slot_line(slot=slot, width=width) for slot in self.options],
            Text(drawing.NOTHING), *button_row(buttons=buttons, selected=OK),
        ]
