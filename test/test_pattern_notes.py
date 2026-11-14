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
"""A pattern's notes as a piano roll handles them, on Pattern alone, with no tracker and no document.

composition/pattern_notes.py is the part of Pattern that knows how a note, its gate and its ties
make the one bar a piano roll draws, and how to draw, lengthen, shorten and cut that bar. How
many steps a gate reaches depends on how long a step is, which a pattern may take from its set,
so the caller passes the step size, and the tests here ask the same pattern at several.
"""

import unittest

from llamatron.composition.file_format import Accidental, ChordSymbol, GateModifier, PatternSetting, Row, Tension
from llamatron.composition.named_scale import NamedScale, scale_type_name
from llamatron.composition.pattern import Pattern
from llamatron.composition.pattern_notes import SPLIT_ROWS, whole_steps_down, whole_steps_up
from llamatron.music.note import NoteName
from llamatron.music.scale import ScaleType
from llamatron.support.rational import Rational

HERE = 'here'
WHOLE = Rational(1, 1)
HALF = Rational(1, 2)
QUARTER = Rational(1, 4)
EIGHTH = Rational(1, 8)
SIXTEENTH = Rational(1, 16)
THIRTY_SECOND = Rational(1, 32)
THREE_THIRTY_SECONDS = Rational(3, 32)
# The same lengths as a file writes them.
WRITTEN_HALF = '1/2'
WRITTEN_QUARTER = '1/4'
WRITTEN_EIGHTH = '1/8'
WRITTEN_THREE_SIXTEENTHS = '3/16'
WRITTEN_SIXTEENTH = '1/16'
WRITTEN_THIRTY_SECOND = '1/32'
WRITTEN_THREE_THIRTY_SECONDS = '3/32'
WRITTEN_FIVE_THIRTY_SECONDS = '5/32'
WRITTEN_THREE_QUARTERS = '3/4'
WRITTEN_WHOLE = 1
STEPS = 8
OCTAVE = 4
A_VELOCITY = 90
MINOR = scale_type_name(ScaleType.MINOR)


def pattern_of(*, steps=STEPS, **rows):
    """Return a pattern from rows given by their names, each as short as its last value: the rest of a row is blank."""
    data = {PatternSetting.STEPS: steps}
    for row, values in rows.items():
        blank = False if row == Row.TIE or row == Row.GRAB else None
        data[row] = [*values, *[blank] * (steps - len(values))]
    return Pattern.from_data(data=data, where=HERE)


def ties(*steps, count=STEPS):
    """Return a Tie row with the given steps tied."""
    return [step in steps for step in range(count)]


def c_major():
    return NamedScale(root=NoteName.C, kind=scale_type_name(ScaleType.MAJOR))


class TestWholeSteps(unittest.TestCase):

    def test_a_gates_reach_counts_a_part_of_a_step_as_one(self):
        self.assertEqual(whole_steps_up(length=SIXTEENTH, step_size=SIXTEENTH), 1)
        self.assertEqual(whole_steps_up(length=THREE_THIRTY_SECONDS, step_size=SIXTEENTH), 2)
        self.assertEqual(whole_steps_up(length=THIRTY_SECOND, step_size=SIXTEENTH), 1)
        self.assertEqual(whole_steps_up(length=QUARTER, step_size=SIXTEENTH), 4)
        self.assertEqual(whole_steps_up(length=QUARTER, step_size=EIGHTH), 2)

    def test_an_entry_size_is_placed_in_the_whole_steps_that_fit_and_at_least_one(self):
        self.assertEqual(whole_steps_down(length=SIXTEENTH, step_size=SIXTEENTH), 1)
        self.assertEqual(whole_steps_down(length=THREE_THIRTY_SECONDS, step_size=SIXTEENTH), 1)
        self.assertEqual(whole_steps_down(length=THIRTY_SECOND, step_size=SIXTEENTH), 1)
        self.assertEqual(whole_steps_down(length=QUARTER, step_size=SIXTEENTH), 4)
        self.assertEqual(whole_steps_down(length=WHOLE, step_size=QUARTER), 4)


class TestReadingNotes(unittest.TestCase):

    def test_a_gates_span_depends_on_how_long_a_step_is(self):
        pattern = pattern_of(degree=[1], gate=[WRITTEN_QUARTER])
        self.assertEqual(pattern.note_span(step=0, step_size=SIXTEENTH), 4)
        self.assertEqual(pattern.note_span(step=0, step_size=EIGHTH), 2)
        self.assertEqual(pattern.note_span(step=0, step_size=QUARTER), 1)
        # A gate shorter than a step still covers the step the note is on.
        self.assertEqual(pattern.note_span(step=0, step_size=HALF), 1)

    def test_a_span_is_the_ties_or_the_gate_in_whole_steps_and_the_ties_after(self):
        self.assertEqual(pattern_of(degree=[1]).note_span(step=0, step_size=SIXTEENTH), 1)
        self.assertEqual(pattern_of(degree=[1], tie=ties(1, 2)).note_span(step=0, step_size=SIXTEENTH), 3)
        # A gate that ends inside a step reaches into it.
        self.assertEqual(pattern_of(degree=[1], gate=[WRITTEN_THREE_THIRTY_SECONDS]).note_span(step=0, step_size=SIXTEENTH), 2)
        # A tie right after the gate's reach holds the note on.
        self.assertEqual(pattern_of(degree=[1], gate=[WRITTEN_EIGHTH], tie=ties(2)).note_span(step=0, step_size=SIXTEENTH), 3)
        # Ties that run further than the gate are the span.
        self.assertEqual(pattern_of(degree=[1], gate=[WRITTEN_SIXTEENTH], tie=ties(1, 2, 3)).note_span(step=0, step_size=SIXTEENTH), 4)
        # The Dot row makes the gate half as long again.
        self.assertEqual(pattern_of(degree=[1], gate=[WRITTEN_EIGHTH], dot=[GateModifier.DOTTED]).note_span(step=0, step_size=SIXTEENTH), 3)
        # A gate is cut at the end of the pattern.
        self.assertEqual(pattern_of(degree=[None, None, 1], gate=[None, None, WRITTEN_WHOLE]).note_span(step=2, step_size=SIXTEENTH), STEPS - 2)

    def test_each_step_is_covered_by_the_note_sounding_through_it(self):
        pattern = pattern_of(degree=[1, None, None, 3, None, 5], gate=[WRITTEN_HALF, None, None, WRITTEN_EIGHTH], tie=ties(6))
        # A later note always shows over an earlier one's gate, and steps nothing covers are left out.
        self.assertEqual(pattern.covering_notes(step_size=SIXTEENTH), {0: 0, 1: 0, 2: 0, 3: 3, 4: 3, 5: 5, 6: 5})
        # With steps twice as long, the eighth note on step 3 covers its own step alone.
        self.assertEqual(pattern.covering_notes(step_size=EIGHTH), {0: 0, 1: 0, 2: 0, 3: 3, 5: 5, 6: 5})
        self.assertEqual(pattern_of().covering_notes(step_size=SIXTEENTH), {})

    def test_a_grab_step_with_no_degree_is_a_note(self):
        pattern = pattern_of(degree=[1], gate=[WRITTEN_QUARTER], grab=[False, False, True])
        self.assertEqual(pattern.covering_notes(step_size=SIXTEENTH), {0: 0, 1: 0, 2: 2})

    def test_a_gate_that_ends_inside_a_step_fills_part_of_its_last_cell(self):
        self.assertEqual(pattern_of(degree=[1], gate=[WRITTEN_THREE_THIRTY_SECONDS]).partial_cell(step=0, step_size=SIXTEENTH), HALF)
        self.assertEqual(pattern_of(degree=[1], gate=[WRITTEN_THIRTY_SECOND]).partial_cell(step=0, step_size=SIXTEENTH), HALF)
        self.assertEqual(pattern_of(degree=[1], gate=[WRITTEN_THREE_SIXTEENTHS]).partial_cell(step=0, step_size=EIGHTH), HALF)
        self.assertEqual(pattern_of(degree=[1], gate=[WRITTEN_FIVE_THIRTY_SECONDS]).partial_cell(step=0, step_size=EIGHTH), QUARTER)

    def test_the_last_cell_is_full_when_the_gate_ends_on_a_step_or_something_else_ends_the_bar(self):
        self.assertIsNone(pattern_of(degree=[1]).partial_cell(step=0, step_size=SIXTEENTH))
        self.assertIsNone(pattern_of(degree=[1], gate=[WRITTEN_EIGHTH]).partial_cell(step=0, step_size=SIXTEENTH))
        # The same gate is whole steps at one step size and not at another.
        self.assertIsNone(pattern_of(degree=[1], gate=[WRITTEN_THREE_SIXTEENTHS]).partial_cell(step=0, step_size=SIXTEENTH))
        # A tie after the gate's reach holds the note to the end of the tied step.
        self.assertIsNone(pattern_of(degree=[1], gate=[WRITTEN_THREE_THIRTY_SECONDS], tie=ties(2)).partial_cell(step=0, step_size=SIXTEENTH))
        # The pattern's end cuts the gate before the step it would have ended inside.
        self.assertIsNone(pattern_of(steps=2, degree=[1], gate=[WRITTEN_FIVE_THIRTY_SECONDS]).partial_cell(step=0, step_size=SIXTEENTH))

    def test_a_scale_chords_tones_are_degrees_above_the_steps_whatever_the_scale(self):
        pattern = pattern_of(degree=[1, 5], chord=[ChordSymbol.SCALE_TRIAD, ChordSymbol.SCALE_SEVENTH], accidental=[None, Accidental.SHARP])
        self.assertEqual(pattern.chord_tones(step=0, octave=OCTAVE, scale=None), [(3, OCTAVE, None), (5, OCTAVE, None)])
        self.assertEqual(pattern.chord_tones(step=1, octave=OCTAVE, scale=None), [(7, OCTAVE, Accidental.SHARP), (9, OCTAVE, Accidental.SHARP), (11, OCTAVE, Accidental.SHARP)])
        self.assertEqual(pattern.chord_tones(step=0, octave=OCTAVE, scale=c_major()), [(3, OCTAVE, None), (5, OCTAVE, None)])

    def test_a_named_chords_tones_are_placed_in_the_scale_and_need_one(self):
        pattern = pattern_of(degree=[1, 5], chord=[ChordSymbol.MAJOR, ChordSymbol.DOMINANT7])
        self.assertEqual(pattern.chord_tones(step=0, octave=OCTAVE, scale=c_major()), [(3, OCTAVE, None), (5, OCTAVE, None)])
        # G's dominant seventh in C major is B, then D and F in the octave above.
        self.assertEqual(pattern.chord_tones(step=1, octave=OCTAVE, scale=c_major()), [(7, OCTAVE, None), (2, OCTAVE + 1, None), (4, OCTAVE + 1, None)])
        self.assertEqual(pattern.chord_tones(step=1, octave=OCTAVE, scale=None), [])

    def test_a_chord_of_c_minor_on_c_major_takes_a_flat(self):
        pattern = pattern_of(degree=[1], chord=[ChordSymbol.MINOR])
        self.assertEqual(pattern.chord_tones(step=0, octave=OCTAVE, scale=c_major()), [(2, OCTAVE, Accidental.SHARP), (5, OCTAVE, None)])

    def test_a_step_with_no_chord_or_no_note_has_no_tones(self):
        pattern = pattern_of(degree=[1, None], chord=[None, ChordSymbol.MAJOR])
        self.assertEqual(pattern.chord_tones(step=0, octave=OCTAVE, scale=c_major()), [])
        self.assertEqual(pattern.chord_tones(step=1, octave=OCTAVE, scale=c_major()), [])


class TestDrawingNotes(unittest.TestCase):

    def test_a_note_of_whole_steps_is_a_degree_and_ties(self):
        pattern = pattern_of()
        pattern.draw_note(step=1, degree=3, octave=OCTAVE, length=QUARTER, step_size=SIXTEENTH, accidental=Accidental.FLAT)
        self.assertEqual(pattern.get_row(Row.DEGREE), [None, 3, *[None] * 6])
        self.assertEqual(pattern.get_value(row=Row.OCTAVE, step=1), OCTAVE)
        self.assertEqual(pattern.get_value(row=Row.ACCIDENTAL, step=1), Accidental.FLAT)
        self.assertEqual(pattern.get_row(Row.TIE), ties(2, 3, 4))
        self.assertIsNone(pattern.get_value(row=Row.GATE, step=1))
        self.assertEqual(pattern.note_span(step=1, step_size=SIXTEENTH), 4)

    def test_the_same_length_is_fewer_steps_when_the_steps_are_longer(self):
        pattern = pattern_of()
        pattern.draw_note(step=0, degree=1, octave=OCTAVE, length=QUARTER, step_size=EIGHTH)
        self.assertEqual(pattern.get_row(Row.TIE), ties(1))
        pattern = pattern_of()
        pattern.draw_note(step=0, degree=1, octave=OCTAVE, length=QUARTER, step_size=QUARTER)
        self.assertIsNone(pattern.get_row(Row.TIE))
        self.assertIsNone(pattern.get_value(row=Row.GATE, step=0))

    def test_a_note_shorter_than_a_step_is_written_as_a_gate(self):
        pattern = pattern_of()
        pattern.draw_note(step=2, degree=1, octave=OCTAVE, length=THIRTY_SECOND, step_size=SIXTEENTH)
        self.assertEqual(pattern.get_value(row=Row.GATE, step=2), WRITTEN_THIRTY_SECOND)
        self.assertIsNone(pattern.get_row(Row.TIE))
        pattern.draw_note(step=4, degree=1, octave=OCTAVE, length=EIGHTH, step_size=QUARTER)
        self.assertEqual(pattern.get_value(row=Row.GATE, step=4), WRITTEN_EIGHTH)

    def test_a_length_between_whole_steps_is_placed_in_the_whole_steps_that_fit(self):
        pattern = pattern_of()
        pattern.draw_note(step=0, degree=1, octave=OCTAVE, length=THREE_THIRTY_SECONDS, step_size=SIXTEENTH)
        self.assertIsNone(pattern.get_value(row=Row.GATE, step=0))
        self.assertIsNone(pattern.get_row(Row.TIE))

    def test_a_note_drawn_on_a_chords_step_moves_the_root_and_keeps_the_chord_and_its_length(self):
        pattern = pattern_of(
            degree=[1], chord=[ChordSymbol.DOMINANT7], tension=[(Tension.FLAT_NINTH,)], inversion=[1], chord_scale=[MINOR], velocity=[A_VELOCITY],
            tie=ties(1, 2), accidental=[Accidental.SHARP],
        )
        pattern.draw_note(step=0, degree=3, octave=OCTAVE + 1, length=SIXTEENTH, step_size=SIXTEENTH)
        self.assertEqual([pattern.get_value(row=row, step=0) for row in (Row.DEGREE, Row.OCTAVE, Row.ACCIDENTAL)], [3, OCTAVE + 1, None])
        kept = (Row.CHORD, Row.TENSION, Row.INVERSION, Row.CHORD_SCALE, Row.VELOCITY)
        self.assertEqual([pattern.get_value(row=row, step=0) for row in kept], [ChordSymbol.DOMINANT7, (Tension.FLAT_NINTH,), 1, MINOR, A_VELOCITY])
        # The note is as long as it was: its two ties still hold it.
        self.assertEqual([bool(pattern.get_value(row=Row.TIE, step=step)) for step in (1, 2)], [True, True])
        # A note with no chord is replaced by the note drawn, as ever, and so is a chord's note once it is erased.
        pattern.clear_sound(0)
        pattern.draw_note(step=0, degree=5, octave=OCTAVE, length=SIXTEENTH, step_size=SIXTEENTH)
        self.assertEqual((pattern.get_value(row=Row.DEGREE, step=0), pattern.get_value(row=Row.CHORD, step=0)), (5, None))

    def test_a_note_drawn_near_the_end_stops_at_the_end(self):
        pattern = pattern_of()
        pattern.draw_note(step=STEPS - 2, degree=1, octave=OCTAVE, length=WHOLE, step_size=SIXTEENTH)
        self.assertEqual(pattern.get_row(Row.TIE), ties(STEPS - 1))

    def test_drawing_under_a_gate_cuts_the_gate_where_the_new_note_starts(self):
        pattern = pattern_of(degree=[1], gate=[WRITTEN_QUARTER], dot=[GateModifier.DOTTED])
        self.assertEqual(pattern.note_span(step=0, step_size=SIXTEENTH), 6)
        pattern.draw_note(step=3, degree=5, octave=OCTAVE, length=SIXTEENTH, step_size=SIXTEENTH)
        self.assertEqual(pattern.get_value(row=Row.GATE, step=0), WRITTEN_THREE_SIXTEENTHS)
        self.assertIsNone(pattern.get_value(row=Row.DOT, step=0))
        self.assertEqual(pattern.covering_notes(step_size=SIXTEENTH), {0: 0, 1: 0, 2: 0, 3: 3})

    def test_a_gate_cut_to_a_whole_number_of_whole_notes_is_written_as_a_number(self):
        pattern = pattern_of(degree=[1], gate=[2])
        self.assertTrue(pattern.cut_gate_before(step=1, step_size=WHOLE))
        self.assertEqual(pattern.get_value(row=Row.GATE, step=0), WRITTEN_WHOLE)

    def test_a_gate_is_cut_only_when_it_reaches_the_step(self):
        pattern = pattern_of(degree=[1, None, None, None, 2], gate=[WRITTEN_EIGHTH], tie=ties(5, 6))
        before = pattern.revision()
        # Nothing covers step 3, step 0 is the note's own, and the note on step 4 reaches step 6 by ties alone.
        for step in (3, 0, 6):
            with self.subTest(step=step):
                self.assertFalse(pattern.cut_gate_before(step=step, step_size=SIXTEENTH))
        self.assertEqual(pattern.revision(), before)
        self.assertTrue(pattern.cut_gate_before(step=1, step_size=SIXTEENTH))
        self.assertEqual(pattern.get_value(row=Row.GATE, step=0), WRITTEN_SIXTEENTH)
        self.assertNotEqual(pattern.revision(), before)

    def test_drawing_inside_a_tied_note_leaves_what_it_held_beyond_as_a_note_of_its_own(self):
        pattern = pattern_of(degree=[1], octave=[OCTAVE], velocity=[A_VELOCITY], tie=ties(1, 2, 3, 4))
        pattern.draw_note(step=1, degree=5, octave=OCTAVE + 1, length=EIGHTH, step_size=SIXTEENTH)
        self.assertEqual(pattern.get_row(Row.DEGREE), [1, 5, None, 1, *[None] * 4])
        self.assertEqual(pattern.get_row(Row.TIE), ties(2, 4))
        for row in SPLIT_ROWS:
            with self.subTest(row=row):
                self.assertEqual(pattern.get_value(row=row, step=3), pattern.get_value(row=row, step=0))


class TestDraggingANotesEnd(unittest.TestCase):

    def test_a_note_shorter_than_a_step_becomes_a_whole_one_first(self):
        pattern = pattern_of(degree=[1], gate=[WRITTEN_THIRTY_SECOND], dot=[GateModifier.DOTTED])
        self.assertTrue(pattern.lengthen_note(start=0, step_size=SIXTEENTH))
        self.assertIsNone(pattern.get_value(row=Row.GATE, step=0))
        self.assertIsNone(pattern.get_value(row=Row.DOT, step=0))
        self.assertIsNone(pattern.get_row(Row.TIE))
        self.assertTrue(pattern.lengthen_note(start=0, step_size=SIXTEENTH))
        self.assertEqual(pattern.get_row(Row.TIE), ties(1))

    def test_what_is_short_depends_on_how_long_a_step_is(self):
        pattern = pattern_of(degree=[1], gate=[WRITTEN_EIGHTH])
        self.assertTrue(pattern.lengthen_note(start=0, step_size=QUARTER))
        self.assertIsNone(pattern.get_value(row=Row.GATE, step=0))
        pattern = pattern_of(degree=[1], gate=[WRITTEN_EIGHTH])
        self.assertTrue(pattern.lengthen_note(start=0, step_size=SIXTEENTH))
        # The gate reaches two steps, so the tie goes on the step after them and the gate stays.
        self.assertEqual(pattern.get_value(row=Row.GATE, step=0), WRITTEN_EIGHTH)
        self.assertEqual(pattern.get_row(Row.TIE), ties(2))
        self.assertEqual(pattern.note_span(step=0, step_size=SIXTEENTH), 3)

    def test_a_note_stops_at_the_next_note_and_at_the_end_and_nothing_changes(self):
        pattern = pattern_of(steps=3, degree=[1, None, 2])
        self.assertTrue(pattern.lengthen_note(start=0, step_size=SIXTEENTH))
        before = pattern.revision()
        self.assertFalse(pattern.lengthen_note(start=0, step_size=SIXTEENTH))
        self.assertFalse(pattern.lengthen_note(start=2, step_size=SIXTEENTH))
        self.assertEqual(pattern.revision(), before)
        self.assertEqual(pattern.get_row(Row.TIE), ties(1, count=3))

    def test_a_grab_step_stops_a_note_too(self):
        pattern = pattern_of(degree=[1], grab=[False, True])
        self.assertFalse(pattern.lengthen_note(start=0, step_size=SIXTEENTH))

    def test_shortening_takes_the_last_tie_first_and_then_steps_off_the_gate(self):
        pattern = pattern_of(degree=[1], gate=[WRITTEN_THREE_SIXTEENTHS], tie=ties(3, 4))
        self.assertEqual(pattern.note_span(step=0, step_size=SIXTEENTH), 5)
        self.assertTrue(pattern.shorten_note(start=0, step_size=SIXTEENTH))
        self.assertEqual(pattern.get_row(Row.TIE), ties(3))
        self.assertTrue(pattern.shorten_note(start=0, step_size=SIXTEENTH))
        self.assertEqual(pattern.get_row(Row.TIE), ties())
        self.assertEqual(pattern.get_value(row=Row.GATE, step=0), WRITTEN_THREE_SIXTEENTHS)
        self.assertTrue(pattern.shorten_note(start=0, step_size=SIXTEENTH))
        self.assertEqual(pattern.get_value(row=Row.GATE, step=0), WRITTEN_EIGHTH)
        # A gate of one step is written blank.
        self.assertTrue(pattern.shorten_note(start=0, step_size=SIXTEENTH))
        self.assertIsNone(pattern.get_value(row=Row.GATE, step=0))

    def test_a_note_of_one_step_stays_and_nothing_changes(self):
        for rows in ({Row.DEGREE: [1]}, {Row.DEGREE: [1], Row.GATE: [WRITTEN_SIXTEENTH]}, {Row.DEGREE: [1], Row.GATE: [WRITTEN_THIRTY_SECOND]}):
            with self.subTest(rows=rows):
                pattern = pattern_of(**rows)
                before = pattern.revision()
                self.assertFalse(pattern.shorten_note(start=0, step_size=SIXTEENTH))
                self.assertEqual(pattern.revision(), before)

    def test_a_step_off_a_gate_is_a_step_of_the_step_size_given(self):
        pattern = pattern_of(degree=[1], gate=[WRITTEN_THREE_QUARTERS])
        self.assertTrue(pattern.shorten_note(start=0, step_size=QUARTER))
        self.assertEqual(pattern.get_value(row=Row.GATE, step=0), WRITTEN_HALF)
        self.assertTrue(pattern.shorten_note(start=0, step_size=QUARTER))
        self.assertIsNone(pattern.get_value(row=Row.GATE, step=0))
        self.assertFalse(pattern.shorten_note(start=0, step_size=QUARTER))
        # A gate that ends inside a step loses a whole step, which can leave less than one.
        pattern = pattern_of(degree=[1], gate=[WRITTEN_THREE_THIRTY_SECONDS])
        self.assertTrue(pattern.shorten_note(start=0, step_size=SIXTEENTH))
        self.assertEqual(pattern.get_value(row=Row.GATE, step=0), WRITTEN_THIRTY_SECOND)

    def test_lengthening_and_shortening_undo_each_other(self):
        pattern = pattern_of(degree=[1, None, None, None, 2])
        for _ in range(3):
            self.assertTrue(pattern.lengthen_note(start=0, step_size=SIXTEENTH))
        self.assertEqual(pattern.note_span(step=0, step_size=SIXTEENTH), 4)
        for _ in range(3):
            self.assertTrue(pattern.shorten_note(start=0, step_size=SIXTEENTH))
        # A row of all blanks is left out of the data, so the pattern is back to what it was.
        self.assertEqual(pattern.to_data(), pattern_of(degree=[1, None, None, None, 2]).to_data())

    def test_the_accidental_goes_round_natural_sharp_and_flat(self):
        pattern = pattern_of(degree=[1])
        seen = []
        for _ in range(3):
            pattern.cycle_accidental(0)
            seen.append(pattern.get_value(row=Row.ACCIDENTAL, step=0))
        self.assertEqual(seen, [Accidental.SHARP, Accidental.FLAT, None])


if __name__ == '__main__':
    unittest.main()
