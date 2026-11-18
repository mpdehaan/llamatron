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

"""The Tune dialog: one line of a tune, drawn a row a note with time going right, edited by hand.

Left and Right move along the line's steps and stop at its ends, Up and Down move the note under the
cursor a note of the scale up and down, Space takes the note under the cursor out or puts a note in
where there is none, [ and ] make the note shorter and longer, into the silence after it, Bksp puts
back the line the dialog was told is the usual one, Enter is OK, answering with the line, and Esc is
CANCEL, changing nothing.
"""

from rich.text import Text

from llamatron.macro_composer import line_edits
from llamatron.strings import labels, marks
from llamatron.tui.components.button_row import button_row
from llamatron.tui.dialogs.dialog import DIALOG_MARGIN, Dialog
from llamatron.tui.drawing import NOTHING, Style, legend
from llamatron.tui.key_table import STEP_BACK, STEP_FORWARD, cursor_moved
from llamatron.tui.note_names import note_shown
from llamatron.tui import keybindings

# The OK button is the one Enter presses, so it is the one drawn selected.
OK = 0
BUTTON_BINDINGS = (keybindings.TuneDialog.DONE, keybindings.TuneDialog.CANCEL)
# A step is two cells wide, so that a note one step long still shows a gap after it.
STEP_WIDTH = 2
# The rows drawn above the highest note and below the lowest, so that a note has somewhere to be moved to in the picture.
ROWS_BESIDE = 1
# The cells beside the picture: the longest note name, a space and the bar lines at both ends.
ROOM_BESIDE = 8


class TuneDialog(Dialog):
    """Answers with the line as edited, a list of notes and rests (line_edits.py), or None when cancelled."""

    KEYS = keybindings.TuneDialog

    def __init__(self, *, title, line, steps_in_bar, pitch_of_place, usual):
        super().__init__()
        self.title = title
        self.line = line_edits.tidied(line)
        self.steps_in_bar = steps_in_bar
        # The MIDI note of a place of the scale, for the names beside the rows.
        self.pitch_of_place = pitch_of_place
        # The line Bksp puts back.
        self.usual = line_edits.tidied(usual)
        self.place = 0

    def steps(self):
        return line_edits.steps_of(self.line)

    def under_cursor(self):
        """Return the note or rest the cursor's step is inside, and the step it starts on."""
        index, start = line_edits.found(line=self.line, step=self.place)
        return self.line[index], start

    def keys(self):
        return [
            self.bind(self.KEYS.CANCEL, action=lambda: self.dismiss(None)),
            self.bind(self.KEYS.MOVE, action=self.move, wants_key=True),
            self.bind(self.KEYS.PITCH, action=self.move_note),
            self.bind(self.KEYS.NOTE, action=self.toggle),
            self.bind(self.KEYS.SHORTER, action=lambda: self.stretch(STEP_BACK)),
            self.bind(self.KEYS.LONGER, action=lambda: self.stretch(STEP_FORWARD)),
            self.bind(self.KEYS.USUAL, action=self.put_back),
            self.bind(self.KEYS.DONE, action=lambda: self.dismiss(line_edits.tidied(self.line))),
        ]

    def move(self, name):
        self.place = cursor_moved(place=self.place, name=name, count=self.steps())

    def move_note(self, direction):
        self.line = line_edits.moved(line=self.line, step=self.place, by=direction)

    def toggle(self):
        """Take the note under the cursor out, or put one in; the last note of a line stays, since a line with no note is no tune."""
        changed = line_edits.toggled(line=self.line, step=self.place)
        if any(not line_edits.is_rest(note) for note in changed):
            self.line = changed

    def stretch(self, direction):
        self.line = line_edits.stretched(line=self.line, step=self.place, by=direction)

    def put_back(self):
        self.line = line_edits.tidied(self.usual)

    def legend_lines(self, width):
        """Return the keys listed under the picture, leaving out OK and CANCEL, which the buttons name."""
        return legend(keys=[item for item in self.keys() if item.shown], width=width)

    def wanted_width(self):
        return max(super().wanted_width(), self.steps() * STEP_WIDTH + ROOM_BESIDE + DIALOG_MARGIN)

    # Drawing.

    def places_drawn(self):
        """Return the places of the scale that get a row, the highest first: every place from the highest note to the lowest, and a row beyond each."""
        places = [line_edits.place_of(note) for note in self.line if not line_edits.is_rest(note)]
        highest = min(max(places) + ROWS_BESIDE, line_edits.HIGHEST_PLACE)
        lowest = max(min(places) - ROWS_BESIDE, line_edits.LOWEST_PLACE)
        return list(range(highest, lowest - 1, -1))

    def in_bars(self, cells):
        """Return a row's cells between bar lines."""
        size = self.steps_in_bar * STEP_WIDTH
        return marks.MSG_WIZARD_HOOK_BAR_LINE + marks.MSG_WIZARD_HOOK_BAR_LINE.join(''.join(cells[at:at + size]) for at in range(0, len(cells), size)) + marks.MSG_WIZARD_HOOK_BAR_LINE

    def row_line(self, *, place, width):
        """Return one place's row: filled where a note at the place sounds, the note under the cursor shaded lighter so that it stands out."""
        cells = [marks.MSG_WIZARD_HOOK_GAP] * (self.steps() * STEP_WIDTH)
        held, _ = self.under_cursor()
        at = 0
        for note in self.line:
            length = line_edits.length_of(note)
            if not line_edits.is_rest(note) and line_edits.place_of(note) == place:
                filled = length * STEP_WIDTH - 1
                cells[at * STEP_WIDTH:at * STEP_WIDTH + filled] = [marks.MSG_TUNE_CURSOR_NOTE if note is held else marks.MSG_WIZARD_HOOK_CELL] * filled
            at += length
        return Text(marks.MSG_WIZARD_HOOK_ROW.format(name=note_shown(self.pitch_of_place(place)), width=width, cells=self.in_bars(cells)), no_wrap=True)

    def floor_line(self, width):
        size = self.steps_in_bar * STEP_WIDTH
        floor = marks.MSG_WIZARD_HOOK_FLOOR_BAR.join([marks.MSG_WIZARD_HOOK_FLOOR * size] * (self.steps() // self.steps_in_bar))
        return Text(marks.MSG_WIZARD_HOOK_ROW.format(name=NOTHING, width=width, cells=marks.MSG_WIZARD_HOOK_FLOOR_BAR + floor + marks.MSG_WIZARD_HOOK_FLOOR_BAR), style=Style.DIM, no_wrap=True)

    def cursor_line(self, width):
        """Return the line under the floor, with the cursor's mark under the cursor's step."""
        cells = [marks.MSG_WIZARD_HOOK_GAP] * (self.steps() * STEP_WIDTH)
        cells[self.place * STEP_WIDTH] = marks.MSG_TUNE_CURSOR
        # Bar lines take a cell each in the rows above, so the marks are spaced as the rows are.
        return Text(marks.MSG_WIZARD_HOOK_ROW.format(name=NOTHING, width=width, cells=self.in_bars(cells).replace(marks.MSG_WIZARD_HOOK_BAR_LINE, marks.MSG_WIZARD_HOOK_GAP)), style=Style.BOLD, no_wrap=True)

    def said(self):
        """Return what the cursor is on, in words: the step, and the note there with its length, or a rest."""
        held, _ = self.under_cursor()
        if line_edits.is_rest(held):
            return marks.MSG_TUNE_REST_SAID.format(step=self.place + 1, steps=self.steps())
        return marks.MSG_TUNE_NOTE_SAID.format(step=self.place + 1, steps=self.steps(), note=note_shown(self.pitch_of_place(line_edits.place_of(held))), length=line_edits.length_of(held))

    def lines(self, width):
        places = self.places_drawn()
        name_width = max(len(note_shown(self.pitch_of_place(place))) for place in places)
        buttons = [(binding[1], label) for label, binding in zip(labels.MSG_OK_CANCEL_BUTTONS, BUTTON_BINDINGS)]
        return [*[self.row_line(place=place, width=name_width) for place in places], self.floor_line(name_width), self.cursor_line(name_width),
                Text(self.said(), style=Style.DIM), Text(NOTHING), *button_row(buttons=buttons, selected=OK)]
