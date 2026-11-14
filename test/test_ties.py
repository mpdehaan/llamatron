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

"""The Tie row: a tied step holds the note before it through the step, within a pass and from one pass into the next."""

import unittest
from fractions import Fraction

from llamatron.composition.file_format import (
    ClipSlotSetting, Direction, PatternSetting, Row, ScaleSetting, SceneSetting, Section, SongSetting, TrackSetting,
)
from llamatron.composition.named_scale import scale_type_name
from llamatron.composition.song_file_error import SongFileError
from llamatron.music.note import NoteName
from llamatron.exporters.timing import timed_events
from rendering import render_data, setlist_from_data, song_from_data
from llamatron.music.scale import ScaleType

# Every pattern plays in C major from middle C, MIDI note 60, with a quarter note a step.
C3 = 60
E3 = 64
STEP = Fraction(1, 4)
STEP_SIZE = '1/4'
OCTAVE = 5
DEGREE_C = 1
DEGREE_E = 3
NO_TIE = False
TIE = True

# Names the tests give to their own things, and other values they use.
LEAD = 'lead'
MAIN = 'main'
X = 'x'
EIGHTH = '1/8'
LONG = 'long'
OTHER = 'other'
G = 'g'
GRABBER = 'grabber'
STEP_2 = 'step 2'
YES = 'yes'


def pattern(degrees, ties, **rows):
    """Return a pattern from a degree and a tie for each step."""
    steps = len(degrees)
    return {
        PatternSetting.STEPS: steps, PatternSetting.STEP_SIZE: STEP_SIZE, Row.DEGREE: degrees,
        Row.OCTAVE: [OCTAVE] * steps, Row.TIE: ties, **rows,
    }


def song(patterns, repeat=1, **clip_slot):
    clip_slots = {LEAD: {ClipSlotSetting.PATTERN: X, ClipSlotSetting.REPEAT: repeat, **clip_slot}}
    return {
        Section.SCALES: {MAIN: {ScaleSetting.ROOT: NoteName.C, ScaleSetting.TYPE: scale_type_name(ScaleType.MAJOR)}}, SongSetting.SCALE: MAIN,
        Section.PATTERNS: patterns, Section.TRACKS: {LEAD: {}}, Section.SCENES: [{SceneSetting.TRACKS: clip_slots}],
    }


def played(data):
    """Return (start, end, pitch) for every note the lead plays, in whole notes, in time order."""
    grid = render_data(data)
    clip = grid.get_clip(row=grid.get_rows()[0], column=grid.get_columns()[0])
    return [(start, end, pitch) for start, end, pitch, _ in sorted(timed_events(clip=clip, scale=clip.get_scale())[0])]


def one(degrees, ties, repeat=1, **rows):
    return played(song({X: pattern(degrees, ties, **rows)}, repeat=repeat))


class TestWithinAPass(unittest.TestCase):

    def test_each_tie_holds_the_note_one_step_longer(self):
        # A note on one step and three ties make a quarter note of sixteenths, here four steps long.
        found = one([DEGREE_C, None, None, None], [NO_TIE, TIE, TIE, TIE])
        self.assertEqual(found, [(0, 4 * STEP, C3)])

    def test_the_note_ends_where_the_ties_stop(self):
        found = one([DEGREE_C, None, None, None], [NO_TIE, TIE, NO_TIE, NO_TIE])
        self.assertEqual(found, [(0, 2 * STEP, C3)])

    def test_a_tie_after_an_empty_step_is_silence(self):
        found = one([DEGREE_C, None, None, None], [NO_TIE, NO_TIE, TIE, TIE])
        self.assertEqual(found, [(0, STEP, C3)])

    def test_the_ties_win_over_the_gate_whether_it_is_longer_or_shorter(self):
        # The note lasts to the end of its ties, so the bar the editor draws is what plays, whatever the gate says.
        whole_note = '1'
        found = one([DEGREE_C, None, None, None], [NO_TIE, TIE, NO_TIE, NO_TIE], gate=[whole_note, None, None, None])
        self.assertEqual(found, [(0, 2 * STEP, C3)])
        short_gate = EIGHTH
        found = one([DEGREE_C, None, None, None], [NO_TIE, TIE, NO_TIE, NO_TIE], gate=[short_gate, None, None, None])
        self.assertEqual(found, [(0, 2 * STEP, C3)])

    def test_a_gate_with_no_ties_after_it_still_plays_as_written(self):
        whole_note = '1'
        found = one([DEGREE_C, None, None, None], [NO_TIE, NO_TIE, NO_TIE, NO_TIE], gate=[whole_note, None, None, None])
        self.assertEqual(found, [(0, 4 * STEP, C3)])

    def test_a_ratchet_whose_gate_reached_past_the_tie_keeps_its_count(self):
        # Two slices of a whole-note gate would be a half note each; the tie cuts the sound to two steps, shared equally.
        whole_note = '1'
        found = one([DEGREE_C, None, None, None], [NO_TIE, TIE, NO_TIE, NO_TIE], gate=[whole_note, None, None, None], ratchet=[2, None, None, None])
        self.assertEqual(found, [(0, STEP, C3), (STEP, 2 * STEP, C3)])

    def test_a_tie_holds_a_whole_chord(self):
        found = one([DEGREE_C, None], [NO_TIE, TIE], chord=[3, None])
        self.assertEqual(sorted(found), [(0, 2 * STEP, C3), (0, 2 * STEP, E3), (0, 2 * STEP, 67)])

    def test_a_tie_holds_the_last_slice_of_a_ratchet(self):
        found = one([DEGREE_C, None], [NO_TIE, TIE], ratchet=[2, None])
        self.assertEqual(found, [(0, STEP / 2, C3), (STEP / 2, 2 * STEP, C3)])

    def test_a_tie_after_a_note_probability_dropped_is_silence(self):
        never = 0
        found = one([DEGREE_C, None, DEGREE_E], [NO_TIE, TIE, NO_TIE], probability=[never, None, None])
        self.assertEqual(found, [(2 * STEP, 3 * STEP, E3)])

    def test_a_tied_step_still_sends_cc_values(self):
        data = song({X: pattern([DEGREE_C, None], [NO_TIE, TIE], cc1=[None, 50])})
        data[Section.TRACKS][LEAD] = {TrackSetting.CC: [1, None, None, None]}
        grid = render_data(data)
        clip = grid.get_clip(row=grid.get_rows()[0], column=grid.get_columns()[0])
        self.assertEqual([(control.get_time(), control.get_value()) for control in clip.get_controls()], [(STEP, 50)])


class TestAcrossPasses(unittest.TestCase):

    def test_a_tie_at_the_start_of_a_repeat_continues_the_last_note_of_the_pass_before(self):
        found = one([None, DEGREE_C, None, None], [TIE, NO_TIE, TIE, TIE], repeat=2)
        pass_length = 4 * STEP
        self.assertEqual(found, [(STEP, pass_length + STEP, C3), (pass_length + STEP, 2 * pass_length, C3)])

    def test_a_tie_at_the_very_start_of_a_clip_is_silence(self):
        found = one([None, DEGREE_C], [TIE, NO_TIE])
        self.assertEqual(found, [(STEP, 2 * STEP, C3)])

    def test_a_tie_into_a_rest_at_the_end_of_the_pass_before_is_silence(self):
        found = one([None, DEGREE_C, None, None], [TIE, NO_TIE, NO_TIE, NO_TIE], repeat=2)
        self.assertEqual(found, [(STEP, 2 * STEP, C3), (5 * STEP, 6 * STEP, C3)])

    def test_the_notes_after_a_tie_still_start_on_time(self):
        found = one([None, DEGREE_C, DEGREE_E, None], [TIE, NO_TIE, NO_TIE, TIE], repeat=2)
        self.assertEqual([start for start, _, _ in found], [STEP, 2 * STEP, 5 * STEP, 6 * STEP])

    def test_a_looping_clip_ties_across_its_passes_too(self):
        patterns = {X: pattern([None, DEGREE_C], [TIE, NO_TIE]), LONG: pattern([DEGREE_E] * 4, [NO_TIE] * 4)}
        data = song(patterns, loop=True)
        data[Section.TRACKS][OTHER] = {}
        data[Section.SCENES][0][SceneSetting.TRACKS][OTHER] = {ClipSlotSetting.PATTERN: LONG}
        found = played(data)
        self.assertEqual(found, [(STEP, 3 * STEP, C3), (3 * STEP, 4 * STEP, C3)])

    def test_a_grab_hears_a_tied_note_as_still_sounding(self):
        patterns = {X: pattern([DEGREE_C, None, None, None], [NO_TIE, TIE, TIE, TIE]), G: pattern([None, None, DEGREE_E, None], [NO_TIE] * 4, grab=[False, False, True, False])}
        data = song(patterns)
        data[Section.TRACKS][GRABBER] = {}
        data[Section.SCENES][0][SceneSetting.TRACKS][GRABBER] = {ClipSlotSetting.PATTERN: G, ClipSlotSetting.GRAB_TRACK: LEAD}
        grid = render_data(data)
        clip = grid.get_clip(row=grid.get_rows()[0], column=[track for track in grid.get_columns() if track.get_name() == GRABBER][0])
        self.assertEqual([pitch for _, _, pitch, _ in timed_events(clip=clip, scale=clip.get_scale())[0]], [C3])

    def test_a_reversed_pattern_ties_in_the_order_it_plays(self):
        # Written as C then a tie, but played backwards the tie comes first, with nothing before it.
        found = one([DEGREE_C, None], [NO_TIE, TIE], direction=Direction.REVERSE_B)
        self.assertEqual(found, [(STEP, 2 * STEP, C3)])


class TestTheFile(unittest.TestCase):

    def test_ties_save_and_load(self):
        data = song({X: pattern([DEGREE_C, None], [NO_TIE, TIE])})
        self.assertEqual(setlist_from_data(data).to_data()[Section.PATTERNS][X][Row.TIE], [NO_TIE, TIE])

    def test_a_tie_on_a_step_with_a_note_is_refused(self):
        with self.assertRaises(SongFileError) as caught:
            song_from_data(song({X: pattern([DEGREE_C, DEGREE_E], [NO_TIE, TIE])}))
        self.assertIn(STEP_2, str(caught.exception))

    def test_a_tie_must_be_true_or_false(self):
        for value in [None, 1, YES]:
            with self.subTest(value=value), self.assertRaises(SongFileError):
                song_from_data(song({X: pattern([DEGREE_C, None], [NO_TIE, value])}))


if __name__ == '__main__':
    unittest.main()
