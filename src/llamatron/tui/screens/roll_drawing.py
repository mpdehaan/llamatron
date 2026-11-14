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

"""Draws the piano roll: the header, a row per pitch with notes as bars, and the description of the step under the cursor.

The rows run from the highest pitch down, scrolled so that the cursor's row is always on screen,
with a rule where each octave starts and a double rule under the step numbers. A note fills its
cells and runs through the dividers it crosses, so one held note is one bar and two notes back
to back keep the divider between them; the cursor is shaded on a note and a reversed blank on an
empty cell. Rows outside the one playing track's octaves are dim and marked off. A note whose gate
ends inside a step fills only part of its last cell, as near as five columns can, so the bar ends
where the sound does, the user's design of 2026-11-08; the header's second line names the scale
and the entry size.
"""

from typing import NamedTuple

from rich.text import Text

from llamatron.tui.drawing import Box, fit, NOTHING, SPACE, Style
from llamatron.tui.screens.grid_drawing import CELL_WIDTH, GridDrawing
from llamatron.composition.checks import fraction_text
from llamatron.strings.marks import (
    MSG_CURSOR_BLOCK, MSG_ENTRY_SIZE_SHOWN, MSG_FROM_SONG_SHOWN, MSG_GHOST_LINE, MSG_GRAB_NOTE_MARK, MSG_NOTE_CELL, MSG_NOTE_CELL_WITH_MARK,
    MSG_NOTE_EDGE, MSG_NOTE_HOLLOW, MSG_NOTE_HOLLOW_UNDER_CURSOR, MSG_NOTE_UNDER_CURSOR, MSG_NOTE_UNDER_CURSOR_WITH_MARK, MSG_OUT_OF_RANGE_CELL,
)

# What a solid bar's blocks become in a hollow one.
HOLLOW = str.maketrans({MSG_NOTE_EDGE: MSG_NOTE_HOLLOW, MSG_CURSOR_BLOCK: MSG_NOTE_HOLLOW_UNDER_CURSOR})

# The lines around the pitch rows: the two header lines, the top rule, the Step row, its double rule, the bottom rule and the description.
LINES_AROUND_ROWS = 7
# The fewest pitch rows drawn, however short the screen.
MIN_ROWS = 1
# The column of a cell that holds a note's mark, its sharp, flat or G, in the middle, or the bar's last column when the bar is shorter.
MARK_COLUMN = CELL_WIDTH // 2


def filled_columns(part):
    """Return how many of a cell's columns a part of a step fills, rounded to the nearest, and never none or all, so that a short note is seen to be short."""
    columns = (part.numerator * CELL_WIDTH * 2 + part.denominator) // (part.denominator * 2)
    return max(min(columns, CELL_WIDTH - 1), 1)


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
        whose = NOTHING if editor.pattern().get_written_entry_size() else MSG_FROM_SONG_SHOWN
        entry = MSG_ENTRY_SIZE_SHOWN.format(size=fraction_text(editor.document().entry_size(editor.item)), whose=whose)
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
            return MSG_GRAB_NOTE_MARK
        # A sharp or flat has a row of its own when the scale is known, so the mark is only for numbered rows.
        return roll.accidental_symbol(start) if roll.scale_name() is None else None

    def note_cell(self, *, mark, selected, columns=CELL_WIDTH, hollow=False):
        """Return a note's cell, shaded under the cursor, with its mark in reverse video in the middle so that it reads against the bar, and hollow for a note an inversion
        plays an octave up.
        """
        cell = self.solid_note_cell(mark=mark, selected=selected, columns=columns)
        return Text(cell.plain.translate(HOLLOW), spans=cell.spans, no_wrap=True) if hollow else cell

    def solid_note_cell(self, *, mark, selected, columns):
        """Return a note's cell with its bar solid.

        A cell the note only partly fills, where its gate ends inside the step, is that many
        columns of bar and then blank, with the mark in the bar's last column when the middle is
        past its end.
        """
        if columns == CELL_WIDTH and mark is None:
            return Text(MSG_NOTE_UNDER_CURSOR if selected else MSG_NOTE_CELL, no_wrap=True)
        if columns == CELL_WIDTH:
            cell = Text((MSG_NOTE_UNDER_CURSOR_WITH_MARK if selected else MSG_NOTE_CELL_WITH_MARK).format(mark=mark), no_wrap=True)
            cell.stylize(Style.REVERSE, MARK_COLUMN, MARK_COLUMN + len(mark))
            return cell
        block = MSG_CURSOR_BLOCK if selected else MSG_NOTE_EDGE
        bar = block * columns
        if mark is not None:
            column = min(MARK_COLUMN, columns - 1)
            bar = bar[:column] + mark + bar[column + 1:]
        cell = Text(fit(text=bar, width=CELL_WIDTH), no_wrap=True)
        if mark is not None:
            cell.stylize(Style.REVERSE, column, column + len(mark))
        return cell

    def columns_filled(self, *, notes, step):
        """Return how many columns a note's bar fills in this cell: all of them, or part when the note's gate ends inside its last step."""
        start = notes.covering.get(step)
        roll = self.roll()
        if step != start + roll.note_span(start) - 1:
            return CELL_WIDTH
        part = roll.partial_cell(start)
        return CELL_WIDTH if part is None else filled_columns(part)

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

    def ghost_cell(self, *, notes, step, selected):
        """Return the thin dim line of a chord's added note over one step, as far as the chord's note fills the cell."""
        columns = self.columns_filled(notes=notes, step=step)
        return Text(fit(text=MSG_GHOST_LINE * columns, width=CELL_WIDTH), style=Style.REVERSE if selected else Style.CHORD_NOTE, no_wrap=True)

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
        editor = self._editor
        on_row = pitch == roll.pitch
        in_range = roll.in_range(pitch)
        # The cursor's cell stands between two bold double bars, the user's choice of 2026-11-08 over a box over the rows beside it, since a shaded bar alone was hard to find.
        cursor_edges = self.cursor_edges() if on_row else ()
        beats = self.beat_steps()
        line = Text(no_wrap=True)
        line.append(Box.BAR, style=Style.DIM)
        # A row between two degrees is dim even in range, so the scale's own rows stand out.
        line.append(fit(text=SPACE + roll.row_label(pitch), width=self.label_width()), style=Style.BOLD if on_row else (Style.PLAIN if in_range and roll.is_degree(pitch) else Style.DIM))
        for step in range(first, last):
            mark = self.note_mark(notes=notes, pitch=pitch, step=step)
            ghost = mark is False and self.ghost_here(notes=notes, pitch=pitch, step=step)
            hollow = notes.covering.get(step) in notes.lifted
            if self.continues(notes=notes, pitch=pitch, step=step):
                replaced = MSG_NOTE_HOLLOW if hollow else MSG_NOTE_EDGE
            elif ghost and notes.covering.get(step) != step:
                replaced = Text(MSG_GHOST_LINE, style=Style.CHORD_NOTE)
            elif step in cursor_edges:
                replaced = Text(Box.DOUBLE_BAR, style=Style.BOLD)
            else:
                replaced = None
            self.append_edge(line=line, step=step, beats=beats, single=Box.BAR, double=Box.DOUBLE_BAR, replaced=replaced)
            selected = on_row and step == editor.step
            if mark is not False:
                line.append_text(self.note_cell(mark=mark, selected=selected, columns=self.columns_filled(notes=notes, step=step), hollow=hollow))
            elif ghost:
                line.append_text(self.ghost_cell(notes=notes, step=step, selected=selected))
            elif selected:
                line.append(SPACE * CELL_WIDTH, style=Style.REVERSE)
            elif in_range:
                line.append(SPACE * CELL_WIDTH)
            else:
                line.append(MSG_OUT_OF_RANGE_CELL, style=Style.DIM)
        if last in cursor_edges:
            line.append(Box.DOUBLE_BAR, style=Style.BOLD)
        else:
            line.append(Box.BAR, style=Style.DIM)
        return line

    def heading_rule(self, *, first, last, boxed=None):
        """Return the double rule under the step numbers."""
        return self.rule(
            left=Box.DOUBLE_RULE_LEFT_TEE, tee=Box.DOUBLE_RULE_CROSS, beat_tee=Box.DOUBLE_RULE_DOUBLE_CROSS, right=Box.DOUBLE_RULE_RIGHT_TEE,
            first=first, last=last, line_character=Box.DOUBLE_RULE, boxed=boxed, boxed_tee=Box.DOUBLE_RULE_DOUBLE_CROSS, boxed_right=Box.DOUBLE_RULE_DOUBLE_RIGHT_TEE,
        )

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
        return lines

    def body(self, *, width, height):
        self._editor.clamp()
        self.roll().place_cursor()
        first, last = self.scroll_to_cursor(width)
        pitches = self.pitches_shown(height)
        lines = self.header_lines(width=width, first=first, last=last) + self.grid_lines(first=first, last=last, pitches=pitches)
        return self.with_description(lines=lines, width=width, height=height)
