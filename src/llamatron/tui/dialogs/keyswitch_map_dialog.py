# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""An instrument's Keyswitch Map: ten slots, numbered from 0, each with a name and the note that switches it.

Up and Down move through the slots and down to the OK and CANCEL buttons. On a slot, N names it,
Bksp empties it, and Enter opens the note picker, drawn over the map two cells down and to the
right as every flyout is: one octave of keys, with the octave picked apart from the key. The
picker opens on the slot's note, or, for a slot with none, a half step above the map's highest
note, or on the lowest C for an empty map. Nothing changes in the set until OK.
"""

from rich.text import Text

from llamatron.model.objects import instrument
from llamatron.model.objects.instrument import Keyswitch
from llamatron.model.values import midi
from llamatron.model.vocabulary import file_format, limits
from llamatron.tui import drawing, key_table, keybindings, keyswitch_text
from llamatron.tui.components.button_row import button_row
from llamatron.tui.components.keyboard import KeyKind, one_octave_rows
from llamatron.tui.cursor import Cursor
from llamatron.tui.dialogs.dialog import Dialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.drawing import cursor_mark, fit, legend, Style
from llamatron.tui.key_table import cursor_moved
from llamatron.tui.keys import Key
from llamatron.tui.keyswitch_text import keyswitch_note_text, shown_name
from llamatron.user_strings import labels, marks, messages

# The place of the row of buttons, under the last slot, and the buttons' places in the order of MSG_OK_CANCEL_BUTTONS.
BUTTONS_PLACE = file_format.KEYSWITCH_SLOT_COUNT
OK = 0
CANCEL = 1
BUTTON_BINDINGS = (keybindings.KeyswitchMapDialog.OK, keybindings.KeyswitchMapDialog.CANCEL)
# The styles of the picker's keys: the key picked filled in the Chord dialog's green, the rest dim.
KEY_STYLES = {KeyKind.CHORD: Style.CHORD_KEY, KeyKind.OUTSIDE: Style.DIM}
ONE_HALF_STEP = 1
# Where the cursor is along a slot's row: on the name, where Enter renames, or on the note, where Enter opens the note picker; the slot's number is only text at the left.
NAME_CELL = 0
NOTE_CELL = 1
SPACE = ' '


def first_note_offered(keyswitches):
    """Return the note the picker opens on for a slot with none: a half step above the map's highest note, or the lowest C for an empty map."""
    notes = [keyswitch.note for keyswitch in keyswitches if keyswitch.note is not None]
    return min(max(notes) + ONE_HALF_STEP, midi.MAX_MIDI_NUMBER) if notes else midi.MIN_MIDI_NUMBER


class KeyswitchMapDialog(Dialog):
    """Answers with the ten slots as Keyswitches, in order, or None when cancelled."""

    KEYS = keybindings.KeyswitchMapDialog

    def __init__(self, *, title, keyswitches, setlist):
        super().__init__()
        self.title = title
        self.keyswitches = list(keyswitches)
        # The set, whose octave labels the notes are written in.
        self.setlist = setlist
        self.cursor = Cursor(place=0)
        self.cell = NAME_CELL
        self.button = OK
        # The note the picker is on while it is open, and None while it is closed.
        self.picking = None

    def on_buttons(self):
        return self.cursor.get_place() == BUTTONS_PLACE

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
            self.bind(self.KEYS.MOVE, action=self.move_cursor, wants_key=True),
            self.bind(self.KEYS.OK, action=self.finish),
        ]
        if self.on_buttons():
            return [*shared, self.bind(self.KEYS.ALONG_BUTTONS, action=self.along_buttons, wants_key=True), self.bind(self.KEYS.PRESS, action=self.press_button)]
        enter = self.bind(self.KEYS.RENAME_HERE, action=self.rename) if self.cell == NAME_CELL else self.bind(self.KEYS.NOTE, action=self.open_picker)
        return [
            *shared,
            self.bind(self.KEYS.TO_NOTE, action=lambda: self.go_to_cell(NOTE_CELL)) if self.cell == NAME_CELL else self.bind(self.KEYS.TO_NAME, action=lambda: self.go_to_cell(NAME_CELL)),
            self.bind(self.KEYS.RENAME, action=self.rename),
            enter,
            self.bind(self.KEYS.CLEAR, action=self.clear),
        ]

    def finish(self):
        self.dismiss(list(self.keyswitches))

    def move_cursor(self, name):
        self.cursor.move(name=name, count=BUTTONS_PLACE + 1)

    def go_to_cell(self, cell):
        """Move to a slot's name or its note; Up and Down keep the place."""
        self.cell = cell

    def along_buttons(self, name):
        self.button = cursor_moved(place=self.button, name=name, count=len(labels.MSG_OK_CANCEL_BUTTONS))

    def press_button(self):
        if self.button == OK:
            self.finish()
        else:
            self.dismiss(None)

    def current(self):
        return self.keyswitches[self.cursor.get_place()]

    def clear(self):
        self.keyswitches[self.cursor.get_place()] = instrument.NO_KEYSWITCH

    def rename(self):
        """Ask for the slot's name over the map, an empty answer leaving the slot without one."""
        place = self.cursor.get_place()

        def named(text):
            if text is not None:
                self.keyswitches[place] = Keyswitch(text.strip() or None, self.keyswitches[place].note)
            self.draw()
        self.app.push_screen(PromptDialog(title=messages.MSG_KEYSWITCH_NAME_PROMPT.format(slot=place), value=self.current().name or drawing.NOTHING, max_length=limits.MAX_NAME_LENGTH), named)

    def open_picker(self):
        note = self.current().note
        self.picking = first_note_offered(self.keyswitches) if note is None else note

    def close_picker(self):
        self.picking = None

    def take_note(self):
        self.keyswitches[self.cursor.get_place()] = Keyswitch(self.current().name, self.picking)
        self.picking = None

    def pick_note(self, name):
        """Move a key along, staying within the octave shown, since the octave is picked apart from the key."""
        within = self.picking % midi.HALF_STEPS_PER_OCTAVE
        moved = cursor_moved(place=within, name=name, count=midi.HALF_STEPS_PER_OCTAVE)
        self.picking = min(self.picking - within + moved, midi.MAX_MIDI_NUMBER)

    def pick_octave(self, name):
        """Up is an octave higher and Down an octave lower, stopping where MIDI's notes end."""
        moved = self.picking + midi.HALF_STEPS_PER_OCTAVE * (key_table.STEP_FORWARD if name == Key.UP else key_table.STEP_BACK)
        if midi.MIN_MIDI_NUMBER <= moved <= midi.MAX_MIDI_NUMBER:
            self.picking = moved

    def note_text(self, note):
        return marks.MSG_NONE_SHOWN if note is None else keyswitch_note_text(setlist=self.setlist, note=note)

    def slot_line(self, *, slot, width):
        keyswitch = self.keyswitches[slot]
        on_name = slot == self.cursor.get_place() and self.cell == NAME_CELL
        on_note = slot == self.cursor.get_place() and self.cell == NOTE_CELL
        # The triangle stands before the name or the note, in a place each keeps for it, so that nothing shifts as the cursor moves.
        line = Text(marks.MSG_KEYSWITCH_MAP_ROW.format(slot=slot), no_wrap=True)
        name_mark = cursor_mark(on_name)
        note_mark = cursor_mark(on_note)
        room = max(width - line.cell_len - len(name_mark) - len(note_mark) - keyswitch_text.KEYSWITCH_NOTE_WIDTH, 0)
        line.append(name_mark)
        line.append(fit(text=shown_name(keyswitch), width=room), style=Style.DIM if keyswitch.name is None else Style.PLAIN)
        line.append(note_mark)
        line.append(fit(text=marks.MSG_KEYSWITCH_NOTE_CELL.format(note=self.note_text(keyswitch.note)), width=keyswitch_text.KEYSWITCH_NOTE_WIDTH - len(marks.MSG_PICKER_MARK)), style=Style.DIM if keyswitch.note is None else Style.PLAIN)
        line.append(marks.MSG_PICKER_MARK, style=Style.DIM)
        return line

    def heading_line(self, width):
        """Return the headings over the slots' two cells, each over the place its cell starts."""
        gap = len(marks.MSG_KEYSWITCH_MAP_ROW.format(slot=0)) + len(cursor_mark(False))
        room = max(width - gap - len(cursor_mark(False)) - keyswitch_text.KEYSWITCH_NOTE_WIDTH, 0)
        line = Text(SPACE * gap, no_wrap=True)
        line.append(fit(text=labels.Column.NAME, width=room) + SPACE * len(cursor_mark(False)) + labels.Column.NOTE, style=Style.DIM)
        return line

    def lines(self, width):
        buttons = [(binding.name, label) for label, binding in zip(labels.MSG_OK_CANCEL_BUTTONS, BUTTON_BINDINGS)]
        return [
            self.heading_line(width),
            *[self.slot_line(slot=slot, width=width) for slot in range(file_format.KEYSWITCH_SLOT_COUNT)],
            Text(drawing.NOTHING), *button_row(buttons=buttons, selected=self.button if self.on_buttons() else None),
        ]

    def legend_lines(self, width):
        """Return the keys under the map, leaving out the two the buttons name; while the picker is open they are the picker's, which the picker lists itself."""
        return legend(keys=[item for item in self.keys() if item.shown], width=width)

    def flyout_lines(self, width):
        """Return the note picker's lines while it is open: the slot, one octave of keys with the key picked filled and named, the note and its octave, and the picker's keys."""
        if self.picking is None:
            return None
        keyswitch = self.current()
        title = messages.MSG_KEYSWITCH_NOTE_TITLE.format(slot=self.cursor.get_place()) if keyswitch.name is None else messages.MSG_KEYSWITCH_NOTE_NAMED_TITLE.format(slot=self.cursor.get_place(), name=keyswitch.name)
        lines = [Text(fit(text=title, width=width), style=Style.BOLD), Text(drawing.NOTHING)]
        for row in one_octave_rows(self.picking % midi.HALF_STEPS_PER_OCTAVE):
            line = Text(drawing.NOTHING, no_wrap=True)
            for text, kind in row:
                line.append(text, style=KEY_STYLES.get(kind, Style.PLAIN))
            lines.append(line)
        octave = self.setlist.shown_octave(self.picking // midi.HALF_STEPS_PER_OCTAVE)
        lines += [
            Text(drawing.NOTHING), Text(messages.MSG_KEYSWITCH_PICKED_NOTE.format(note=self.note_text(self.picking))), Text(messages.MSG_KEYSWITCH_PICKED_OCTAVE.format(octave=octave)),
            Text(drawing.NOTHING), *legend(keys=self.keys(), width=width),
        ]
        return lines
