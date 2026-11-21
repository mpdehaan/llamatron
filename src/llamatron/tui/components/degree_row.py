# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Degree row, drawn as a gauge: a bar in each step's column, filled from the bottom to the note's degree, with the number beneath.

Gauges were chosen over numbers so that a melody can be read as a shape. The
gauge is as tall as the scale when the pattern's uses agree on one, with the scale's note names
labelling its rows, and seven rows labelled by number when they don't or when nothing says. When
the scale is known, the gauge caps at the scale's size: a degree past it is shown, and written,
as the degree within the scale an octave higher, and + at the top and - at the bottom stop there
and say on the status line that the octave is changed on the Octave row,
rather than carrying into the next octave. When the screen is too short for the whole gauge,
a degree above the rows that fit fills the bar and marks the number. A drum pattern keeps its
note letters and has no gauge.
"""

from llamatron.composition import limits
from llamatron.composition.file_format import Row
from llamatron.tui import drawing, keybindings, keys as keys_values
from llamatron.tui.components.pattern_row import PatternRow
from llamatron.user_strings import errors, labels as labels_text, legends, marks

# The gauge's rows when the scale isn't known, one per degree of a seven-note scale.
GAUGE_ROWS_WITHOUT_SCALE = 7
# The fewest rows a gauge is drawn with when the screen is short.
GAUGE_MIN_ROWS = 3


class DegreeRow(PatternRow):
    """Digits type a degree up to the scale's size, + and - move it, letters type a drum note, and Bksp makes the step a rest."""

    KEYS = keybindings.DegreeRow

    __slots__ = ()

    def label(self):
        return marks.MSG_DRUM_LETTER_ROW if self.editor.is_drum() else labels_text.MSG_ROW_LABELS[self.name]

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
            names = [str(degree) for degree in range(limits.MIN_DEGREE, self.full_rows() + 1)]
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
        return (value - limits.MIN_DEGREE) % size + limits.MIN_DEGREE

    def octave_shift(self, *, step=None):
        """Return how many octaves above its stored octave a note plays, for a degree past a known scale's size."""
        value = self.value(step=step)
        size = self.scale_size()
        if value is None or size is None or not self.has_gauge():
            return 0
        return (value - limits.MIN_DEGREE) // size

    def limit(self):
        """Return the highest degree that can be typed: the scale's size when it's known, or the largest scale the pattern can play in."""
        return self.scale_size() or self.editor.document().degree_limit(self.editor.item)

    # Keys.

    def keys(self):
        if self.editor.is_drum():
            result = [self.bind(self.KEYS.NOTE, action=self.type_letter, wants_key=True)]
        else:
            limit = self.limit()
            digits = keys_values.DIGITS if limit > int(keys_values.DIGITS[-1]) else tuple(str(number) for number in range(limits.MIN_DEGREE, limit + 1))
            result = [
                self.bind(self.KEYS.DEGREE, action=self.type_degree, wants_key=True, keys=digits, name=legends.MSG_DIGITS_RANGE_LABEL.format(low=limits.MIN_DEGREE, high=limit)),
                *self.adjust_keys(),
            ]
        if not self.editor.is_drum():
            result.append(self.bind(self.KEYS.TOGGLE_NOTE, action=self.toggle_note))
        if self.is_note():
            result.append(self.bind(self.KEYS.CLEAR, action=self.clear))
        return result

    def toggle_note(self):
        """Take the note off a step that has one, as Bksp does, or put the scale's first degree on an empty step."""
        if self.is_note():
            self.clear()
        else:
            self.set_value(limits.MIN_DEGREE)
            self.editor.fill_in()

    def type_degree(self, digit):
        number = self.editor.typed_number(digit=digit, low=limits.MIN_DEGREE, high=self.limit())
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
            self.set_value(max(min(current + offset, self.limit()), limits.MIN_DEGREE))
            self.editor.fill_in()
            return
        current = self.shown_degree()
        if current is None:
            # A rest nudged either way becomes the root, as it did before the gauge.
            degree = limits.MIN_DEGREE
        else:
            degree = current + offset
            if degree > size:
                self.editor.refuse(errors.ERR_TOP_OF_SCALE.format(scale=self.scale_name()))
                degree = size
            elif degree < limits.MIN_DEGREE:
                self.editor.refuse(errors.ERR_BOTTOM_OF_SCALE.format(scale=self.scale_name()))
                degree = limits.MIN_DEGREE
        if self.octave_shift():
            # A file's degree past the scale is written back within it, with its octave moved up to match.
            self.editor.set_value(value=self.editor.row_for(Row.OCTAVE).octave_now() + self.octave_shift(), row=Row.OCTAVE)
        self.set_value(degree)
        self.editor.fill_in()

    def clear(self):
        self.editor.document().change(self.editor.document().get_setlist().get_pattern(self.editor.item).clear_sound, self.editor.step)

    # Drawing.

    def cell_text(self, *, step):
        """Return the number under the gauge, marked when the gauge is too short to show it, or the drum note's letter."""
        if not self.has_gauge():
            value = self.value(step=step)
            return drawing.NOTHING if value is None else str(value)
        degree = self.shown_degree(step=step)
        if degree is None:
            return drawing.NOTHING
        return str(degree) + (marks.MSG_OVER_THE_TOP_MARK if degree > self.rows_shown() else drawing.NOTHING)

    def cell_lines(self, *, step):
        if not self.has_gauge():
            return [self.cell_text(step=step)]
        degree = self.shown_degree(step=step) or 0
        bars = [marks.MSG_GAUGE_BAR if degree >= level else drawing.NOTHING for level in range(self.rows_shown(), 0, -1)]
        return [*bars, self.cell_text(step=step)]
