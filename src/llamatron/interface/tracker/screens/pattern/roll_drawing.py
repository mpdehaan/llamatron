# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Draws the piano roll: the header, a row per pitch with notes as bars, and the description of the step under the cursor.

The rows run from the highest pitch down, scrolled so that the cursor's row is always on screen,
with a rule where each octave starts and a double rule under the step numbers. A note fills its
cells and runs through the dividers it crosses, so one held note is one bar and two notes back
to back keep the divider between them; the cursor is shaded on a note and a reversed blank on an
empty cell. Rows outside the one playing track's octaves are dim and marked off. A note whose gate
ends inside a step fills only part of its last cell, as near as five columns can, so the bar ends
where the sound does; the header's second line names the scale
and the entry size.
"""

from typing import NamedTuple

from llamatron.interface.forms import pattern_grid
from llamatron.interface.forms.pattern_grid import RollCell, RollRow
from llamatron.interface.tracker import drawing
from llamatron.interface.tracker.renderers import pattern_grid as grid_renderer
from llamatron.interface.tracker.screens.pattern.grid_drawing import GridDrawing
from llamatron.model.file.checks import fraction_text
from llamatron.model.schema.file_format import Row
from llamatron.user_strings import marks

# The lines around the pitch rows: the two header lines, the top rule, the Step row, its double rule, the bottom rule and the description.
LINES_AROUND_ROWS = 7
# The fewest pitch rows drawn, however short the screen.
MIN_ROWS = 1
# Which of the grid's lines is the roll's top row, under the top rule, the step numbers and the heading's rule: where the keyswitch lights go.
TOP_PITCH_LINE = 3


def filled_columns(part):
    """Return how many of a cell's columns a part of a step fills, rounded to the nearest, and never none or all, so that a short note is seen to be short."""
    columns = (part.numerator * pattern_grid.CELL_WIDTH * 2 + part.denominator) // (part.denominator * 2)
    return max(min(columns, pattern_grid.CELL_WIDTH - 1), 1)


class DrawnNotes(NamedTuple):
    """What drawing the roll's rows needs to know about the pattern's notes.

    covering is the step of the note sounding through each step, ghosts the rows of the notes
    each note's chord adds, and pitches each note's row, the last two by the note's step; lifted
    holds the steps of the notes an inversion plays an octave up, whose bars are drawn hollow.
    """

    covering: dict
    ghosts: dict
    pitches: dict
    lifted: frozenset


class RollDrawing(GridDrawing):
    """Draws a PatternEditor's piano roll from the roll's cursor and the pattern's notes."""

    __slots__ = ()

    def roll(self):
        return self._editor.roll

    def widest_label(self):
        """Return the width the roll's own row labels can need, with a space either side."""
        return self.roll().widest_row_label() + 2

    def header_extra(self):
        """Return the second header line's cells after Time: the scale and the entry size, how long Space draws a note, said to be the song's when the pattern sets none."""
        editor = self._editor
        whose = drawing.NOTHING if editor.pattern().get_written_entry_size() else marks.MSG_FROM_SONG_SHOWN
        entry = marks.MSG_ENTRY_SIZE_SHOWN.format(size=fraction_text(editor.document().entry_size(editor.item)), whose=whose)
        return [self.scale_header(), entry]

    # Which rows are on screen.

    def lines_for(self, rows):
        """Return how many lines a run of rows takes, highest first, with the rules between octaves that fall inside it."""
        return len(rows) + sum(1 for pitch in rows[:-1] if self.roll().starts_an_octave(pitch))

    def pitches_shown(self, height):
        """Return the rows drawn, highest first, moving the window so that the cursor's row is on it and centring it the first time."""
        roll = self.roll()
        rows = roll.rows()
        room = max(height - LINES_AROUND_ROWS, MIN_ROWS)
        cursor = rows.index(roll.pitch)
        if roll.top_pitch is None:
            roll.top_pitch = rows[max(cursor - room // 2, 0)]
        # The top row may have been a sharp's row that went, so the window starts at the nearest row still there, and never below the cursor.
        top = min(next((place for place, pitch in enumerate(rows) if pitch <= roll.top_pitch), cursor), cursor)
        while self.lines_for(rows[top:cursor + 1]) > room and top < cursor:
            top += 1
        roll.top_pitch = rows[top]
        shown = []
        for pitch in rows[top:]:
            if self.lines_for([*shown, pitch]) > room and shown:
                break
            shown.append(pitch)
        return shown

    # The rows.

    def note_mark(self, *, notes, pitch, step):
        """Return what marks a note's first step at this pitch, G for a grab or its sharp or flat, None for no mark, and False where no note is."""
        roll = self.roll()
        start = notes.covering.get(step)
        if start is None or notes.pitches[start] != pitch:
            return False
        if start != step:
            return None
        if roll.grabs(start):
            return marks.MSG_GRAB_NOTE_MARK
        # A sharp or flat has a row of its own when the scale is known, so the mark is only for numbered rows.
        return roll.accidental_symbol(start) if roll.scale_name() is None else None

    def columns_filled(self, *, notes, step):
        """Return how many columns a note's bar fills in this cell: all of them, or part when the note's gate ends inside its last step."""
        start = notes.covering.get(step)
        roll = self.roll()
        if step != start + roll.note_span(start) - 1:
            return pattern_grid.CELL_WIDTH
        part = roll.partial_cell(start)
        return pattern_grid.CELL_WIDTH if part is None else filled_columns(part)

    def continues(self, *, notes, pitch, step):
        """Return whether a note at this pitch runs from the step before into this one, so the bar replaces the divider."""
        start = notes.covering.get(step)
        return start is not None and start != step and notes.pitches[start] == pitch

    def notes(self):
        """Return what the rows need to know about the pattern's notes, gathered once per change of the set rather than asked again for every cell."""
        editor = self._editor
        document = editor.document()
        return document.remembered(key=(RollDrawing.notes.__name__, editor.item), on=(document,), compute=self.gathered_notes)

    def gathered_notes(self):
        roll = self.roll()
        covering = roll.covering()
        starts = set(covering.values())
        lifted = frozenset(start for start in starts if roll.root_is_lifted(start))
        return DrawnNotes(covering=covering, ghosts=self.ghosts_of(starts), pitches=self.pitches_of(starts), lifted=lifted)

    def ghosts_of(self, starts):
        """Return each note's ghosts, the rows of the notes its chord adds, by the note's step."""
        return {start: self.roll().ghost_pitches(start) for start in starts}

    def pitches_of(self, starts):
        """Return each note's row, by the note's step."""
        return {start: self.roll().pitch_of(start) for start in starts}

    def ghost_here(self, *, notes, pitch, step):
        """Return whether a chord's added note at this pitch sounds through this step: the chord's note covers it, and its chord reaches this row."""
        start = notes.covering.get(step)
        return start is not None and pitch in notes.ghosts[start]

    def cursor_edges(self):
        """Return the edges the cursor's bold double bars stand on: the left edge of the cursor's step and of the step after it, which is the right border on the last step."""
        editor = self._editor
        return (editor.step, editor.step + 1)

    def pitch_line(self, *, notes, pitch, first, last):
        """Return a row of the roll, drawn once and kept until the set changes.

        Only the cursor's row shows where the cursor is, so a row is kept by its pitch and the
        steps shown, and the cursor's row by the cursor's step as well: moving the cursor draws
        the row the cursor left and the row the cursor reached, and every other row is the line
        already drawn. Nothing changes a line once it's drawn.
        """
        editor = self._editor
        document = editor.document()
        cursor_step = editor.step if pitch == self.roll().pitch else None
        key = (RollDrawing.pitch_line.__name__, editor.item, pitch, first, last, cursor_step)
        return document.remembered(key=key, on=(document,), compute=lambda: self.drawn_pitch_line(notes=notes, pitch=pitch, first=first, last=last))

    def drawn_pitch_line(self, *, notes, pitch, first, last):
        """Draw a row of the roll: its label, then each step's edge and cell."""
        roll = self.roll()
        on_row = pitch == roll.pitch
        in_range = roll.in_range(pitch)
        cursor_edges = self.cursor_edges() if on_row else ()
        # A row between two degrees is dim even in range, so the scale's own rows stand out.
        label_kind = pattern_grid.DIM_LABEL
        if on_row:
            label_kind = pattern_grid.BOLD_LABEL
        elif in_range and roll.is_degree(pitch):
            label_kind = pattern_grid.PLAIN_LABEL
        cursor_step = self._editor.step if on_row else None
        steps = self.row_steps(notes=notes, pitch=pitch, steps=range(first, last), cursor_step=cursor_step, in_range=in_range)
        last_edge = pattern_grid.CURSOR_EDGE if last in cursor_edges else pattern_grid.DIVIDER_EDGE
        row = RollRow(label=roll.row_label(pitch), label_kind=label_kind, steps=steps, beats=self.beat_steps(), last_edge=last_edge)
        return grid_renderer.roll_row_line(row=row, label_width=self.label_width())

    def row_steps(self, *, notes, pitch, steps, cursor_step, in_range):
        """Return each step of a row as the roll shows it, with the step's number.

        Most of a row has no note and no chord's line at its pitch, and off the cursor's row such a
        step is the divider and a blank cell, shared rather than asked for, since every row is
        drawn again whenever the set changes and the calls were measured at a twentieth of a
        millisecond a key.
        """
        plain = (pattern_grid.DIVIDER_EDGE, pattern_grid.EMPTY if in_range else pattern_grid.OUT_OF_RANGE)
        covering = notes.covering
        shown = []
        for step in steps:
            start = covering.get(step)
            if cursor_step is None and (start is None or (notes.pitches[start] != pitch and pitch not in notes.ghosts[start])):
                shown.append((step, plain))
            else:
                shown.append((step, self.step_shown(notes=notes, pitch=pitch, step=step, cursor_step=cursor_step, in_range=in_range)))
        return tuple(shown)

    def step_shown(self, *, notes, pitch, step, cursor_step, in_range):
        """Return a step of a row as the roll shows it: the edge before it, which a note's bar or a chord's line runs through, and
        its cell; cursor_step is the cursor's step on the cursor's row, and None on every other row."""
        mark = self.note_mark(notes=notes, pitch=pitch, step=step)
        ghost = mark is False and self.ghost_here(notes=notes, pitch=pitch, step=step)
        hollow = notes.covering.get(step) in notes.lifted
        if self.continues(notes=notes, pitch=pitch, step=step):
            edge = pattern_grid.HOLLOW_EDGE if hollow else pattern_grid.NOTE_EDGE
        elif ghost and notes.covering.get(step) != step:
            edge = pattern_grid.GHOST_EDGE
        else:
            edge = self.plain_edge(step=step, cursor_step=cursor_step)
        selected = step == cursor_step
        if mark is not False:
            return edge, RollCell(kind=pattern_grid.NOTE_CELL, mark=mark, hollow=hollow, columns=self.columns_filled(notes=notes, step=step), selected=selected)
        if ghost:
            return edge, RollCell(kind=pattern_grid.GHOST_CELL, columns=self.columns_filled(notes=notes, step=step), selected=selected)
        return self.empty_step_shown(step=step, cursor_step=cursor_step, in_range=in_range)

    def empty_step_shown(self, *, step, cursor_step, in_range):
        """Return a step with no note or chord's line at this pitch: its plain edge, and a blank cell, or a mark outside the range."""
        edge = self.plain_edge(step=step, cursor_step=cursor_step)
        if step == cursor_step:
            return edge, pattern_grid.EMPTY_UNDER_CURSOR
        if in_range:
            return edge, pattern_grid.EMPTY
        return edge, pattern_grid.OUT_OF_RANGE

    @staticmethod
    def plain_edge(*, step, cursor_step):
        """Return a step's edge where nothing runs through it: one of the cursor's double bars, or the divider."""
        if cursor_step is not None and step in (cursor_step, cursor_step + 1):
            return pattern_grid.CURSOR_EDGE
        return pattern_grid.DIVIDER_EDGE

    def heading_rule(self, *, first, last, boxed=None):
        """Return the double rule under the step numbers."""
        return self.drawn_rule(kind=pattern_grid.HEADING, first=first, last=last, boxed=boxed)

    def boxed_beside(self, *pitches):
        """Return the cursor's step when one of the rows beside a rule is the cursor's, so that the rule boxes the cursor's cell on that side, and None otherwise."""
        return self._editor.step if self.roll().pitch in pitches else None

    def grid_lines(self, *, first, last, pitches):
        roll = self.roll()
        notes = self.notes()
        lines = [self.top_rule(first=first, last=last), self.step_line(first=first, last=last), self.heading_rule(first=first, last=last, boxed=self.boxed_beside(pitches[0]))]
        for place, pitch in enumerate(pitches):
            lines.append(self.pitch_line(notes=notes, pitch=pitch, first=first, last=last))
            if roll.starts_an_octave(pitch) and pitch != pitches[-1]:
                lines.append(self.inner_rule(first=first, last=last, boxed=self.boxed_beside(pitch, pitches[place + 1])))
        lines.append(self.bottom_rule(first=first, last=last, boxed=self.boxed_beside(pitches[-1])))
        lines[TOP_PITCH_LINE] = self.with_keyswitch_lights(line=lines[TOP_PITCH_LINE], first=first, last=last)
        return self.with_read_head(lines=lines, first=first, last=last)

    def with_keyswitch_lights(self, *, line, first, last):
        """Return the roll's top row with a light in the middle of the cell of every step shown whose note has keyswitches, drawn over a note's bar when one is
        there: the top row stays in view however far the roll scrolls."""
        editor = self._editor
        steps = [step for step in range(first, last) if editor.value(row=Row.KEYSWITCH, step=step) and editor.is_note(step=step)]
        columns = [self.edge_column(step=step, first=first) + pattern_grid.EDGE_WIDTH + pattern_grid.MARK_COLUMN for step in steps]
        return grid_renderer.with_keyswitch_lights(line=line, columns=columns)

    def with_read_head(self, *, lines, first, last):
        """Return the roll's lines with the read head down them at the left edge of the step that sounds, while the pattern plays."""
        step = self._editor.playing_step()
        if step is None or not first <= step < last:
            return lines
        return grid_renderer.with_read_head(lines=lines, column=self.edge_column(step=step, first=first))

    def edge_column(self, *, step, first):
        """Return the column of a step's left edge on the screen."""
        return pattern_grid.EDGE_WIDTH + self.label_width() + (step - first) * (pattern_grid.CELL_WIDTH + pattern_grid.EDGE_WIDTH)

    def body(self, *, width, height):
        self._editor.clamp()
        self.roll().place_cursor()
        first, last = self.scroll_to_cursor(width)
        pitches = self.pitches_shown(height)
        lines = self.header_lines(width=width, first=first, last=last) + self.grid_lines(first=first, last=last, pitches=pitches)
        return self.with_description(lines=lines, width=width, height=height)
