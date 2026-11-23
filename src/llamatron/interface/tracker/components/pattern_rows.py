# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later


"""The pattern editor's rows: the cursor's row, the sections that open and close, and the keys of the row the cursor is on.

One of the editor's two views, shaped like the other, PianoRoll: it holds its own cursor and
keys, reads and writes the pattern through the editor's document, and knows nothing of Textual;
PatternDrawing draws it. The pinned rows (the Degree gauge with its number, and the octave under
it) stay at the top while the rows beneath scroll. Those rows come in sections:
each is headed by a row (SectionRow) that Space or Enter opens or closes, PgUp and
PgDn jump between the headings, and which sections are open is kept on the app for the session.
"""

from llamatron.interface.tracker import key_table, keybindings
from llamatron.interface.tracker.components import degree_row
from llamatron.interface.tracker.components.accent_row import AccentRow
from llamatron.interface.tracker.components.accidental_row import AccidentalRow
from llamatron.interface.tracker.components.cc_row import CcRow
from llamatron.interface.tracker.components.chord_row import ChordRow
from llamatron.interface.tracker.components.chord_scale_row import ChordScaleRow
from llamatron.interface.tracker.components.degree_row import DegreeRow
from llamatron.interface.tracker.components.dot_row import DotRow
from llamatron.interface.tracker.components.draw_reset_row import DrawResetRow
from llamatron.interface.tracker.components.gate_row import GateRow
from llamatron.interface.tracker.components.glide_row import GlideRow
from llamatron.interface.tracker.components.grab_row import GrabRow
from llamatron.interface.tracker.components.inversion_row import InversionRow
from llamatron.interface.tracker.components.keyswitch_row import KeyswitchSlotRow, slot_row_name, slot_rows
from llamatron.interface.tracker.components.number_row import NumberRow
from llamatron.interface.tracker.components.octave_row import OctaveRow
from llamatron.interface.tracker.components.register_row import RegisterRow
from llamatron.interface.tracker.components.section_row import SectionRow
from llamatron.interface.tracker.components.slide_row import SlideRow
from llamatron.interface.tracker.components.statement_row import StatementRow
from llamatron.interface.tracker.components.tension_row import TensionRow
from llamatron.interface.tracker.components.tie_row import TieRow
from llamatron.interface.tracker.key_table import BindsKeys, cursor_moved
from llamatron.interface.tracker.keys import Key, RowSection
from llamatron.model.schema import file_format, row_descriptions
from llamatron.model.schema.file_format import Row, StepStatement
from llamatron.user_strings import labels as labels_text

# The rows at the top, which stay in place while the rows beneath them scroll: the note's gauge and its octave right under it.
PINNED_ROWS = [Row.DEGREE, Row.OCTAVE]
# The sections of rows under the pinned ones, in order, each headed by a row the cursor can rest on.
SECTIONS = {
    RowSection.BASICS: [Row.ACCIDENTAL, Row.VELOCITY, Row.ACCENT],
    # Everything about a step's chord together, in the order that is the same wherever a chord is chosen: the chord, its tensions, the scale it borrows and its inversion.
    RowSection.CHORD: [Row.CHORD, Row.TENSION, Row.CHORD_SCALE, Row.INVERSION],
    RowSection.TIMING: [Row.TIE, Row.GATE, Row.DOT, Row.GLIDE],
    # The Keyswitch row is shown as a row for each slot of the instrument's Keyswitch Map, which the pattern and its instrument decide (section_rows).
    RowSection.KEYSWITCH: [Row.KEYSWITCH],
    RowSection.ADVANCED: [Row.PROBABILITY, Row.RATCHET, Row.RATCHET_OFFSET, Row.GRAB],
    RowSection.CC: [*file_format.CC_ROWS, Row.SLIDE],
    # The draws a step adds to its note and velocity, and the draws it resets first.
    RowSection.DRAW_APPLY: [*file_format.DRAW_NOTE_ROWS.values(), *file_format.DRAW_VELOCITY_ROWS.values(), *file_format.DRAW_RESET_ROWS.values()],
    # A step's statements, in the order a step reads them.
    RowSection.STOP_WHEN: [*file_format.STATEMENT_ROWS[StepStatement.STOP]],
    RowSection.RESTART_WHEN: [*file_format.STATEMENT_ROWS[StepStatement.RESTART]],
    RowSection.MUTE_WHEN: [*file_format.STATEMENT_ROWS[StepStatement.MUTE]],
}
# The component that draws and edits each row.
ROW_CLASSES = {
    Row.DEGREE: DegreeRow, Row.GATE: GateRow, Row.DOT: DotRow, Row.ACCIDENTAL: AccidentalRow, Row.OCTAVE: OctaveRow,
    Row.CHORD: ChordRow, Row.TENSION: TensionRow, Row.CHORD_SCALE: ChordScaleRow, Row.INVERSION: InversionRow, Row.VELOCITY: NumberRow, Row.ACCENT: AccentRow, Row.PROBABILITY: NumberRow, Row.GLIDE: GlideRow, Row.TIE: TieRow,
    Row.RATCHET: NumberRow, Row.RATCHET_OFFSET: NumberRow, Row.GRAB: GrabRow, Row.KEYSWITCH: KeyswitchSlotRow, Row.SLIDE: SlideRow,
    **dict.fromkeys(file_format.CC_ROWS, CcRow),
    **dict.fromkeys(file_format.DRAW_NOTE_ROWS.values(), RegisterRow),
    **dict.fromkeys(file_format.DRAW_VELOCITY_ROWS.values(), RegisterRow),
    **dict.fromkeys(file_format.DRAW_RESET_ROWS.values(), DrawResetRow),
    **dict.fromkeys(file_format.STATEMENT_OF_ROW, StatementRow),
}
# The slot each row of the Keyswitch section is for, by the row's name in the rows view.
SLOT_OF_ROW = {slot_row_name(slot): slot for slot in range(file_format.KEYSWITCH_SLOT_COUNT)}
KEYSWITCH_SLOTS_KEY = 'keyswitch slots'
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
        self.gauge_rows = degree_row.GAUGE_ROWS_WITHOUT_SCALE
        # The row objects, one per row name, built as they're first needed.
        self.row_objects = {}

    def row_for(self, name):
        """Return the row object for a row name, or a section's heading row for a section's name, built the first time it's asked for."""
        if name not in self.row_objects:
            if name in SLOT_OF_ROW:
                self.row_objects[name] = KeyswitchSlotRow(editor=self.editor, slot=SLOT_OF_ROW[name])
            else:
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
        if section == RowSection.KEYSWITCH:
            return [] if self.editor.is_drum() and not row_descriptions.ROW_DESCRIPTIONS[Row.KEYSWITCH].is_in_drum_patterns() else [slot_row_name(slot) for slot in self.keyswitch_slots()[0]]
        names = SECTIONS[section]
        if section == RowSection.DRAW_APPLY:
            names = self.rows_of_draws_with_values()
        if self.editor.is_drum():
            names = [name for name in names if row_descriptions.ROW_DESCRIPTIONS[name].is_in_drum_patterns()]
        return names

    def rows_of_draws_with_values(self):
        """Return the Use Draws rows of the current song's draws that hold a value, the Note+= rows, then Vel+= and Reset: none,
        and so no Use Draws section, while every draw is empty, as a new song's are."""
        draws = self.editor.document().song().draws_with_values()
        rows = []
        for by_draw in (file_format.DRAW_NOTE_ROWS, file_format.DRAW_VELOCITY_ROWS, file_format.DRAW_RESET_ROWS):
            rows += [by_draw[name] for name in draws]
        return rows

    def shown_sections(self):
        """Return the sections that have rows in this pattern: a drum pattern has no Chord section, since none of its rows mean
        anything there, and the Keyswitch section shows only once an instrument's Keyswitch Map or a step gives it a slot."""
        return [section for section in SECTIONS if self.section_rows(section)]

    def section_of(self, row):
        """Return the section a row is in, by its name or its heading's, or None for a pinned row."""
        for section, names in SECTIONS.items():
            if row == section or row in names:
                return section
        return None

    def keyswitch_slots(self):
        """Return the slots the Keyswitch section has rows for and the hint over them, worked out once until the set changes."""
        editor = self.editor
        document = editor.document()
        return document.remembered(key=(KEYSWITCH_SLOTS_KEY, editor.item, editor.opened_track), on=(document,), compute=lambda: slot_rows(editor))

    def section_hint(self, section):
        """Return what the header says while the cursor is in a section, or None for a section with nothing to say."""
        if section == RowSection.KEYSWITCH:
            return self.keyswitch_slots()[1]
        return labels_text.MSG_SECTION_HINTS.get(section)

    def all_row_names(self):
        """Return every row there could be, open or closed, which sizes the label column so that nothing moves when a section opens."""
        return [*PINNED_ROWS, *[name for section in self.shown_sections() for name in (section, *self.section_rows(section))]]

    def jump_section(self, direction):
        """Move the cursor to the next section's heading, which PgDn does, or the one before, which PgUp does, stopping at the first and the last like every cursor."""
        headings = [place for place, row in enumerate(self.reachable()) if row.marks_label()]
        if direction == key_table.STEP_BACK:
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
            self.bind(self.KEYS.MOVE, action=self.move_cursor, wants_key=True),
            self.bind(self.KEYS.ENDS, action=self.editor.jump_end),
            self.bind(self.KEYS.SECTION, action=self.jump_section),
        ]

    def keys(self):
        """Return the current row's keys, which the editor lists last, and which a rest only has on rows a rest can hold."""
        row = self.current_row()
        return row.in_order(row.keys()) if row.editable() else []

    def move_cursor(self, name):
        """Move the cursor a step or a row, stopping at the pattern's ends and the first and last row."""
        editor = self.editor
        if name in STEP_ARROWS:
            editor.step = cursor_moved(place=editor.step, name=name, count=max(editor.step_count(), 1))
        else:
            self.row = cursor_moved(place=self.row, name=name, count=len(self.reachable()))
