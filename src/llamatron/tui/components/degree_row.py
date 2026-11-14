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
"""The Degree row, drawn as a gauge: a bar in each step's column, filled from the bottom to the note's degree, with the number beneath.

The user chose gauges over numbers on 2026-11-08 so that a melody can be read as a shape. The
gauge is as tall as the scale when the pattern's uses agree on one, with the scale's note names
labelling its rows, and seven rows labelled by number when they don't or when nothing says. When
the scale is known, the gauge caps at the scale's size: a degree past it is shown, and written,
as the degree within the scale an octave higher, and + at the top and - at the bottom stop there
and say on the status line that the octave is changed on the Octave row, as the user chose on
2026-11-08 over carrying into the next octave. When the screen is too short for the whole gauge,
a degree above the rows that fit fills the bar and marks the number. A drum pattern keeps its
note letters and has no gauge.
"""

from llamatron.composition.file_format import Row
from llamatron.composition.limits import MIN_DEGREE
from llamatron.strings.errors import ERR_BOTTOM_OF_SCALE, ERR_TOP_OF_SCALE
from llamatron.tui.components.pattern_row import PatternRow
from llamatron.tui.drawing import NOTHING
from llamatron.tui.keys import DIGITS
from llamatron.strings.labels import MSG_ROW_LABELS
from llamatron.strings.legends import MSG_DIGITS_RANGE_LABEL
from llamatron.strings.marks import MSG_DRUM_LETTER_ROW, MSG_GAUGE_BAR, MSG_OVER_THE_TOP_MARK
from llamatron.tui import keybindings

# The gauge's rows when the scale isn't known, one per degree of a seven-note scale.
GAUGE_ROWS_WITHOUT_SCALE = 7
# The fewest rows a gauge is drawn with when the screen is short.
GAUGE_MIN_ROWS = 3


class DegreeRow(PatternRow):
    """Digits type a degree up to the scale's size, + and - move it, letters type a drum note, and Bksp makes the step a rest."""

    KEYS = keybindings.DegreeRow

    __slots__ = ()

    def label(self):
        return MSG_DRUM_LETTER_ROW if self.editor.is_drum() else MSG_ROW_LABELS[self.name]

    def on_rests(self):
        return True

    # The scale the gauge is drawn in.

    def scale_name(self):
        """Return the one scale the pattern plays under, or None when its uses disagree or nothing says."""
        return self.editor.document().pattern_scale(self.editor.item)

    def scale_size(self):
        """Return the scale's size when it's known, which is the gauge's full height and where degrees wrap, or None."""
        name = self.scale_name()
        return None if name is None else self.editor.document().scale_size(name)

    def has_gauge(self):
        return not self.editor.is_drum()

    def full_rows(self):
        """Return how many rows the gauge has when the screen has room for all of them."""
        return self.scale_size() or GAUGE_ROWS_WITHOUT_SCALE

    def rows_shown(self):
        """Return how many of the gauge's rows are drawn, which the drawing caps to fit the screen."""
        return min(self.full_rows(), max(self.editor.rows_view.gauge_rows, GAUGE_MIN_ROWS))

    def row_labels(self):
        """Return the gauge's row labels from the top down: the scale's note names, or the degrees as numbers."""
        name = self.scale_name()
        if name is None:
            names = [str(degree) for degree in range(MIN_DEGREE, self.full_rows() + 1)]
        else:
            names = self.editor.document().scale_note_names(name)
        return list(reversed(names[:self.rows_shown()]))

    def labels(self):
        if not self.has_gauge():
            return [self.label()]
        return [*self.row_labels(), self.label()]

    def rule_after(self):
        return self.has_gauge()

    # How a stored degree is shown: within the scale when it's known, with the octave moved up for what's past it.

    def shown_degree(self, *, step=None):
        """Return the degree as the gauge shows it, or None on a rest."""
        value = self.value(step=step)
        size = self.scale_size()
        if value is None or size is None or not self.has_gauge():
            return value
        return (value - MIN_DEGREE) % size + MIN_DEGREE

    def octave_shift(self, *, step=None):
        """Return how many octaves above its stored octave a note plays, for a degree past a known scale's size."""
        value = self.value(step=step)
        size = self.scale_size()
        if value is None or size is None or not self.has_gauge():
            return 0
        return (value - MIN_DEGREE) // size

    def limit(self):
        """Return the highest degree that can be typed: the scale's size when it's known, or the largest scale the pattern can play in."""
        return self.scale_size() or self.editor.document().degree_limit(self.editor.item)

    # Keys.

    def keys(self):
        if self.editor.is_drum():
            result = [self.bind(self.KEYS.NOTE, action=self.type_letter, wants_key=True)]
        else:
            limit = self.limit()
            digits = DIGITS if limit > int(DIGITS[-1]) else tuple(str(number) for number in range(MIN_DEGREE, limit + 1))
            result = [
                self.bind(self.KEYS.DEGREE, action=self.type_degree, wants_key=True, keys=digits, name=MSG_DIGITS_RANGE_LABEL.format(low=MIN_DEGREE, high=limit)),
                *self.adjust_keys(),
            ]
        if self.is_note():
            result.append(self.bind(self.KEYS.CLEAR, action=self.clear))
        return result

    def type_degree(self, digit):
        number = self.editor.typed_number(digit=digit, low=MIN_DEGREE, high=self.limit())
        if number is not None:
            self.set_value(number)
            self.editor.fill_in()

    def type_letter(self, letter):
        self.set_value(letter.upper())
        self.editor.fill_in()

    def nudge(self, offset):
        """Move the degree a step along the scale, stopping at the top or bottom of a known scale and saying where the octave is changed."""
        size = self.scale_size()
        if size is None:
            current = self.value() or 0
            self.set_value(max(min(current + offset, self.limit()), MIN_DEGREE))
            self.editor.fill_in()
            return
        current = self.shown_degree()
        if current is None:
            # A rest nudged either way becomes the root, as it did before the gauge.
            degree = MIN_DEGREE
        else:
            degree = current + offset
            if degree > size:
                self.editor.refuse(ERR_TOP_OF_SCALE.format(scale=self.scale_name()))
                degree = size
            elif degree < MIN_DEGREE:
                self.editor.refuse(ERR_BOTTOM_OF_SCALE.format(scale=self.scale_name()))
                degree = MIN_DEGREE
        if self.octave_shift():
            # A file's degree past the scale is written back within it, with its octave moved up to match.
            self.editor.set_value(value=self.editor.row_for(Row.OCTAVE).octave_now() + self.octave_shift(), row=Row.OCTAVE)
        self.set_value(degree)
        self.editor.fill_in()

    def clear(self):
        self.editor.document().clear_sound(name=self.editor.item, step=self.editor.step)

    # Drawing.

    def cell_text(self, *, step):
        """Return the number under the gauge, marked when the gauge is too short to show it, or the drum note's letter."""
        if not self.has_gauge():
            value = self.value(step=step)
            return NOTHING if value is None else str(value)
        degree = self.shown_degree(step=step)
        if degree is None:
            return NOTHING
        return str(degree) + (MSG_OVER_THE_TOP_MARK if degree > self.rows_shown() else NOTHING)

    def cell_lines(self, *, step):
        if not self.has_gauge():
            return [self.cell_text(step=step)]
        degree = self.shown_degree(step=step) or 0
        bars = [MSG_GAUGE_BAR if degree >= level else NOTHING for level in range(self.rows_shown(), 0, -1)]
        return [*bars, self.cell_text(step=step)]
