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
"""The chord editor: a progression's chords as a row of bars rising to each chord's degree, with its numeral and its name in the song's scale, and rows of sharps and flats and of inversions beneath.

The user's design of 2026-11-11. Up and Down move the cursor between the Chord row, the #/b row,
the Quality, Tens. and Scale rows and the Inv. row, and Left and Right along the chords. On the Chord row, [ and ] step the degree from 1 to 7 and digits type one; on the #/b
and Inv. rows, [ and ] and Space or Enter step through their choices. I inserts a chord I before
the cursor's, D removes the cursor's, and H fills the chords with a named progression, matched to
the song's scale.

A chord leaves the song's scale three ways, the user's design (composition/chords.py): its Scale, a scale type on the same
root that the chord borrows; its Quality, a named chord symbol in place of the chord the scale builds; and its Tensions, the
notes added on top. On those rows [ and ] and Space step through the choices and Enter opens the Chord dialog, the one the
pattern editor opens, on that row's list. The Name row and the status line say what the cursor's chord comes to.
"""


from llamatron.composition.chords import chord_half_steps, borrowed
from llamatron.composition.file_format import ACCIDENTAL_CYCLE, FIXED_CHORDS, TENSIONS, GeneratorKind, Section
from llamatron.composition.generator_settings import PROGRESSION_INVERSIONS
from llamatron.composition.limits import MAX_PROGRESSION_CHORDS, MAX_PROGRESSION_DEGREE, MIN_PROGRESSION_CHORDS, MIN_PROGRESSION_DEGREE
from llamatron.composition.naming import words
from llamatron.composition.progressions import NAMED_PROGRESSIONS, ROMAN_NUMERALS, named_progression_in, shown_numerals
from llamatron.strings.help import HELP_CHORDS_EDITOR
from llamatron.strings.labels import (
    Crumb, MSG_CHORD_NAME_ROW_LABEL, MSG_CHORD_ROW_LABEL, MSG_INVERSION_ROW_LABEL, MSG_NUMERAL_ROW_LABEL, MSG_PROGRESSION_ACCIDENTAL_ROW_LABEL,
    MSG_PROGRESSION_GROUPS, MSG_PROGRESSION_NAMES, MSG_PROGRESSION_QUALITY_ROW_LABEL, MSG_PROGRESSION_SCALE_ROW_LABEL, MSG_PROGRESSION_TENSIONS_ROW_LABEL,
)
from llamatron.strings.marks import (
    MSG_ACCIDENTAL_MARKS, MSG_AUGMENTED_NUMERAL_MARK, MSG_DIMINISHED_NUMERAL_MARK, MSG_GAUGE_BAR, MSG_GAUGE_HALF_BAR, MSG_TENSIONS_COUNTED, MSG_TENSIONS_IN_CELL_SEPARATOR,
)
from llamatron.strings.messages import (
    MSG_CHORD_DIALOG_TITLE, MSG_CHORD_OF_PROGRESSION, MSG_CHORDS_NOTE, MSG_PROGRESSION_PICKER_TITLE, MSG_QUALITY_FROM_SCALE, MSG_RESTING_CHORD,
)
from llamatron.tui import keybindings
from llamatron.tui.chord_text import ChordInWords
from llamatron.tui.components.chord_row import quality_names
from llamatron.tui.scale_categories import SCALE_TYPES_IN_ORDER
from llamatron.tui.scale_categories import SCALE_CATEGORIES
from llamatron.tui.dialogs.chord_dialog import QUALITY_LIST, SCALE_LIST, TENSION_LIST, ChordChoice, ChordDialog
from llamatron.tui.dialogs.grid_choice_dialog import GridChoiceDialog, grouped_grid
from llamatron.tui.drawing import Box, NOTHING, Style
from llamatron.tui.key_table import STEP_BACK, STEP_FORWARD, cursor_moved
from llamatron.tui.keys import ARROWS_LEFT_RIGHT
from llamatron.tui.screens.step_editor import StepEditor
from llamatron.tui.screens.step_grid import StepGrid
from llamatron.tui.screens.shows_named_item import ShowsNamedItem

# The rows the cursor edits, top to bottom, in the user's order, the same wherever a chord is chosen: its root, with the root's sharp or flat, then its quality, its
# tensions, the scale it borrows, and how it is voiced.
CHORD_ROW = 0
ACCIDENTAL_ROW = 1
QUALITY_ROW = 2
TENSION_ROW = 3
SCALE_ROW = 4
INVERSION_ROW = 5
EDITED_ROWS = 6
# The rows the Chord dialog edits together, and the list it opens on from each.
DIALOG_ROWS = {SCALE_ROW: SCALE_LIST, QUALITY_ROW: QUALITY_LIST, TENSION_ROW: TENSION_LIST}
# What each of those rows steps through, nothing first.
QUALITY_CYCLE = [None, *FIXED_CHORDS]
SCALE_CYCLE = [None, *SCALE_TYPES_IN_ORDER]
TENSION_CYCLE = [None, *[(tension,) for tension in TENSIONS]]
# The Degree gauge is drawn two degrees a line, a half block for the odd one, so that the page fits 24 lines with the three rows added.
GAUGE_LINES = (MAX_PROGRESSION_DEGREE + 1) // 2
# The degree a chord with a sharp or flat keeps the sound of, when no quality is named: the figure's own, on degree 1.
FIGURE_DEGREE = 1
# The half steps of a minor third, a diminished fifth and an augmented fifth, which a numeral shows.
MINOR_THIRD = 3
DIMINISHED_FIFTH = 6
AUGMENTED_FIFTH = 8
THIRD_AND_FIFTH = 2
# How much of a scale type's name and of a chord's tensions a cell shows.
CELL_ROOM = 5
# The inversions a chord steps through: root position first.
INVERSION_CYCLE = [None, *PROGRESSION_INVERSIONS]
# The chord I inserts.
INSERTED_DEGREE = MIN_PROGRESSION_DEGREE
# What a digit types on the Inv. row to go back to root position.
ROOT_POSITION_TYPED = 0


class ChordsEditor(ShowsNamedItem, StepGrid, StepEditor):
    """A progression's chords, up to 16, each a column of the grid."""

    KEYS = keybindings.ChordsEditor
    HELP = HELP_CHORDS_EDITOR
    SECTION = Section.PROGRESSIONS
    CRUMBS_BEFORE = (Crumb.GENERATORS,)
    CRUMBS_AFTER = (Crumb.CHORDS,)
    # A cell is wide enough for a numeral like ♭vii° or a name like Bb°.
    CELL_WIDTH = 7

    def __init__(self, *, holder, name):
        super().__init__(holder)
        self.show_item(name)
        self.edited_row = CHORD_ROW

    def progression(self):
        return self.document().song().get_generator_settings(kind=GeneratorKind.PROGRESSION, name=self.item)

    def scale(self):
        """Return the current song's scale, which names the chords, or None when it has none."""
        song = self.document().song()
        name = song.get_scale_name()
        return None if name is None else song.get_named_scale(name)

    def steps(self):
        return len(self.progression().get_chords())

    def keys(self):
        self.keep_step()
        result = [
            self.bind(self.KEYS.BACK, action=self.go_back), self.bind(self.KEYS.MOVE, action=self.move, wants_key=True),
            self.bind(self.KEYS.LESS, action=lambda: self.nudge(STEP_BACK)), self.bind(self.KEYS.MORE, action=lambda: self.nudge(STEP_FORWARD)),
        ]
        if self.edited_row in (CHORD_ROW, INVERSION_ROW):
            result.append(self.bind(self.KEYS.TYPE, action=self.type_digit, wants_key=True))
        if self.edited_row in (ACCIDENTAL_ROW, INVERSION_ROW):
            result.append(self.bind(self.KEYS.NEXT, action=lambda: self.nudge(STEP_FORWARD)))
        if self.edited_row in DIALOG_ROWS:
            result += [
                self.bind(self.KEYS.CHOOSE, action=self.pick_chord), self.bind(self.KEYS.NEXT_CHOICE, action=lambda: self.nudge(STEP_FORWARD)),
                self.bind(self.KEYS.CLEAR, action=lambda: self.changed_here(row=self.edited_row, value=None)),
            ]
        if self.steps() < MAX_PROGRESSION_CHORDS:
            result.append(self.bind(self.KEYS.INSERT_STEP, action=self.add_step))
        if self.steps() > MIN_PROGRESSION_CHORDS:
            result.append(self.bind(self.KEYS.REMOVE_STEP, action=self.drop_step))
        result.append(self.bind(self.KEYS.PICK, action=self.pick_progression))
        return result

    def move(self, name):
        """Move along the chords with Left and Right, and between the rows with Up and Down, stopping at every edge."""
        if name in ARROWS_LEFT_RIGHT:
            self.step = cursor_moved(place=self.step, name=name, count=self.steps())
        else:
            self.edited_row = cursor_moved(place=self.edited_row, name=name, count=EDITED_ROWS)

    def rows(self):
        """Return the chords and the rows beside them, in the order of the rows on screen, as lists of one length."""
        progression = self.progression()
        return [
            progression.get_chords(), progression.get_accidentals(), progression.get_qualities(), progression.get_tensions(), progression.get_scales(),
            progression.get_inversions(),
        ]

    def store(self, rows):
        """Store every row, given in the order of the rows on screen."""
        self.document().set_progression(
            name=self.item, chords=rows[CHORD_ROW], accidentals=rows[ACCIDENTAL_ROW], inversions=rows[INVERSION_ROW],
            scales=rows[SCALE_ROW], qualities=rows[QUALITY_ROW], tensions=rows[TENSION_ROW],
        )

    def changed_here(self, *, row, value):
        """Store a value on the cursor's step of one of the rows."""
        rows = [list(values) for values in self.rows()]
        rows[row][self.step] = value
        self.store(rows)

    def set_value(self, value):
        self.changed_here(row=CHORD_ROW, value=value)

    def nudge(self, offset):
        """Step the cursor's value on the row being edited: the degree from 1 to 7, stopping at both, or the next or last choice of a sharp or flat or an inversion."""
        if self.edited_row == CHORD_ROW:
            self.set_value(max(min(self.rows()[CHORD_ROW][self.step] + offset, MAX_PROGRESSION_DEGREE), MIN_PROGRESSION_DEGREE))
            return
        cycle = {ACCIDENTAL_ROW: ACCIDENTAL_CYCLE, INVERSION_ROW: INVERSION_CYCLE, SCALE_ROW: SCALE_CYCLE, QUALITY_ROW: QUALITY_CYCLE, TENSION_ROW: TENSION_CYCLE}[self.edited_row]
        current = self.rows()[self.edited_row][self.step]
        if current not in cycle:
            # Several tensions at once are no step of the cycle, which starts again from none.
            current = None
        self.changed_here(row=self.edited_row, value=cycle[(cycle.index(current) + offset) % len(cycle)])

    def type_digit(self, digit):
        """Type a degree on the Chord row, or an inversion, 0 for root position, on the Inv. row."""
        if self.edited_row == CHORD_ROW:
            number = self.typed_number(digit=digit, low=MIN_PROGRESSION_DEGREE, high=MAX_PROGRESSION_DEGREE)
            if number is not None:
                self.set_value(number)
        elif self.edited_row == INVERSION_ROW:
            number = self.typed_number(digit=digit, low=ROOT_POSITION_TYPED, high=PROGRESSION_INVERSIONS[-1])
            if number is not None:
                self.changed_here(row=INVERSION_ROW, value=number or None)

    def add_step(self):
        self.store([values[:self.step] + [INSERTED_DEGREE if row == CHORD_ROW else None] + values[self.step:] for row, values in enumerate(self.rows())])

    def drop_step(self):
        self.store([values[:self.step] + values[self.step + 1:] for values in self.rows()])
        self.keep_step()

    # The chord under the cursor: its scale, quality and tensions, chosen together and said in words.

    def choice_at(self, place):
        """Return a chord's quality, tensions and scale type as a ChordChoice."""
        rows = self.rows()
        return ChordChoice(quality=rows[QUALITY_ROW][place], tensions=rows[TENSION_ROW][place], kind=rows[SCALE_ROW][place])

    def in_words(self, *, place, choice=None):
        """Return a chord in words, in the song's scale, with a ChordChoice in place of its own when one is given."""
        rows = self.rows()
        current = self.choice_at(place) if choice is None else choice
        accidental = rows[ACCIDENTAL_ROW][place]
        return ChordInWords(
            scale=self.scale(), degree=rows[CHORD_ROW][place], accidental=accidental, kind=current.kind, symbol=current.quality, tensions=current.tensions,
            own_degree=FIGURE_DEGREE if accidental and current.quality is None else None,
        )

    def pick_chord(self):
        """Open the Chord dialog on the cursor's chord, on the list of the row the cursor is on, and store what it answers."""
        place = self.step

        def chosen(choice):
            rows = [list(values) for values in self.rows()]
            rows[QUALITY_ROW][place] = choice.quality
            rows[TENSION_ROW][place] = choice.tensions
            rows[SCALE_ROW][place] = choice.kind
            self.store(rows)

        dialog = ChordDialog(
            title=MSG_CHORD_DIALOG_TITLE.format(where=MSG_CHORD_OF_PROGRESSION.format(chord=place + 1, progression=self.item)),
            qualities=QUALITY_CYCLE, quality_names=[MSG_QUALITY_FROM_SCALE, *quality_names(FIXED_CHORDS)], categories=SCALE_CATEGORIES,
            current=self.choice_at(place), opens_on=DIALOG_ROWS[self.edited_row], said=lambda choice: self.in_words(place=place, choice=choice).sentences(),
        )
        self.ask(dialog=dialog, then=chosen)

    def resting_status(self):
        """Say the cursor's chord, its name and notes in the song's scale, while nothing else is said."""
        self.keep_step()
        return self.in_words(place=self.step).resting(where=MSG_RESTING_CHORD.format(chord=self.step + 1))

    def numeral(self, place):
        """Return a chord's Roman numeral: upper case with a major third and lower case with a minor one, a mark for a diminished or augmented fifth, a sharp or flat in front."""
        rows = self.rows()
        degree = rows[CHORD_ROW][place]
        accidental = rows[ACCIDENTAL_ROW][place]
        quality = rows[QUALITY_ROW][place]
        own = chord_half_steps(
            scale=borrowed(scale=self.scale(), kind=rows[SCALE_ROW][place]), degree=degree, symbol=quality, own_degree=FIGURE_DEGREE if accidental and quality is None else None,
        )
        numeral = ROMAN_NUMERALS[(degree - 1) % len(ROMAN_NUMERALS)]
        if own and own[0] == MINOR_THIRD:
            numeral = numeral.lower()
        fifth = own[1] if len(own) >= THIRD_AND_FIFTH else None
        mark = {DIMINISHED_FIFTH: MSG_DIMINISHED_NUMERAL_MARK, AUGMENTED_FIFTH: MSG_AUGMENTED_NUMERAL_MARK}.get(fifth, NOTHING)
        return MSG_ACCIDENTAL_MARKS.get(accidental, NOTHING) + numeral + mark

    def gauge_cell(self, *, degree, line):
        """Return a chord's cell on one line of the Degree gauge, counted from the bottom: full where the degree reaches both of the line's degrees, half where it reaches the lower."""
        if degree >= 2 * line + 2:
            return MSG_GAUGE_BAR
        return MSG_GAUGE_HALF_BAR if degree >= 2 * line + 1 else NOTHING

    def pick_progression(self):
        """Fill the chords with a named progression from a picker of two columns, matched to the song's scale."""
        keys = [name for column in NAMED_PROGRESSIONS for name, _ in column]
        columns = []
        place = 0
        for heading, column in zip(MSG_PROGRESSION_GROUPS, NAMED_PROGRESSIONS):
            columns.append([(heading, list(range(place, place + len(column))))])
            place += len(column)
        dialog = GridChoiceDialog(
            title=MSG_PROGRESSION_PICKER_TITLE, options=[MSG_PROGRESSION_NAMES[key] for key in keys], grid=grouped_grid(columns),
            details=lambda chosen: shown_numerals(keys[chosen]),
        )
        self.ask(dialog=dialog, then=lambda chosen: self.fill(keys[chosen]))

    def fill(self, key):
        degrees, accidentals = named_progression_in(key=key, scale=self.scale())
        nothing = [None] * len(degrees)
        self.store([degrees, accidentals, list(nothing), list(nothing), list(nothing), list(nothing)])
        self.step = 0

    # Drawing.

    def body(self, *, width, height):
        self.keep_step()
        first, last = self.scroll_to_cursor(width)
        places = range(first, last)
        chords, accidentals, qualities, tensions, scales, inversions = self.rows()
        selected = {row: self.step if self.edited_row == row else None for row in range(EDITED_ROWS)}
        lines = [
            self.with_steps_shown(text=MSG_CHORDS_NOTE, style=Style.DIM, width=width, first=first, last=last),
            self.grid_rule(left=Box.TOP_LEFT, middle=Box.TOP_TEE, right=Box.TOP_RIGHT, count=len(places)),
            self.grid_line(label=MSG_CHORD_ROW_LABEL, cells=[(place, str(place + 1)) for place in places], selected=self.step, bold=True),
        ]
        for line in range(GAUGE_LINES - 1, -1, -1):
            lines.append(self.grid_line(label=NOTHING, cells=[(place, self.gauge_cell(degree=chords[place], line=line)) for place in places]))
        lines.append(self.grid_line(label=MSG_NUMERAL_ROW_LABEL, cells=[(place, self.numeral(place)) for place in places], selected=selected[CHORD_ROW]))
        lines.append(self.grid_line(label=MSG_CHORD_NAME_ROW_LABEL, cells=[(place, self.in_words(place=place).name()) for place in places]))
        lines.append(self.grid_rule(left=Box.LEFT_TEE, middle=Box.CROSS, right=Box.RIGHT_TEE, count=len(places)))
        lines.append(self.grid_line(
            label=MSG_PROGRESSION_ACCIDENTAL_ROW_LABEL, cells=[(place, MSG_ACCIDENTAL_MARKS.get(accidentals[place], NOTHING)) for place in places],
            selected=selected[ACCIDENTAL_ROW],
        ))
        lines.append(self.grid_line(label=MSG_PROGRESSION_QUALITY_ROW_LABEL, cells=[(place, qualities[place] or NOTHING) for place in places], selected=selected[QUALITY_ROW]))
        lines.append(self.grid_line(label=MSG_PROGRESSION_TENSIONS_ROW_LABEL, cells=[(place, tensions_shown(tensions[place])) for place in places], selected=selected[TENSION_ROW]))
        lines.append(self.grid_line(
            label=MSG_PROGRESSION_SCALE_ROW_LABEL, cells=[(place, NOTHING if scales[place] is None else words(scales[place]).title()[:CELL_ROOM]) for place in places],
            selected=selected[SCALE_ROW],
        ))
        lines.append(self.grid_line(
            label=MSG_INVERSION_ROW_LABEL, cells=[(place, NOTHING if inversions[place] is None else str(inversions[place])) for place in places],
            selected=selected[INVERSION_ROW],
        ))
        lines.append(self.grid_rule(left=Box.BOTTOM_LEFT, middle=Box.BOTTOM_TEE, right=Box.BOTTOM_RIGHT, count=len(places)))
        return lines


def tensions_shown(tensions):
    """Return a chord's tensions as a cell shows them: written out where they fit, and counted where they don't."""
    if not tensions:
        return NOTHING
    for separator in (MSG_TENSIONS_IN_CELL_SEPARATOR, NOTHING):
        if len(separator.join(tensions)) <= CELL_ROOM:
            return separator.join(tensions)
    return MSG_TENSIONS_COUNTED.format(count=len(tensions))
