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

"""An instrument's Keyswitch Map, the user's design: ten slots, numbered from 0, each with a name and the note that switches it.

Up and Down move through the slots and down to the OK and CANCEL buttons. On a slot, N names it,
Bksp empties it, and Enter opens the note picker, drawn over the map two cells down and to the
right as every flyout is: one octave of keys, with the octave picked apart from the key. The
picker opens on the slot's note, or, for a slot with none, a half step above the map's highest
note, or on the lowest C for an empty map. Nothing changes in the set until OK.
"""

from rich.text import Text

from llamatron.composition.file_format import KEYSWITCH_SLOT_COUNT
from llamatron.composition.instrument import NO_KEYSWITCH, Keyswitch
from llamatron.composition.limits import MAX_NAME_LENGTH
from llamatron.music.midi import HALF_STEPS_PER_OCTAVE, MAX_MIDI_NUMBER, MIN_MIDI_NUMBER
from llamatron.strings.labels import MSG_OK_CANCEL_BUTTONS
from llamatron.strings.marks import MSG_KEYSWITCH_CELL_CLOSE, MSG_KEYSWITCH_CELL_OPEN, MSG_KEYSWITCH_MAP_ROW
from llamatron.strings.messages import (
    MSG_KEYSWITCH_NAME_PROMPT, MSG_KEYSWITCH_NOTE_NAMED_TITLE, MSG_KEYSWITCH_NOTE_TITLE, MSG_KEYSWITCH_PICKED_NOTE, MSG_KEYSWITCH_PICKED_OCTAVE,
)
from llamatron.tui.components.button_row import button_row
from llamatron.tui.components.keyboard import KeyKind, one_octave_rows
from llamatron.tui.dialogs.dialog import Dialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.drawing import NOTHING, Style, cursor_mark, fit, legend
from llamatron.tui.key_table import STEP_BACK, STEP_FORWARD, cursor_moved
from llamatron.tui.keys import Key
from llamatron.tui.keyswitch_text import KEYSWITCH_NOTE_WIDTH, keyswitch_note_text, shown_name
from llamatron.tui import keybindings

# The place of the row of buttons, under the last slot, and the buttons' places in the order of MSG_OK_CANCEL_BUTTONS.
BUTTONS_PLACE = KEYSWITCH_SLOT_COUNT
OK = 0
CANCEL = 1
BUTTON_BINDINGS = (keybindings.KeyswitchMapDialog.OK, keybindings.KeyswitchMapDialog.CANCEL)
# The styles of the picker's keys: the key picked filled in the Chord dialog's green, the rest dim.
KEY_STYLES = {KeyKind.CHORD: Style.CHORD_KEY, KeyKind.OUTSIDE: Style.DIM}
ONE_HALF_STEP = 1
# Where the cursor is along a slot's row, the user's design: on the whole row, where Enter opens the note picker, then with Right on the name, where Enter renames, then on the note.
WHOLE_ROW = 0
NAME_CELL = 1
NOTE_CELL = 2
CELL_COUNT = 3
SPACE = ' '


def first_note_offered(keyswitches):
    """Return the note the picker opens on for a slot with none: a half step above the map's highest note, or the lowest C for an empty map (the user's choice)."""
    notes = [keyswitch.note for keyswitch in keyswitches if keyswitch.note is not None]
    return min(max(notes) + ONE_HALF_STEP, MAX_MIDI_NUMBER) if notes else MIN_MIDI_NUMBER


class KeyswitchMapDialog(Dialog):
    """Answers with the ten slots as Keyswitches, in order, or None when cancelled."""

    KEYS = keybindings.KeyswitchMapDialog

    def __init__(self, *, title, keyswitches, setlist):
        super().__init__()
        self.title = title
        self.keyswitches = list(keyswitches)
        # The set, whose octave labels the notes are written in.
        self.setlist = setlist
        self.place = 0
        self.cell = WHOLE_ROW
        self.button = OK
        # The note the picker is on while it is open, and None while it is closed.
        self.picking = None

    def on_buttons(self):
        return self.place == BUTTONS_PLACE

    def keys(self):
        if self.picking is not None:
            return [
                self.bind(self.KEYS.CLOSE_PICKER, action=self.close_picker),
                self.bind(self.KEYS.PICK_NOTE, action=self.pick_note, wants_key=True),
                self.bind(self.KEYS.PICK_OCTAVE, action=self.pick_octave, wants_key=True),
                self.bind(self.KEYS.TAKE_NOTE, action=self.take_note),
            ]
        shared = [
            self.bind(self.KEYS.CANCEL, action=lambda: self.dismiss(None)),
            self.bind(self.KEYS.MOVE, action=self.move, wants_key=True),
            self.bind(self.KEYS.OK, action=self.finish),
        ]
        if self.on_buttons():
            return [*shared, self.bind(self.KEYS.ALONG_BUTTONS, action=self.along_buttons, wants_key=True), self.bind(self.KEYS.PRESS, action=self.press_button)]
        enter = self.bind(self.KEYS.RENAME_HERE, action=self.rename) if self.cell == NAME_CELL else self.bind(self.KEYS.NOTE, action=self.open_picker)
        return [
            *shared,
            self.bind(self.KEYS.ACROSS, action=self.across, wants_key=True),
            self.bind(self.KEYS.RENAME, action=self.rename),
            enter,
            self.bind(self.KEYS.CLEAR, action=self.clear),
        ]

    def finish(self):
        self.dismiss(list(self.keyswitches))

    def move(self, name):
        self.place = cursor_moved(place=self.place, name=name, count=BUTTONS_PLACE + 1)

    def across(self, name):
        """Move along a slot's row, from the whole row to its name and on to its note, stopping at both ends; Up and Down keep the place."""
        self.cell = cursor_moved(place=self.cell, name=name, count=CELL_COUNT)

    def along_buttons(self, name):
        self.button = cursor_moved(place=self.button, name=name, count=len(MSG_OK_CANCEL_BUTTONS))

    def press_button(self):
        if self.button == OK:
            self.finish()
        else:
            self.dismiss(None)

    def current(self):
        return self.keyswitches[self.place]

    def clear(self):
        self.keyswitches[self.place] = NO_KEYSWITCH

    def rename(self):
        """Ask for the slot's name over the map, an empty answer leaving the slot without one."""
        place = self.place

        def named(text):
            if text is not None:
                self.keyswitches[place] = Keyswitch(text.strip() or None, self.keyswitches[place].note)
            self.draw()
        self.app.push_screen(PromptDialog(title=MSG_KEYSWITCH_NAME_PROMPT.format(slot=place), value=self.current().name or NOTHING, max_length=MAX_NAME_LENGTH), named)

    def open_picker(self):
        note = self.current().note
        self.picking = first_note_offered(self.keyswitches) if note is None else note

    def close_picker(self):
        self.picking = None

    def take_note(self):
        self.keyswitches[self.place] = Keyswitch(self.current().name, self.picking)
        self.picking = None

    def pick_note(self, name):
        """Move a key along, staying within the octave shown, the user's design of an octave picked apart from the key."""
        within = self.picking % HALF_STEPS_PER_OCTAVE
        moved = cursor_moved(place=within, name=name, count=HALF_STEPS_PER_OCTAVE)
        self.picking = min(self.picking - within + moved, MAX_MIDI_NUMBER)

    def pick_octave(self, name):
        """Up is an octave higher and Down an octave lower, stopping where MIDI's notes end."""
        moved = self.picking + HALF_STEPS_PER_OCTAVE * (STEP_FORWARD if name == Key.UP else STEP_BACK)
        if MIN_MIDI_NUMBER <= moved <= MAX_MIDI_NUMBER:
            self.picking = moved

    def note_text(self, note):
        return NOTHING if note is None else keyswitch_note_text(setlist=self.setlist, note=note)

    def slot_line(self, *, slot, width):
        keyswitch = self.keyswitches[slot]
        start = cursor_mark(slot == self.place) + MSG_KEYSWITCH_MAP_ROW.format(slot=slot)
        line = Text(start, no_wrap=True)
        on_name = slot == self.place and self.cell == NAME_CELL
        on_note = slot == self.place and self.cell == NOTE_CELL
        # Each cell keeps a place before and after its text, a space or a bracket, so that nothing shifts as the cursor moves.
        room = max(width - len(start) - KEYSWITCH_NOTE_WIDTH - 2, 0)
        name = fit(text=shown_name(keyswitch), width=room).rstrip()
        line.append(MSG_KEYSWITCH_CELL_OPEN if on_name else SPACE, style=Style.BOLD)
        line.append(name, style=Style.DIM if keyswitch.name is None else Style.PLAIN)
        line.append(MSG_KEYSWITCH_CELL_CLOSE if on_name else SPACE, style=Style.BOLD)
        line.append(SPACE * (room - len(name)))
        note = fit(text=self.note_text(keyswitch.note), width=KEYSWITCH_NOTE_WIDTH - 2).rstrip()
        line.append(MSG_KEYSWITCH_CELL_OPEN if on_note else SPACE, style=Style.BOLD)
        line.append(note)
        line.append(MSG_KEYSWITCH_CELL_CLOSE if on_note else SPACE, style=Style.BOLD)
        return line

    def lines(self, width):
        buttons = [(binding[1], label) for label, binding in zip(MSG_OK_CANCEL_BUTTONS, BUTTON_BINDINGS)]
        return [
            *[self.slot_line(slot=slot, width=width) for slot in range(KEYSWITCH_SLOT_COUNT)],
            Text(NOTHING), *button_row(buttons=buttons, selected=self.button if self.on_buttons() else None),
        ]

    def legend_lines(self, width):
        """Return the keys under the map, leaving out the two the buttons name; while the picker is open they are the picker's, which the picker lists itself."""
        return legend(keys=[item for item in self.keys() if item.shown], width=width)

    def flyout_lines(self, width):
        """Return the note picker's lines while it is open: the slot, one octave of keys with the key picked filled and named, the note and its octave, and the picker's keys."""
        if self.picking is None:
            return None
        keyswitch = self.current()
        title = MSG_KEYSWITCH_NOTE_TITLE.format(slot=self.place) if keyswitch.name is None else MSG_KEYSWITCH_NOTE_NAMED_TITLE.format(slot=self.place, name=keyswitch.name)
        lines = [Text(fit(text=title, width=width), style=Style.BOLD), Text(NOTHING)]
        for row in one_octave_rows(self.picking % HALF_STEPS_PER_OCTAVE):
            line = Text(NOTHING, no_wrap=True)
            for text, kind in row:
                line.append(text, style=KEY_STYLES.get(kind, Style.PLAIN))
            lines.append(line)
        octave = self.setlist.shown_octave(self.picking // HALF_STEPS_PER_OCTAVE)
        lines += [
            Text(NOTHING), Text(MSG_KEYSWITCH_PICKED_NOTE.format(note=self.note_text(self.picking))), Text(MSG_KEYSWITCH_PICKED_OCTAVE.format(octave=octave)),
            Text(NOTHING), *legend(keys=self.keys(), width=width),
        ]
        return lines
