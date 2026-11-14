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

"""What the pattern editor's two drawings share: the header, the window of steps, the rules and the Step row, and the description.

The grid shows as many steps as fit across the screen, from the editor's first_step, and moves
that window so that the cursor's step is always on it, so a long pattern scrolls sideways rather
than wrapping onto more blocks; the header's second line says which steps are on screen. The
piano roll (RollDrawing) and the rows (PatternDrawing) draw their own cells between the rules.
"""

from rich.text import Text

from llamatron.composition.file_format import Row
from llamatron.tui.drawing import Align, Box, fit, NOTHING, SPACE, Style
from llamatron.composition.checks import fraction_text
from llamatron.composition.naming import words
from llamatron.strings.labels import MSG_DOT_NAMES, MSG_NO_SCALE_NEEDED, MSG_SCALE_HEADER, MSG_SEVERAL_SCALES, MSG_STEP_HEADING
from llamatron.strings.marks import (
    MSG_DIRECTION_HEADER, MSG_DRUM_HEADER, MSG_DRUM_OFF, MSG_DRUM_ON, MSG_FROM_SONG_SHOWN, MSG_HEADER_CELL_GAP, MSG_HEADER_INDENT, MSG_SCALE_SHOWN,
    MSG_STEPS_HEADER, MSG_STEP_SIZE_SHOWN, MSG_TIME_SIGNATURE_SHOWN,
)
from llamatron.strings.messages import (
    MSG_DEGREE_WITHOUT_SCALE, MSG_DESCRIBE_CHORD, MSG_DESCRIBE_EMPTY, MSG_DESCRIBE_GATE_OVERRIDDEN, MSG_DESCRIBE_NOTE,
    MSG_DESCRIBE_TIED, MSG_GRABBED_SOUND, MSG_IN_SCALE, MSG_NO_SCALE,
)

# How wide a cell of the grid is, which every value fits.
CELL_WIDTH = 5
# The lines after the grid: a blank line and the description.
LINES_AFTER_GRID = 2


class GridDrawing:
    """Draws the parts of a PatternEditor's screen that don't depend on what the cells hold."""

    __slots__ = ('_editor',)

    def __init__(self, editor):
        self._editor = editor

    def label_width(self):
        """Return how wide the labels down the left are: one width for both views, the wider, so that the grid stays put when Tab switches views (the user's choice of 2026-11-09)."""
        return self._editor.label_width()

    def widest_label(self):
        """Return the width this drawing's own labels need, with a space either side."""
        raise NotImplementedError

    def steps_shown(self, width):
        """Return how many steps fit across the screen beside the labels."""
        return max((width - self.label_width() - 2) // (CELL_WIDTH + 1), 1)

    def scroll_to_cursor(self, width):
        """Move the window of steps so that the cursor's step is on it, and return its first and last steps (the last excluded)."""
        return self._editor.window_of_steps(self.steps_shown(width))

    # The header.

    def scale_header(self):
        """Return what the header says about the scale: the one the rows are drawn in, the note that there are several, or that drums need none."""
        editor = self._editor
        if editor.pattern().is_drum():
            return MSG_SCALE_HEADER.format(scale=MSG_NO_SCALE_NEEDED)
        document = editor.document()
        scales = document.scales_of_pattern(editor.item)
        if len(scales) > 1:
            return MSG_SEVERAL_SCALES
        if not scales:
            return MSG_SCALE_HEADER.format(scale=MSG_NO_SCALE)
        if document.scale_name_says_what_it_is(scales[0]):
            return MSG_SCALE_HEADER.format(scale=scales[0])
        return MSG_SCALE_HEADER.format(scale=MSG_SCALE_SHOWN.format(name=scales[0], notes=document.scale_notes_text(scales[0])))

    def header_extra(self):
        """Return what the header's second line says after the time signature, which each drawing decides."""
        raise NotImplementedError

    def header_lines(self, *, width, first, last):
        """Return the two header lines as aligned cells: Steps, Step size, Drum and Direction over Time and what the view adds (the user's layout of 2026-11-09)."""
        pattern = self._editor.pattern()
        drum = MSG_DRUM_ON if pattern.is_drum() else MSG_DRUM_OFF
        whose = NOTHING if pattern.get_written_step_size() else MSG_FROM_SONG_SHOWN
        step_size = MSG_STEP_SIZE_SHOWN.format(size=fraction_text(self._editor.document().lengths().step_size(self._editor.item)), whose=whose)
        first_cells = [
            MSG_STEPS_HEADER.format(steps=pattern.get_steps()), step_size, MSG_DRUM_HEADER.format(drum=drum),
            MSG_DIRECTION_HEADER.format(direction=words(pattern.get_direction())),
        ]
        signature_whose = NOTHING if pattern.get_written_time_signature() else MSG_FROM_SONG_SHOWN
        second_cells = [MSG_TIME_SIGNATURE_SHOWN.format(signature=self.time_signature().to_text(), whose=signature_whose), *self.header_extra()]
        header, second = header_cells(lines=[first_cells, second_cells])
        shown = self._editor.steps_shown_text(first=first, last=last)
        if shown:
            second = fit(text=second, width=width - len(shown) - 1) + SPACE + shown
        return [Text(header, no_wrap=True), Text(second, no_wrap=True)]

    def time_signature(self):
        """Return the time signature the pattern is drawn in: its own, or else the song's."""
        return self._editor.document().song().get_pattern_time_signature(self._editor.pattern())

    def beat_steps(self):
        """Return the steps, counted from 0, that start a beat of the time signature, worked out once per change of the set, since parsing the signature for every cell cost more than drawing them."""
        editor = self._editor
        document = editor.document()
        # The pattern's own time signature and step size, or else the song's signature and the set's step size.
        on = (editor.pattern(), document.song(), document.setlist())
        return document.remembered(key=(GridDrawing.beat_steps.__name__, editor.item), on=on, compute=self.steps_starting_a_beat)

    def steps_starting_a_beat(self):
        """Return the steps, counted from 0, that start a beat of the pattern's time signature at its step size."""
        editor = self._editor
        step_size = editor.document().lengths().step_size(editor.item)
        signature = self.time_signature()
        return frozenset(step for step in range(editor.pattern().get_steps()) if signature.starts_a_beat(step * step_size))

    def starts_a_beat(self, step):
        """Return whether a step, counted from 0, starts a beat of the time signature, which makes its number bold."""
        return step in self.beat_steps()

    # The rules and the Step row.

    def rule(self, *, left, tee, beat_tee, right, first, last, line_character=Box.RULE, boxed=None, boxed_tee=None, boxed_right=None, joints=True):
        """Return a rule across the grid, with a double tee where a step starts a beat, or an unbroken line when joints is false, for a rule with no dividers on either side.

        When boxed names a step, the rule is the edge of the cursor's cell on that step: the piece
        under or over the cell is a bold double rule, joined to the cell's double bars by boxed_tee
        at both ends, or boxed_right where the cell's right bar is the grid's border, so that the
        cursor's cell is boxed on that side too, as the user asked on 2026-11-09 when the single
        rule between the double joints read as the wrong corners.

        A joint where the bold beat edge crosses the dim rule is plain, between the two, so that
        neither line reads as broken: a bold cross showed as a break in the rule at every beat,
        and a dim one as a break in the beat edge at every rule and section heading, both of which
        the user saw on 2026-11-08. Every crossing is read after a change to a drawing (.claude/UX.md).
        """
        # The line has no style of its own, so that a plain joint stays plain among the dim pieces.
        line = Text(no_wrap=True)
        line.append(left + line_character * self.label_width(), style=Style.DIM)
        beats = self.beat_steps()
        for step in range(first, last):
            if boxed is not None and step in (boxed, boxed + 1):
                line.append(boxed_tee, style=Style.PLAIN)
            elif not joints:
                line.append(line_character, style=Style.DIM)
            elif step in beats:
                line.append(beat_tee, style=Style.PLAIN)
            else:
                line.append(tee, style=Style.DIM)
            if step == boxed:
                line.append(Box.DOUBLE_RULE * CELL_WIDTH, style=Style.BOLD)
            else:
                line.append(line_character * CELL_WIDTH, style=Style.DIM)
        if boxed is not None and boxed + 1 == last:
            line.append(boxed_right, style=Style.PLAIN)
        else:
            line.append(right, style=Style.DIM)
        return line

    def top_rule(self, *, first, last):
        return self.rule(left=Box.TOP_LEFT, tee=Box.TOP_TEE, beat_tee=Box.DOUBLE_TOP_TEE, right=Box.TOP_RIGHT, first=first, last=last)

    def inner_rule(self, *, first, last, boxed=None):
        return self.rule(
            left=Box.LEFT_TEE, tee=Box.CROSS, beat_tee=Box.DOUBLE_CROSS, right=Box.RIGHT_TEE, first=first, last=last,
            boxed=boxed, boxed_tee=Box.DOUBLE_RULE_DOUBLE_CROSS, boxed_right=Box.DOUBLE_RULE_DOUBLE_RIGHT_TEE,
        )

    def bottom_rule(self, *, first, last, boxed=None, joints=True):
        return self.rule(
            left=Box.BOTTOM_LEFT, tee=Box.BOTTOM_TEE, beat_tee=Box.DOUBLE_BOTTOM_TEE, right=Box.BOTTOM_RIGHT, first=first, last=last,
            boxed=boxed, boxed_tee=Box.DOUBLE_RULE_DOUBLE_BOTTOM_TEE, boxed_right=Box.DOUBLE_BOTTOM_RIGHT, joints=joints,
        )

    # The rules around a row with no dividers, like a section heading: the dividers above end in bottom tees, the ones below start in top tees, and between two such rows the rule is unbroken.

    def closing_rule(self, *, first, last):
        return self.rule(left=Box.LEFT_TEE, tee=Box.BOTTOM_TEE, beat_tee=Box.DOUBLE_BOTTOM_TEE, right=Box.RIGHT_TEE, first=first, last=last)

    def opening_rule(self, *, first, last):
        return self.rule(left=Box.LEFT_TEE, tee=Box.TOP_TEE, beat_tee=Box.DOUBLE_TOP_TEE, right=Box.RIGHT_TEE, first=first, last=last)

    def plain_rule(self, *, first, last):
        return self.rule(left=Box.LEFT_TEE, tee=Box.CROSS, beat_tee=Box.DOUBLE_CROSS, right=Box.RIGHT_TEE, first=first, last=last, joints=False)

    def append_edge(self, *, line, step, beats, single, double, replaced=None):
        """Add a step's left edge to a line: a bold double line where the step starts a beat, so the beats stand out as columns, unless a bar runs through it.

        beats is beat_steps(), which whoever draws the line asks for once rather than once for every step.
        """
        if isinstance(replaced, Text):
            line.append_text(replaced)
        elif replaced is not None:
            line.append(replaced)
        elif step in beats:
            line.append(double, style=Style.BOLD)
        else:
            line.append(single, style=Style.DIM)

    def step_line(self, *, first, last):
        head = Text(no_wrap=True)
        head.append(Box.BAR, style=Style.DIM)
        head.append(fit(text=MSG_STEP_HEADING, width=self.label_width()), style=Style.BOLD)
        beats = self.beat_steps()
        for step in range(first, last):
            self.append_edge(line=head, step=step, beats=beats, single=Box.BAR, double=Box.DOUBLE_BAR)
            head.append(fit(text=str(step + 1), width=CELL_WIDTH, align=Align.CENTER), style=Style.BOLD if step in beats else Style.PLAIN)
        head.append(Box.BAR, style=Style.DIM)
        return head

    # The description of the step under the cursor.

    def describe(self):
        step = self._editor.step + 1
        if not self._editor.is_note():
            return (MSG_DESCRIBE_TIED if self._editor.value(row=Row.TIE) else MSG_DESCRIBE_EMPTY).format(step=step)
        document = self._editor.document()
        where = NOTHING if self._editor.is_drum() else MSG_IN_SCALE.format(scale=document.pattern_scale(self._editor.item) or document.song().get_scale_name() or MSG_NO_SCALE)
        played = self._editor.document().note_name(name=self._editor.item, step=self._editor.step)
        if self._editor.value(row=Row.GRAB):
            # What a grab step plays is whatever the other track played, moved by whatever else is at work, so the line names no note, as the user chose.
            sound = MSG_GRABBED_SOUND
        elif played:
            sound = played + where
        else:
            sound = MSG_DEGREE_WITHOUT_SCALE.format(degree=self._editor.value(row=Row.DEGREE))
        chord = self._editor.value(row=Row.CHORD)
        chord_text = MSG_DESCRIBE_CHORD.format(chord=chord) if chord is not None else NOTHING
        gate = str(fraction_text(self._editor.gate_now())) + MSG_DOT_NAMES.get(self._editor.value(row=Row.DOT), NOTHING)
        if self._editor.gate_is_overridden():
            gate += MSG_DESCRIBE_GATE_OVERRIDDEN
        return MSG_DESCRIBE_NOTE.format(step=step, sound=sound, gate=gate, chord=chord_text)

    def with_description(self, *, lines, width, height):
        """Return the header and grid lines with the description after them, set apart by a blank line unless the console is too short for one."""
        description = Text(SPACE + fit(text=self.describe(), width=width - 1), style=Style.BOLD)
        spacer = [Text(NOTHING)] if len(lines) + LINES_AFTER_GRID <= height else []
        return lines + spacer + [description]


def header_cells(*, lines):
    """Return the header lines laid out as columns of cells: each column as wide as its widest cell, so that the cells of one line start under the other's.

    A line's last cell is written as it is, so a long last cell, like the rows view's section hint, runs on without widening a column.
    """
    widths = {}
    for cells in lines:
        for column, cell in enumerate(cells[:-1]):
            widths[column] = max(widths.get(column, 0), len(cell))
    return [
        MSG_HEADER_INDENT + MSG_HEADER_CELL_GAP.join([*[cell.ljust(widths[column]) for column, cell in enumerate(cells[:-1])], cells[-1]])
        for cells in lines
    ]
