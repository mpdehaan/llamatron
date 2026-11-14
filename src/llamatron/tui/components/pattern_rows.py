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


"""The pattern editor's rows: the cursor's row, the sections that open and close, and the keys of the row the cursor is on.

One of the editor's two views, shaped like the other, PianoRoll: it holds its own cursor and
keys, reads and writes the pattern through the editor's document, and knows nothing of Textual;
PatternDrawing draws it. The pinned rows (the Degree gauge with its number, and the octave under
it) stay at the top while the rows beneath scroll. Those rows come in sections, the user's design
of 2026-11-08: each is headed by a row (SectionRow) that Space or Enter opens or closes, PgUp and
PgDn jump between the headings, and which sections are open is kept on the app for the session.
"""

from llamatron.composition.file_format import CC_ROWS, CONDITION_ROWS, REGISTER_ADD_ROWS, REGISTER_NOTE_ROWS, REGISTER_SET_ROWS, REGISTER_VELOCITY_ROWS, Row
from llamatron.composition.row_descriptions import ROW_DESCRIPTIONS
from llamatron.tui.components.accidental_row import AccidentalRow
from llamatron.tui.components.add_row import AddRow
from llamatron.tui.components.cc_row import CcRow
from llamatron.tui.components.chord_row import ChordRow
from llamatron.tui.components.chord_scale_row import ChordScaleRow
from llamatron.tui.components.condition_row import ConditionRow
from llamatron.tui.components.degree_row import DegreeRow, GAUGE_ROWS_WITHOUT_SCALE
from llamatron.tui.components.dot_row import DotRow
from llamatron.tui.components.inversion_row import InversionRow
from llamatron.tui.components.gate_row import GateRow
from llamatron.tui.components.glide_row import GlideRow
from llamatron.tui.components.grab_row import GrabRow
from llamatron.tui.components.number_row import NumberRow
from llamatron.tui.components.octave_row import OctaveRow
from llamatron.tui.components.register_row import RegisterRow
from llamatron.tui.components.section_row import SectionRow
from llamatron.tui.components.set_row import SetRow
from llamatron.tui.components.slide_row import SlideRow
from llamatron.tui.components.tension_row import TensionRow
from llamatron.tui.components.tie_row import TieRow
from llamatron.tui.key_table import STEP_BACK, cursor_moved, BindsKeys
from llamatron.tui.keys import Key, RowSection
from llamatron.tui import keybindings

# The rows at the top, which stay in place while the rows beneath them scroll: the note's gauge and its octave right under it.
PINNED_ROWS = [Row.DEGREE, Row.OCTAVE]
# The sections of rows under the pinned ones, in order, each headed by a row the cursor can rest on: the user's grouping of 2026-11-08.
SECTIONS = {
    RowSection.BASICS: [Row.ACCIDENTAL, Row.VELOCITY],
    # Everything about a step's chord together, the user's design: the chord, then the scale it borrows, its tensions and its inversion.
    RowSection.CHORD: [Row.CHORD, Row.CHORD_SCALE, Row.TENSION, Row.INVERSION],
    RowSection.TIMING: [Row.TIE, Row.GATE, Row.DOT, Row.GLIDE],
    RowSection.ADVANCED: [Row.PROBABILITY, Row.RATCHET, Row.RATCHET_OFFSET, Row.GRAB],
    RowSection.CC: [*CC_ROWS, Row.SLIDE],
    # The register sections read in the order a step works them out, the user's choice of 2026-11-11: sets, then adds, then the uses, then the conditions.
    RowSection.REGISTER_MOD: [*REGISTER_SET_ROWS.values(), *REGISTER_ADD_ROWS.values()],
    RowSection.REGISTER_APPLY: [*REGISTER_NOTE_ROWS.values(), *REGISTER_VELOCITY_ROWS.values()],
    RowSection.REGISTER_COND: [*CONDITION_ROWS.values()],
}
# The component that draws and edits each row.
ROW_CLASSES = {
    Row.DEGREE: DegreeRow, Row.GATE: GateRow, Row.DOT: DotRow, Row.ACCIDENTAL: AccidentalRow, Row.OCTAVE: OctaveRow,
    Row.CHORD: ChordRow, Row.TENSION: TensionRow, Row.CHORD_SCALE: ChordScaleRow, Row.INVERSION: InversionRow, Row.VELOCITY: NumberRow, Row.PROBABILITY: NumberRow, Row.GLIDE: GlideRow, Row.TIE: TieRow,
    Row.RATCHET: NumberRow, Row.RATCHET_OFFSET: NumberRow, Row.GRAB: GrabRow, Row.SLIDE: SlideRow,
    **dict.fromkeys(CC_ROWS, CcRow),
    **dict.fromkeys(REGISTER_NOTE_ROWS.values(), RegisterRow),
    **dict.fromkeys(REGISTER_VELOCITY_ROWS.values(), RegisterRow),
    **dict.fromkeys(REGISTER_ADD_ROWS.values(), AddRow),
    **dict.fromkeys(REGISTER_SET_ROWS.values(), SetRow),
    **dict.fromkeys(CONDITION_ROWS.values(), ConditionRow),
}
# The arrows that move the cursor along the steps; the others move it between rows.
STEP_ARROWS = (Key.LEFT, Key.RIGHT)
TOP_ROW = 0


class PatternRows(BindsKeys):
    """The rows' cursor, their sections and their keys, which read and write the pattern through the editor's document."""

    KEYS = keybindings.PatternRows

    __slots__ = ('editor', 'drawing', 'row', 'first_row', 'gauge_rows', 'row_objects')

    def __init__(self, *, editor, drawing):
        self.editor = editor
        # What draws the rows, which the editor asks for when the rows are showing.
        self.drawing = drawing
        # The cursor's row, as a place among the rows it can reach, and the first of the scrolled rows on screen, which the drawing moves so that the cursor is always shown.
        self.row = TOP_ROW
        self.first_row = 0
        # How many rows the Degree gauge is drawn with, which the drawing caps to what fits the screen.
        self.gauge_rows = GAUGE_ROWS_WITHOUT_SCALE
        # The row objects, one per row name, built as they're first needed.
        self.row_objects = {}

    def row_for(self, name):
        """Return the row object for a row name, or a section's heading row for a section's name, built the first time it's asked for."""
        if name not in self.row_objects:
            self.row_objects[name] = (SectionRow if name in SECTIONS else ROW_CLASSES[name])(editor=self.editor, name=name)
        return self.row_objects[name]

    # The sections.

    def section_is_open(self, section):
        return section in self.editor.holder.open_sections

    def toggle_section(self, section):
        """Open a closed section or close an open one, for the session, leaving the cursor on its heading."""
        self.editor.holder.open_sections ^= {section}

    def section_rows(self, section):
        """Return the names of a section's rows, leaving out those a drum pattern has no use for."""
        names = SECTIONS[section]
        if self.editor.is_drum():
            names = [name for name in names if ROW_DESCRIPTIONS[name].is_in_drum_patterns()]
        return names

    def shown_sections(self):
        """Return the sections that have rows in this pattern: a drum pattern has no Chord section, since none of its rows mean anything there."""
        return [section for section in SECTIONS if self.section_rows(section)]

    def section_of(self, row):
        """Return the section a row is in, by its name or its heading's, or None for a pinned row."""
        for section, names in SECTIONS.items():
            if row == section or row in names:
                return section
        return None

    def all_row_names(self):
        """Return every row there could be, open or closed, which sizes the label column so that nothing moves when a section opens."""
        return [*PINNED_ROWS, *[name for section in self.shown_sections() for name in (section, *self.section_rows(section))]]

    def jump_section(self, direction):
        """Move the cursor to the next section's heading, which PgDn does, or the one before, which PgUp does, stopping at the first and the last like every cursor."""
        headings = [place for place, row in enumerate(self.reachable()) if row.marks_label()]
        if direction == STEP_BACK:
            self.row = next((place for place in reversed(headings) if place < self.row), self.row if self.row < headings[0] else headings[0])
        else:
            self.row = next((place for place in headings if place > self.row), self.row if self.row > headings[-1] else headings[-1])

    # The rows, and the one under the cursor.

    def reachable(self):
        """Return the rows the cursor can reach: the pinned ones, then each section's heading with its rows when it's open. Chords and moving notes by registers aren't used in a drum pattern."""
        names = list(PINNED_ROWS)
        for section in self.shown_sections():
            names.append(section)
            if self.section_is_open(section):
                names += self.section_rows(section)
        return [self.row_for(name) for name in names]

    def pinned_rows(self):
        return self.reachable()[:len(PINNED_ROWS)]

    def scrolled_rows(self):
        """Return the rows beneath the pinned ones, which scroll when the screen is too short for them all."""
        return self.reachable()[len(PINNED_ROWS):]

    def scrolled_row(self):
        """Return the cursor's place among the scrolled rows, or None when it's on a pinned row."""
        place = self.row - len(PINNED_ROWS)
        return place if place >= 0 else None

    def current_row(self):
        return self.reachable()[self.row]

    def row_name(self):
        return self.current_row().name

    def clamp(self):
        """Keep the cursor on a row that's there, since closing a section or loading another pattern takes rows away."""
        self.row = max(min(self.row, len(self.reachable()) - 1), 0)

    def go_to_top(self):
        """Put the cursor on the first row, as a pattern whose rows changed starts."""
        self.row = TOP_ROW

    # What the editor asks of whichever view is showing.

    def other_view_binding(self):
        """Return the editor's binding for Tab from here, which goes to the piano roll."""
        return keybindings.PatternEditor.TO_ROLL

    def other_view_what(self):
        """Return what Tab does from here, for the legend."""
        _, _, what = self.other_view_binding()
        return what

    def step_keys(self, *, can_remove):
        """Return the keys that insert and remove a step, which the editor lists after Tab, the second only where a step can be removed."""
        result = [self.bind(self.KEYS.INSERT_STEP, action=self.editor.insert_step)]
        if can_remove:
            result.append(self.bind(self.KEYS.REMOVE_STEP, action=self.editor.remove_step))
        return result

    def lists_step_keys(self):
        """Return whether the legend lists the keys that insert and remove a step, which the rows' does."""
        return self.KEYS.INSERT_STEP in self.KEYS.IN_LEGEND

    def takes_note_letters(self):
        """Return whether letters type notes where the cursor is, as on a drum pattern's Note row, where D is a note and so can't remove a step."""
        return self.editor.is_drum() and self.row_name() == Row.DEGREE

    def move_keys(self):
        """Return the keys that move the cursor, which the editor lists after Esc: the arrows, the ends, which only the F1 dialog names, and the jump between section headings."""
        return [
            self.bind(self.KEYS.MOVE, action=self.move, wants_key=True),
            self.bind(self.KEYS.ENDS, action=self.editor.jump_end),
            self.bind(self.KEYS.SECTION, action=self.jump_section),
        ]

    def keys(self):
        """Return the current row's keys, which the editor lists last, and which a rest only has on rows a rest can hold."""
        row = self.current_row()
        return row.in_order(row.keys()) if row.editable() else []

    def move(self, name):
        """Move the cursor a step or a row, stopping at the pattern's ends and the first and last row."""
        editor = self.editor
        if name in STEP_ARROWS:
            editor.step = cursor_moved(place=editor.step, name=name, count=max(editor.steps(), 1))
        else:
            self.row = cursor_moved(place=self.row, name=name, count=len(self.reachable()))
