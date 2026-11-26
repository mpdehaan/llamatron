# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What the pattern editor's two drawings share: the header, the window of steps, the rules and the Step row, and the description.

The grid shows as many steps as fit across the screen, from the editor's first_step, and moves
that window so that the cursor's step is always on it, so a long pattern scrolls sideways rather
than wrapping onto more blocks; the header's second line says which steps are on screen. The
piano roll (RollDrawing) and the rows (PatternDrawing) draw their own cells between the rules.
"""

from rich.text import Text

from llamatron.interface.forms import pattern_grid
from llamatron.interface.forms.pattern_grid import PatternRule, StepNumbers
from llamatron.interface.tracker import drawing
from llamatron.interface.tracker.drawing import fit, Style
from llamatron.interface.tracker.keyswitch_text import keyswitches_of, slots_in_words
from llamatron.interface.tracker.renderers import pattern_grid as grid_renderer
from llamatron.model.file.checks import fraction_text
from llamatron.model.objects.naming import words
from llamatron.model.schema.file_format import Row
from llamatron.user_strings import labels, marks, messages

# The lines after the grid: a blank line and the description.
LINES_AFTER_GRID = 2


class GridDrawing:
    """Draws the parts of a PatternEditor's screen that don't depend on what the cells hold."""

    __slots__ = ('_editor',)

    def __init__(self, editor):
        self._editor = editor

    def label_width(self):
        """Return how wide the labels down the left are: one width for both views, the wider, so that the grid stays put when Tab switches views."""
        return self._editor.label_width()

    def widest_label(self):
        """Return the width this drawing's own labels need, with a space either side."""
        raise NotImplementedError

    def steps_shown(self, width):
        """Return how many steps fit across the screen beside the labels."""
        return max((width - self.label_width() - 2) // (pattern_grid.CELL_WIDTH + 1), 1)

    def scroll_to_cursor(self, width):
        """Move the window of steps so that the cursor's step is on it, and return its first and last steps (the last excluded)."""
        return self._editor.window_of_steps(self.steps_shown(width))

    # The header.

    def scale_header(self):
        """Return what the header says about the scale, and after it the scale length the pattern was written for where a scale it plays under has another."""
        said = self.scale_said()
        editor = self._editor
        if editor.document().scales_unsuited_to_pattern(editor.item):
            return labels.MSG_WRITTEN_FOR.format(scale=said, length=editor.pattern().get_scale_length())
        return said

    def scale_said(self):
        """Return what the header says about the scale: the one the rows are drawn in, the note that there are several, or that drums need none."""
        editor = self._editor
        if editor.pattern().is_drum():
            return labels.MSG_SCALE_HEADER.format(scale=labels.MSG_NO_SCALE_NEEDED)
        document = editor.document()
        scales = document.scales_of_pattern(editor.item)
        if len(scales) > 1:
            return labels.MSG_SEVERAL_SCALES
        if not scales:
            return labels.MSG_SCALE_HEADER.format(scale=messages.MSG_NO_SCALE)
        if document.scale_name_says_what_it_is(scales[0]):
            return labels.MSG_SCALE_HEADER.format(scale=scales[0])
        return labels.MSG_SCALE_HEADER.format(scale=marks.MSG_SCALE_SHOWN.format(name=scales[0], notes=document.scale_notes_text(scales[0])))

    def header_extra(self):
        """Return what the header's second line says after the time signature, which each drawing decides."""
        raise NotImplementedError

    def header_lines(self, *, width, first, last):
        """Return the two header lines as aligned cells: Steps, Step size, Drum and Direction over Time and what the view adds."""
        pattern = self._editor.pattern()
        drum = marks.MSG_DRUM_ON if pattern.is_drum() else marks.MSG_DRUM_OFF
        whose = drawing.NOTHING if pattern.get_written_step_size() else marks.MSG_FROM_SONG_SHOWN
        step_size = marks.MSG_STEP_SIZE_SHOWN.format(size=fraction_text(self._editor.document().lengths().step_size(self._editor.item)), whose=whose)
        first_cells = [
            marks.MSG_STEPS_HEADER.format(steps=pattern.get_steps()), step_size, marks.MSG_DRUM_HEADER.format(drum=drum),
            marks.MSG_DIRECTION_HEADER.format(direction=words(pattern.get_direction())),
        ]
        signature_whose = drawing.NOTHING if pattern.get_written_time_signature() else marks.MSG_FROM_SONG_SHOWN
        second_cells = [marks.MSG_TIME_SIGNATURE_SHOWN.format(signature=self.time_signature().to_text(), whose=signature_whose), *self.header_extra()]
        header, second = header_cells(lines=[first_cells, second_cells])
        shown = self._editor.steps_shown_text(first=first, last=last)
        if shown:
            second = fit(text=second, width=width - len(shown) - 1) + drawing.SPACE + shown
        return [Text(header, no_wrap=True), Text(second, no_wrap=True)]

    def time_signature(self):
        """Return the time signature the pattern is drawn in: its own, or else the song's."""
        return self._editor.document().song().get_pattern_time_signature(self._editor.pattern())

    def beat_steps(self):
        """Return the steps, counted from 0, that start a beat of the time signature, worked out once per change of the set, since parsing the signature for every cell cost more than drawing them."""
        editor = self._editor
        document = editor.document()
        # The pattern's own time signature and step size, or else the song's signature and the set's step size.
        on = (editor.pattern(), document.song(), document.get_setlist())
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

    def drawn_rule(self, *, kind, first, last, boxed=None, joints=True):
        """Return a rule across the grid of a kind (forms/pattern_grid.py), edging the cursor's cell on the step boxed names."""
        rule = PatternRule(kind=kind, first=first, last=last, beats=self.beat_steps(), boxed=boxed, joints=joints)
        return grid_renderer.rule_line(rule=rule, label_width=self.label_width())

    def top_rule(self, *, first, last):
        return self.drawn_rule(kind=pattern_grid.TOP, first=first, last=last)

    def inner_rule(self, *, first, last, boxed=None):
        return self.drawn_rule(kind=pattern_grid.INNER, first=first, last=last, boxed=boxed)

    def bottom_rule(self, *, first, last, boxed=None, joints=True):
        return self.drawn_rule(kind=pattern_grid.BOTTOM, first=first, last=last, boxed=boxed, joints=joints)

    # The rules around a row with no dividers, like a section heading: the dividers above end in bottom tees, the ones below start in top tees, and between two such rows the rule is unbroken.

    def closing_rule(self, *, first, last):
        return self.drawn_rule(kind=pattern_grid.CLOSING, first=first, last=last)

    def opening_rule(self, *, first, last):
        return self.drawn_rule(kind=pattern_grid.OPENING, first=first, last=last)

    def plain_rule(self, *, first, last):
        return self.drawn_rule(kind=pattern_grid.PLAIN, first=first, last=last, joints=False)

    def step_line(self, *, first, last, sounding=None):
        """Return the line of step numbers, with the number of the step that sounds, if one is given, in the read head's light, as the rows view shows it."""
        numbers = StepNumbers(first=first, last=last, beats=self.beat_steps(), sounding=sounding)
        return grid_renderer.step_numbers_line(numbers=numbers, label_width=self.label_width())

    # The description of the step under the cursor.

    def describe(self):
        step = self._editor.step + 1
        if not self._editor.is_note():
            return (messages.MSG_DESCRIBE_TIED if self._editor.value(row=Row.TIE) else messages.MSG_DESCRIBE_EMPTY).format(step=step)
        document = self._editor.document()
        where = drawing.NOTHING if self._editor.is_drum() else messages.MSG_IN_SCALE.format(scale=document.pattern_scale(self._editor.item) or document.song().get_scale_name() or messages.MSG_NO_SCALE)
        played = self._editor.document().note_name(name=self._editor.item, step=self._editor.step)
        if self._editor.value(row=Row.GRAB):
            # What a grab step plays is whatever the other track played, moved by whatever else is at work, so the line names no note.
            sound = messages.MSG_GRABBED_SOUND
        elif played:
            sound = played + where
        else:
            sound = messages.MSG_DEGREE_WITHOUT_SCALE.format(degree=self._editor.value(row=Row.DEGREE))
        chord = self._editor.value(row=Row.CHORD)
        chord_text = messages.MSG_DESCRIBE_CHORD.format(chord=chord) if chord is not None else drawing.NOTHING
        gate = str(fraction_text(self._editor.gate_now())) + labels.MSG_DOT_NAMES.get(self._editor.value(row=Row.DOT), drawing.NOTHING)
        if self._editor.gate_is_overridden():
            gate += messages.MSG_DESCRIBE_GATE_OVERRIDDEN
        return messages.MSG_DESCRIBE_NOTE.format(step=step, sound=sound, gate=gate, chord=chord_text) + self.keyswitches_described()

    def keyswitches_described(self):
        """Return the end of the description that names the cursor's keyswitches, each by its instrument's name for it or by its number, or nothing for none."""
        slots = self._editor.value(row=Row.KEYSWITCH)
        if not slots:
            return drawing.NOTHING
        instrument, _ = self._editor.keyswitch_instrument()
        return messages.MSG_DESCRIBE_KEYSWITCHES.format(names=slots_in_words(keyswitches=keyswitches_of(instrument), slots=slots))

    def with_description(self, *, lines, width, height):
        """Return the header and grid lines with the description after them, set apart by a blank line unless the console is too short for one."""
        description = Text(drawing.SPACE + fit(text=self.describe(), width=width - 1), style=Style.BOLD)
        spacer = [Text(drawing.NOTHING)] if len(lines) + LINES_AFTER_GRID <= height else []
        return lines + spacer + [description]


def header_cells(*, lines):
    """Return the header lines laid out as columns of cells: each column as wide as its widest cell, so that the cells of one line start under the other's.

    A line's last cell is written as it is, so a long last cell, like the rows view's section hint, runs on without widening a column.
    """
    widths = {}
    for cells in lines:
        for column, cell in enumerate(cells[:-1]):
            widths[column] = max(widths.get(column, 0), len(cell))
    return [header_line(cells=cells, widths=widths) for cells in lines]


def header_line(*, cells, widths):
    """Return one line of the header, each cell but the last padded to its column's width, the last as it is."""
    padded_cells = [cell.ljust(widths[column]) for column, cell in enumerate(cells[:-1])]
    return marks.MSG_HEADER_INDENT + marks.MSG_HEADER_CELL_GAP.join([*padded_cells, cells[-1]])
