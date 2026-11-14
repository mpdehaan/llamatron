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

"""The composition objects, each saving itself with to_data() and loading with from_data().

Every class gets the same kinds of test: what it reads comes back the same from to_data(), a
setting the data leaves out gets its default, settings left out aren't written back, and wrong
data is refused with a message that says where it is.
"""

import re
import random
import unittest
from fractions import Fraction

from llamatron.composition.clip_slot import ClipSlot, morph_style_name
from llamatron.composition.chain import Chain
from llamatron.composition.file_format import (
    CC_ROWS, PATTERN_ROWS, REGISTER_ADD_ROWS, REGISTER_NOTE_ROWS, REGISTER_VELOCITY_ROWS, Accidental, AtLimit,
    ClipSlotSetting, Direction, GeneratorKind, PatternSetting, RegisterName, RegisterSetting, Row, ScaleSetting, SceneSetting, Section,
    SetlistSetting, SongSetting, TrackSetting,
)
from llamatron.composition.generator_settings import (
    ArpSetting, ArpSettings, AutoRatchetSetting, AutoRatchetSettings, written_name,
)
from llamatron.composition.named_scale import NamedScale, scale_type_name
from llamatron.composition.pattern import Pattern
from llamatron.composition.defaults import (
    DEFAULT_REGISTER_MAXIMUM, DEFAULT_REGISTER_MINIMUM, DEFAULT_REGISTER_VALUE, DEFAULT_AT_LIMIT, DEFAULT_RESET_EACH_SCENE, DEFAULT_TIME_SIGNATURE,
)
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.limits import MAX_OCTAVE, MAX_REGISTER_VALUE, MAX_SCENE_REPEAT, MIN_OCTAVE, MIN_REGISTER_VALUE, MIN_REPEAT
from llamatron.composition.register import Register
from llamatron.composition.scene import Scene
from llamatron.composition.setlist import Setlist
from llamatron.composition.song import Song
from llamatron.composition.song_file_error import SongFileError
from llamatron.strings.errors import ERR_BAD_REPEAT, ERR_NEEDS_SETTING, ERR_NOT_A_SETLIST
from llamatron.composition.track import Track
from llamatron.generators.arp import MAX_OCTAVE_RANGE, Arp, ChordOrder
from llamatron.generators.auto_ratchet import AutoRatchet
from llamatron.generators.blend import BlendMode
from llamatron.music.note import NoteName
from llamatron.music.scale import ScaleType
from llamatron.music.time_signature import TimeSignature
from rendering import song_from_data

# Names the tests give to their own things, and other values they use.
MAIN = 'main'
A = 'a'
B = 'b'
LEAD = 'lead'
BASS = 'bass'
RIFF = 'riff'
NO_TEXT = ''
NAME_MUST_BE_TEXT = 'a name must be text'
UP = 'up'
X = 'x'
EIGHTH = '1/8'
QUARTER = '1/4'
HERE = 'here'
# Where a song's messages say they are, as the set places them.
SONG_WHERE = 'song (verse)'
# The name of from_data's song parameter, for the kinds that take one.
SONG_ARGUMENT = 'song'
NATURAL_MINOR = 'natural minor'
NOT_A_ROOT = 'H'
WOBBLY = 'wobbly'
EXPECTED_SETTINGS = 'expected track settings'
YES = 'yes'
DIRECTION_MUST_BE_ONE_OF = 'direction must be one of'
MUST_BE_A_NOTE_LETTER = 'must be a note letter'
NOTES = 'notes'
SIDEWAYS = 'sideways'
CHAIN_X = 'chain x'
SIXTEENTH = '1/16'
COUNT = 'count'
NEEDS_COUNTS = ERR_NEEDS_SETTING.format(name=AutoRatchetSetting.COUNTS)
EIGHTH_FRACTION = Fraction(1, 8)
CHAIN_X_AUTO_RATCHET = 'chain (x), auto_ratchet'
UNKNOWN_COUNT_HERE = 'here: unknown setting (count)'
UNKNOWN_COUNT_IN_CHAIN = 'chain (x), auto_ratchet: unknown setting (count)'
# Settings of an arp that reading a file refuses, each wrong in one setting.
WRONG_ARP_SETTINGS = [
    {ArpSetting.ORDER: 'sideways'},
    {ArpSetting.SEED: 'seven'},
    {ArpSetting.OCTAVE_RANGE: MAX_OCTAVE_RANGE + 1},
    {ArpSetting.OCTAVE_JUMP: 'never'},
    {ArpSetting.OFFSETS: 'up'},
    {ArpSetting.STEP: 'long'},
]
R = 'r'
WOBBLE = 'wobble'
NOT_AN_ARP = 'down'
A_MORPH_NEEDS_BOTH = 'a morph needs both'
ZZ = 'zz'
Y = 'y'
VERSE = 'verse'
OTHER = 'other'
DRUMS = 'drums'
TITLE_MUST_BE_TEXT = 'title must be text'
A_TITLE = 'T'
THEMES = 'themes'


def a_song():
    """Return a small song for objects that check names: a pattern, a track pair, an arp and a chain."""
    return song_from_data({
        Section.SCALES: {MAIN: {ScaleSetting.ROOT: NoteName.C, ScaleSetting.TYPE: scale_type_name(ScaleType.MAJOR)}},
        Section.PATTERNS: {A: {PatternSetting.STEPS: 1, Row.DEGREE: [1]}, B: {PatternSetting.STEPS: 1, Row.DEGREE: [5]}},
        Section.TRACKS: {LEAD: {}, BASS: {}},
        Section.ARPS: {UP: {ArpSetting.STEP: EIGHTH}},
        Section.CHAINS: {X: [{GeneratorKind.ARP: UP}]},
    })


# Time signatures the tests use, as a file writes them, and one that isn't.
WALTZ = '3/4'
COMPOUND_DUPLE = '6/8'
NOT_A_SIGNATURE = '4/5'


class RoundTrip(unittest.TestCase):

    def read(self, *, kind, data, song, named):
        """Read data as a kind of object, passing the song and any other arguments its from_data takes."""
        if song is not None:
            named = {**named, SONG_ARGUMENT: song}
        return kind.from_data(data=data, where=SONG_WHERE if kind is Song else HERE, **named)

    def assert_round_trip(self, kind, data, song=None, **named):
        self.assertEqual(self.read(kind=kind, data=data, song=song, named=named).to_data(), data)

    def assert_refused(self, expected, kind, data, song=None, **named):
        with self.assertRaises(SongFileError) as caught:
            self.read(kind=kind, data=data, song=song, named=named)
        self.assertIn(expected, str(caught.exception))


class TestNamedScale(RoundTrip):

    def test_round_trip_keeps_the_spelling(self):
        self.assert_round_trip(NamedScale, {ScaleSetting.ROOT: NoteName.B_FLAT, ScaleSetting.TYPE: NATURAL_MINOR})

    def test_a_note_some_half_steps_above_a_degree_is_placed_on_a_degree_with_a_sharp_or_flat_where_it_falls_between(self):
        major = NamedScale.from_data(data={ScaleSetting.ROOT: NoteName.C, ScaleSetting.TYPE: scale_type_name(ScaleType.MAJOR)}, where=HERE)
        # From C: Eb is D sharpened, E is the third degree, G the fifth, and C an octave up is the first degree of the next octave.
        self.assertEqual(major.degree_above(degree=1, octave=5, accidental=None, half_steps=3), (2, 5, Accidental.SHARP))
        self.assertEqual(major.degree_above(degree=1, octave=5, accidental=None, half_steps=4), (3, 5, None))
        self.assertEqual(major.degree_above(degree=1, octave=5, accidental=None, half_steps=7), (5, 5, None))
        self.assertEqual(major.degree_above(degree=1, octave=5, accidental=None, half_steps=12), (1, 6, None))
        # From a sharpened degree, and from a degree past the scale's size, which is in the next octave.
        self.assertEqual(major.degree_above(degree=1, octave=5, accidental=Accidental.SHARP, half_steps=3), (3, 5, None))
        self.assertEqual(major.degree_above(degree=8, octave=5, accidental=None, half_steps=4), (3, 6, None))
        # A pentatonic scale has gaps of three half steps: the middle note of a gap is a sharp of the degree below or a flat of the one above, and a note a whole step from both has no row.
        pentatonic = NamedScale.from_data(data={ScaleSetting.ROOT: NoteName.C, ScaleSetting.TYPE: scale_type_name(ScaleType.MAJOR_PENTATONIC)}, where=HERE)
        self.assertEqual(pentatonic.degree_above(degree=1, octave=5, accidental=None, half_steps=5), (3, 5, Accidental.SHARP))
        self.assertEqual(pentatonic.degree_above(degree=1, octave=5, accidental=None, half_steps=6), (4, 5, Accidental.FLAT))
        self.assertEqual(pentatonic.degree_above(degree=1, octave=5, accidental=None, half_steps=11), (1, 6, Accidental.FLAT))

    def test_it_makes_a_scale_in_an_octave(self):
        scale = NamedScale.from_data(data={ScaleSetting.ROOT: NoteName.F, ScaleSetting.TYPE: scale_type_name(ScaleType.MINOR)}, where=HERE).scale_at(5)
        self.assertEqual(scale.get_root().get_name(), NoteName.F)
        self.assertEqual(scale.get_root().get_octave_number(), 5)

    def test_refusals(self):
        self.assert_refused('expected a root and a type', NamedScale, {ScaleSetting.ROOT: NoteName.C})
        self.assert_refused('expected a root note such as F or Bb', NamedScale, {ScaleSetting.ROOT: NOT_A_ROOT, ScaleSetting.TYPE: scale_type_name(ScaleType.MAJOR)})
        self.assert_refused('unknown scale type (wobbly)', NamedScale, {ScaleSetting.ROOT: NoteName.C, ScaleSetting.TYPE: WOBBLY})


# A seed for a register's random picks, and enough picks to land on every value of a small range.
SEED = 5
RANDOM_TRIES = 200


class TestRegister(RoundTrip):

    def test_round_trip_and_defaults(self):
        self.assert_round_trip(Register, {RegisterSetting.DEFAULT: 1, RegisterSetting.MINIMUM: -3, RegisterSetting.MAXIMUM: 3, RegisterSetting.AT_LIMIT: AtLimit.OVERFLOW})
        self.assert_round_trip(Register, {})
        plain = Register.from_data(data={}, where=HERE)
        self.assertEqual(
            (plain.get_default(), plain.get_minimum(), plain.get_maximum(), plain.get_at_limit(), plain.resets_each_scene()),
            (DEFAULT_REGISTER_VALUE, DEFAULT_REGISTER_MINIMUM, DEFAULT_REGISTER_MAXIMUM, DEFAULT_AT_LIMIT, DEFAULT_RESET_EACH_SCENE),
        )

    def test_adding_stops_at_the_ends_or_wraps_to_the_other_one(self):
        lowest = 0
        highest = 3
        stops = Register.from_data(data={RegisterSetting.MINIMUM: lowest, RegisterSetting.MAXIMUM: highest}, where=HERE)
        self.assertEqual([stops.added(value=highest - 1, amount=1), stops.added(value=highest - 1, amount=highest), stops.added(value=lowest, amount=-1)], [highest, highest, lowest])
        wraps = Register.from_data(data={RegisterSetting.MINIMUM: lowest, RegisterSetting.MAXIMUM: highest, RegisterSetting.AT_LIMIT: AtLimit.OVERFLOW}, where=HERE)
        # Past an end, it lands on the other end, whatever is left over.
        self.assertEqual([wraps.added(value=highest - 1, amount=1), wraps.added(value=highest - 1, amount=highest), wraps.added(value=lowest, amount=-highest)], [highest, lowest, highest])

    def test_each_at_limit_does_its_own_thing_past_each_end(self):
        lowest = 0
        default = 1
        highest = 3
        # What each At limit gives past the top and past the bottom.
        expected = {
            AtLimit.STOP: (highest, lowest), AtLimit.RESET: (default, default), AtLimit.OVERFLOW: (lowest, highest),
            AtLimit.OVERFLOW_RIGHT: (lowest, lowest), AtLimit.OVERFLOW_LEFT: (highest, highest),
        }
        for at_limit, (past_the_top, past_the_bottom) in expected.items():
            with self.subTest(at_limit=at_limit):
                register = Register.from_data(data={
                    RegisterSetting.MINIMUM: lowest, RegisterSetting.DEFAULT: default, RegisterSetting.MAXIMUM: highest, RegisterSetting.AT_LIMIT: at_limit,
                }, where=HERE)
                self.assertEqual(register.added(value=highest, amount=1), past_the_top)
                self.assertEqual(register.added(value=lowest, amount=-1), past_the_bottom)
                self.assertEqual(register.added(value=lowest, amount=1), lowest + 1)
        picks = Register.from_data(data={RegisterSetting.MINIMUM: lowest, RegisterSetting.MAXIMUM: highest, RegisterSetting.AT_LIMIT: AtLimit.PICK_RANDOM}, where=HERE)
        chooser = random.Random(SEED)
        landed = {picks.added(value=highest, amount=1, chooser=chooser) for _ in range(RANDOM_TRIES)}
        self.assertEqual(landed, set(range(lowest, highest + 1)))

    def test_a_file_from_before_at_limit_reads_wrap_as_overflow(self):
        register = Register.from_data(data={RegisterSetting.WRAP: True}, where=HERE)
        self.assertEqual(register.get_at_limit(), AtLimit.OVERFLOW)
        self.assertEqual(register.to_data(), {RegisterSetting.AT_LIMIT: AtLimit.OVERFLOW})
        self.assertEqual(Register.from_data(data={RegisterSetting.WRAP: False}, where=HERE).get_at_limit(), DEFAULT_AT_LIMIT)

    def test_refusals(self):
        too_high = MAX_REGISTER_VALUE + 1
        self.assert_refused(f'maximum must be an integer from {MIN_REGISTER_VALUE} to {MAX_REGISTER_VALUE}', Register, {RegisterSetting.MAXIMUM: too_high})
        self.assert_refused('wrap must be true or false', Register, {RegisterSetting.WRAP: 1})
        above = DEFAULT_REGISTER_MAXIMUM + 1
        expected = f'needs minimum ({DEFAULT_REGISTER_MINIMUM}) <= default ({above}) <= maximum ({DEFAULT_REGISTER_MAXIMUM})'
        self.assert_refused(expected, Register, {RegisterSetting.DEFAULT: above})
        self.assert_refused('unknown setting (step)', Register, {ArpSetting.STEP: 1})


class TestTrack(RoundTrip):

    def test_round_trip(self):
        self.assert_round_trip(Track, {TrackSetting.DRUM: True, TrackSetting.MUTE: True, TrackSetting.CC: [74, None, None, 1]})
        self.assert_round_trip(Track, {TrackSetting.TRANSPOSE: -7})
        self.assert_round_trip(Track, {})

    def test_defaults(self):
        track = Track.from_data(data=None, where=HERE)
        self.assertEqual((track.is_drum(), track.is_muted(), track.get_transpose()), (False, False, 0))
        self.assertEqual(track.get_cc_numbers(), [None] * 4)
        self.assertEqual(track.to_data(), {})

    def test_a_drum_track_never_transposes(self):
        self.assertEqual(Track.from_data(data={TrackSetting.DRUM: True, TrackSetting.TRANSPOSE: 3}, where=HERE).get_transpose(), 0)

    def test_its_octave_range_is_the_whole_midi_range_unless_set_and_the_ends_cannot_cross(self):
        self.assert_round_trip(Track, {TrackSetting.LOWEST_OCTAVE: 3, TrackSetting.HIGHEST_OCTAVE: 6})
        track = Track.from_data(data={TrackSetting.LOWEST_OCTAVE: 3, TrackSetting.HIGHEST_OCTAVE: 6}, where=HERE)
        self.assertEqual((track.get_lowest_octave(), track.get_highest_octave()), (3, 6))
        plain = Track.from_data(data=None, where=HERE)
        self.assertEqual((plain.get_lowest_octave(), plain.get_highest_octave()), (MIN_OCTAVE, MAX_OCTAVE))
        plain.set_lowest_octave(2)
        plain.set_highest_octave(MAX_OCTAVE)
        self.assertEqual(plain.to_data(), {TrackSetting.LOWEST_OCTAVE: 2})
        self.assertEqual(plain.copy().get_lowest_octave(), 2)
        with self.assertRaises(InvalidValue):
            plain.set_highest_octave(1)
        with self.assertRaises(InvalidValue):
            plain.set_lowest_octave(MAX_OCTAVE + 1)
        self.assert_refused('lowest_octave must be an integer from 0 to 10', Track, {TrackSetting.LOWEST_OCTAVE: MAX_OCTAVE + 1})
        self.assert_refused('highest_octave must be an integer from 0 to 10', Track, {TrackSetting.HIGHEST_OCTAVE: EIGHTH})
        self.assert_refused('lowest_octave must not be above highest_octave', Track, {TrackSetting.LOWEST_OCTAVE: 5, TrackSetting.HIGHEST_OCTAVE: 4})

    def test_refusals(self):
        self.assert_refused(EXPECTED_SETTINGS, Track, [1])
        self.assert_refused('unknown setting (octave)', Track, {Row.OCTAVE: 2})
        self.assert_refused('mute must be true or false', Track, {TrackSetting.MUTE: YES})
        self.assert_refused('transpose must be an integer from -24 to 24', Track, {TrackSetting.TRANSPOSE: 25})
        self.assert_refused('cc must be a list of 4 CC numbers', Track, {TrackSetting.CC: [1, 2]})


class TestPattern(RoundTrip):

    DATA = {
        'steps': 3, 'drum': False, 'direction': 'pendulum', 'ax_add': [1, None, -2], 'bx_note': [False, False, True],
        'degree': [1, None, 5], 'gate': ['1/4', None, 1], 'dot': ['d', None, None], 'glide': [True, False, False],
        'tie': [False, True, False],
    }

    def test_round_trip(self):
        self.assert_round_trip(Pattern, self.DATA)
        self.assert_round_trip(Pattern, {PatternSetting.STEPS: 1})

    def test_values_and_defaults(self):
        pattern = Pattern.from_data(data=self.DATA, where=HERE)
        self.assertEqual((pattern.get_steps(), pattern.get_direction()), (3, Direction.PENDULUM))
        self.assertEqual([pattern.get_value(row=Row.AX_ADD, step=step) for step in range(3)], [1, None, -2])
        self.assertEqual([pattern.get_value(row=Row.DEGREE, step=step) for step in range(3)], [1, None, 5])
        self.assertIsNone(pattern.get_value(row=Row.VELOCITY, step=0))
        self.assertEqual(pattern.get_note_steps(), [0, 2])
        self.assertIsNone(pattern.get_first_octave())
        plain = Pattern.from_data(data={PatternSetting.STEPS: 2, Row.OCTAVE: [None, 4]}, where=HERE)
        self.assertEqual((plain.get_direction(), plain.is_drum()), (Direction.FORWARD, False))
        self.assertEqual(plain.get_first_octave(), 4)

    def test_every_step_values_are_each_steps_values_with_none_where_it_is_blank(self):
        pattern = Pattern.from_data(data=self.DATA, where=HERE)
        rows = [Row.DEGREE, Row.AX_ADD, Row.VELOCITY, Row.TIE]
        self.assertEqual(pattern.get_every_step_values(rows=rows), [
            {Row.DEGREE: 1, Row.AX_ADD: 1, Row.VELOCITY: None, Row.TIE: False},
            {Row.DEGREE: None, Row.AX_ADD: None, Row.VELOCITY: None, Row.TIE: True},
            {Row.DEGREE: 5, Row.AX_ADD: -2, Row.VELOCITY: None, Row.TIE: False},
        ])

    def test_every_step_values_agree_with_get_value_on_every_row_before_and_after_an_edit(self):
        pattern = Pattern.from_data(data=self.DATA, where=HERE)
        # Each edit gives a row that was blank throughout a value on one step, and a CC value of 0 is a value.
        for edit in (None, {Row.VELOCITY: 64}, {Row.CC1: 0}):
            for row, value in (edit or {}).items():
                pattern.set_value(row=row, step=1, value=value)
            every = pattern.get_every_step_values(rows=PATTERN_ROWS)
            self.assertEqual(len(every), pattern.get_steps())
            for step, values in enumerate(every):
                with self.subTest(edit=edit, step=step):
                    self.assertEqual(values, {row: pattern.get_value(row=row, step=step) for row in PATTERN_ROWS})

    def test_every_steps_values_are_a_dictionary_of_their_own(self):
        every = Pattern.from_data(data=self.DATA, where=HERE).get_every_step_values(rows=PATTERN_ROWS)
        every[0][Row.DEGREE] = 7
        self.assertIsNone(every[1][Row.DEGREE])

    def test_a_pattern_sends_controls_when_any_step_holds_a_cc_value_even_zero(self):
        def pattern_with(**rows):
            return Pattern.from_data(data={PatternSetting.STEPS: 2, Row.DEGREE: [1, 2], **rows}, where=HERE)

        self.assertFalse(pattern_with().sends_controls())
        self.assertFalse(pattern_with(**{Row.SLIDE: [True, False]}).sends_controls())
        for row in CC_ROWS:
            with self.subTest(row=row):
                self.assertTrue(pattern_with(**{row: [None, 0]}).sends_controls())
                self.assertFalse(pattern_with(**{row: [None, None]}).sends_controls())
        emptied = pattern_with()
        emptied.set_value(row=Row.CC1, step=0, value=64)
        self.assertTrue(emptied.sends_controls())
        emptied.set_value(row=Row.CC1, step=0, value=None)
        self.assertFalse(emptied.sends_controls())

    def test_a_pattern_uses_registers_when_any_step_switches_a_note_or_velocity_row_on(self):
        def pattern_with(**rows):
            return Pattern.from_data(data={PatternSetting.STEPS: 2, Row.DEGREE: [1, 2], **rows}, where=HERE)

        self.assertFalse(pattern_with().uses_registers())
        # Adding to a register is not using one.
        self.assertFalse(pattern_with(**{REGISTER_ADD_ROWS[RegisterName.AX]: [1, 1]}).uses_registers())
        for rows in (REGISTER_NOTE_ROWS, REGISTER_VELOCITY_ROWS):
            for name, row in rows.items():
                with self.subTest(register=name, row=row):
                    self.assertTrue(pattern_with(**{row: [False, True]}).uses_registers())
                    self.assertFalse(pattern_with(**{row: [False, False]}).uses_registers())

    def test_holding_note_and_tied_end_follow_the_ties(self):
        pattern = Pattern.from_data(data={PatternSetting.STEPS: 5, Row.DEGREE: [1, None, None, 3, None], Row.TIE: [False, True, True, False, False]}, where=HERE)
        self.assertEqual([pattern.holding_note(step) for step in range(5)], [0, 0, 0, 3, None])
        self.assertEqual((pattern.tied_end(0), pattern.tied_end(3)), (3, 4))
        self.assertEqual(pattern.gate_length(0), None)

    def test_gate_length_takes_in_the_dot(self):
        pattern = Pattern.from_data(data={PatternSetting.STEPS: 2, Row.DEGREE: [1, 1], Row.GATE: ['1/4', '1/4'], Row.DOT: ['d', 't']}, where=HERE)
        self.assertEqual((pattern.gate_length(0), pattern.gate_length(1)), (Fraction(3, 8), Fraction(1, 6)))

    def test_placing_a_note_writes_ties_and_takes_out_what_was_there(self):
        pattern = Pattern.from_data(data={PatternSetting.STEPS: 4, Row.DEGREE: [None, 5, None, None], Row.GATE: [None, '1/2', None, None], Row.TIE: [False, False, True, False]}, where=HERE)
        pattern.place_note(step=0, degree=2, octave=4, covered=3)
        self.assertEqual(pattern.get_row(Row.DEGREE), [2, None, None, None])
        self.assertEqual(pattern.get_row(Row.OCTAVE), [4, None, None, None])
        self.assertEqual(pattern.get_row(Row.TIE), [False, True, True, False])
        self.assertIsNone(pattern.get_value(row=Row.GATE, step=1))
        pattern.place_note(step=3, degree=1, octave=4, covered=4, gate='1/32')
        self.assertEqual(pattern.get_value(row=Row.GATE, step=3), '1/32')
        self.assertEqual(pattern.get_row(Row.TIE), [False, True, True, False])

    def test_placing_inside_a_held_note_cuts_it_there(self):
        pattern = Pattern.from_data(data={PatternSetting.STEPS: 4, Row.DEGREE: [1, None, None, None], Row.TIE: [False, True, True, True]}, where=HERE)
        pattern.place_note(step=2, degree=3, octave=5, covered=1)
        # The tie after the new note held the old one, so it becomes a note of its own at the old pitch: drawing never silences anything to the right.
        self.assertEqual(pattern.get_row(Row.DEGREE), [1, None, 3, 1])
        self.assertEqual(pattern.get_row(Row.TIE), [False, True, False, False])

    def test_split(self):
        pattern = Pattern.from_data(
            data={PatternSetting.STEPS: 4, Row.DEGREE: [1, None, None, None], Row.OCTAVE: [4, None, None, None], Row.VELOCITY: [100, None, None, None], Row.TIE: [False, True, True, False]},
            where=HERE,
        )
        self.assertFalse(pattern.split_note(0))
        self.assertFalse(pattern.split_note(3))
        self.assertTrue(pattern.split_note(2))
        self.assertEqual(pattern.get_row(Row.DEGREE), [1, None, 1, None])
        self.assertEqual(pattern.get_row(Row.OCTAVE), [4, None, 4, None])
        self.assertEqual(pattern.get_row(Row.VELOCITY), [100, None, 100, None])
        self.assertEqual(pattern.get_row(Row.TIE), [False, True, False, False])

    def test_its_lists_are_its_own(self):
        data = {PatternSetting.STEPS: 1, Row.DEGREE: [1]}
        pattern = Pattern.from_data(data=data, where=HERE)
        data[Row.DEGREE][0] = 9
        pattern.to_data()[Row.DEGREE][0] = 9
        self.assertEqual(pattern.get_value(row=Row.DEGREE, step=0), 1)

    def test_refusals(self):
        self.assert_refused('expected pattern settings', Pattern, [])
        self.assert_refused('unknown setting (notes)', Pattern, {PatternSetting.STEPS: 1, NOTES: []})
        self.assert_refused('steps must be an integer of 1 or more', Pattern, {PatternSetting.STEPS: 0})
        self.assert_refused('degree must be a list of 2 values', Pattern, {PatternSetting.STEPS: 2, Row.DEGREE: [1]})
        self.assert_refused('glide must be true or false, got null', Pattern, {PatternSetting.STEPS: 1, Row.GLIDE: [None]})
        self.assert_refused('step 1 has both a note and a tie', Pattern, {PatternSetting.STEPS: 1, Row.DEGREE: [1], Row.TIE: [True]})
        self.assert_refused(DIRECTION_MUST_BE_ONE_OF, Pattern, {PatternSetting.STEPS: 1, PatternSetting.DIRECTION: SIDEWAYS})
        self.assert_refused('velocity must be an integer from 1 to 127', Pattern, {PatternSetting.STEPS: 1, Row.VELOCITY: [0]})
        self.assert_refused(MUST_BE_A_NOTE_LETTER, Pattern, {PatternSetting.STEPS: 1, PatternSetting.DRUM: True, Row.DEGREE: [1]})


class TestGeneratorSettings(RoundTrip):

    def test_round_trip_keeps_settings_as_written(self):
        self.assert_round_trip(ArpSettings, {ArpSetting.STEP: SIXTEENTH, ArpSetting.ORDER: written_name(ChordOrder.UP_DOWN), ArpSetting.OFFSETS: [0, None, 7]})
        self.assert_round_trip(AutoRatchetSettings, {AutoRatchetSetting.COUNTS: [1, 4]})

    def test_a_generator_written_with_no_settings_is_refused_for_what_it_needs(self):
        with self.assertRaisesRegex(SongFileError, NEEDS_COUNTS):
            AutoRatchetSettings.from_data(data=None, where=HERE)

    def test_an_arp_with_no_step_takes_the_step_of_the_pattern_its_clip_plays(self):
        # Since 2026-11-11 an arp's step left out is "(pattern)", the user's rule, where it was refused before.
        settings = ArpSettings.from_data(data=None, where=HERE)
        self.assertIsNone(settings.get_step())
        self.assertEqual(settings.make_generator(where=CHAIN_X, default_seed=7, default_step=EIGHTH_FRACTION).get_step(), EIGHTH_FRACTION)

    def test_it_makes_its_generator(self):
        arp = ArpSettings.from_data(data={ArpSetting.STEP: EIGHTH, ArpSetting.ORDER: written_name(ChordOrder.DOWN)}, where=HERE).make_generator(where='chain x, arp', default_seed=7)
        self.assertIsInstance(arp, Arp)
        self.assertEqual((arp.get_step(), arp.get_order(), arp.get_seed()), (Fraction(1, 8), ChordOrder.DOWN, 7))
        self.assertIsInstance(AutoRatchetSettings.from_data(data={AutoRatchetSetting.COUNTS: [2]}, where=HERE).make_generator(where=CHAIN_X, default_seed=7), AutoRatchet)

    def test_a_seed_of_its_own_beats_the_default(self):
        arp = ArpSettings.from_data(data={ArpSetting.STEP: EIGHTH, ArpSetting.SEED: 3}, where=HERE).make_generator(where=CHAIN_X, default_seed=7)
        self.assertEqual(arp.get_seed(), 3)

    def test_wrong_settings_are_refused_when_read_and_name_the_place(self):
        with self.assertRaisesRegex(SongFileError, re.escape(UNKNOWN_COUNT_HERE)):
            AutoRatchetSettings.from_data(data={COUNT: [2]}, where=HERE)
        for data in WRONG_ARP_SETTINGS:
            with self.subTest(data=data), self.assertRaises(SongFileError):
                ArpSettings.from_data(data={ArpSetting.STEP: EIGHTH, **data}, where=HERE)

    def test_settings_built_without_a_file_are_refused_when_used_and_name_the_chain(self):
        with self.assertRaisesRegex(SongFileError, re.escape(UNKNOWN_COUNT_IN_CHAIN)):
            AutoRatchetSettings({COUNT: [2]}).make_generator(where=CHAIN_X_AUTO_RATCHET, default_seed=1)
        with self.assertRaisesRegex(SongFileError, NEEDS_COUNTS):
            AutoRatchetSettings({}).make_generator(where=CHAIN_X, default_seed=1)


class TestChain(RoundTrip):

    def test_round_trip(self):
        self.assert_round_trip(Chain, [{GeneratorKind.ARP: UP}, {GeneratorKind.ARP: UP}], setlist=a_song().get_setlist())

    def test_steps(self):
        self.assertEqual(Chain.from_data(data=[{GeneratorKind.ARP: UP}], where=HERE, setlist=a_song().get_setlist()).get_steps(), [(GeneratorKind.ARP, UP)])

    def test_refusals(self):
        setlist = a_song().get_setlist()
        self.assert_refused('expected a list of generators', Chain, {}, setlist=setlist)
        self.assert_refused('each step must be one generator', Chain, [{GeneratorKind.ARP: UP, GeneratorKind.AUTO_RATCHET: R}], setlist=setlist)
        self.assert_refused('unknown generator (wobble)', Chain, [{WOBBLE: UP}], setlist=setlist)
        self.assert_refused('no arp called (down)', Chain, [{GeneratorKind.ARP: NOT_AN_ARP}], setlist=setlist)


class TestClipSlot(RoundTrip):

    def test_round_trip(self):
        data = {ClipSlotSetting.PATTERN: A, ClipSlotSetting.CHAIN: X, ClipSlotSetting.REPEAT: 2, ClipSlotSetting.MORPH_TO: B, ClipSlotSetting.MORPH_STYLE: morph_style_name(BlendMode.LEFT), ClipSlotSetting.GRAB_TRACK: BASS}
        self.assert_round_trip(ClipSlot, data, a_song(), track=LEAD)
        self.assert_round_trip(ClipSlot, {ClipSlotSetting.PATTERN: A, ClipSlotSetting.LOOP: False}, a_song(), track=LEAD)

    def test_a_name_of_its_own_or_its_patterns(self):
        named = ClipSlot.from_data(data={ClipSlotSetting.PATTERN: A, ClipSlotSetting.NAME: RIFF}, where=HERE, song=a_song(), track=LEAD)
        self.assertEqual((named.get_name(), named.get_display_name()), (RIFF, RIFF))
        plain = ClipSlot.from_data(data={ClipSlotSetting.PATTERN: A}, where=HERE, song=a_song(), track=LEAD)
        self.assertEqual((plain.get_name(), plain.get_display_name()), (None, A))
        plain.set_name(RIFF)
        self.assertEqual(plain.to_data(), {ClipSlotSetting.PATTERN: A, ClipSlotSetting.NAME: RIFF})
        plain.set_name(NO_TEXT)
        self.assertEqual(plain.to_data(), {ClipSlotSetting.PATTERN: A})
        self.assert_refused(NAME_MUST_BE_TEXT, ClipSlot, {ClipSlotSetting.PATTERN: A, ClipSlotSetting.NAME: 3}, song=a_song(), track=LEAD)

    def test_values_and_defaults(self):
        clip_slot = ClipSlot.from_data(data={ClipSlotSetting.PATTERN: A, ClipSlotSetting.MORPH_TO: B, ClipSlotSetting.MORPH_STYLE: morph_style_name(BlendMode.MIDDLE), ClipSlotSetting.REPEAT: 3}, where=HERE, song=a_song(), track=LEAD)
        self.assertEqual((clip_slot.get_pattern_name(), clip_slot.get_repeat()), (A, 3))
        self.assertEqual((clip_slot.get_morph_target(), clip_slot.get_morph_style()), (B, BlendMode.MIDDLE))
        plain = ClipSlot.from_data(data={ClipSlotSetting.PATTERN: A}, where=HERE, song=a_song(), track=LEAD)
        self.assertEqual((plain.get_pattern_name(), plain.get_repeat(), plain.loops()), (A, 1, False))
        self.assertEqual(plain.get_chain_names(), [])
        self.assertIsNone(plain.get_direction())
        self.assertIsNone(plain.get_morph_style())
        self.assertIsNone(plain.get_grab_track())

    def test_refusals_name_the_track(self):
        song = a_song()
        self.assert_refused('here, track (lead): needs a pattern', ClipSlot, {}, song, track=LEAD)
        self.assert_refused('no pattern called (zz)', ClipSlot, {ClipSlotSetting.PATTERN: ZZ}, song, track=LEAD)
        self.assert_refused('no chain called (y)', ClipSlot, {ClipSlotSetting.PATTERN: A, ClipSlotSetting.CHAIN: Y}, song, track=LEAD)
        self.assert_refused('cannot grab from its own track', ClipSlot, {ClipSlotSetting.PATTERN: A, ClipSlotSetting.GRAB_TRACK: LEAD}, song, track=LEAD)
        self.assert_refused(A_MORPH_NEEDS_BOTH, ClipSlot, {ClipSlotSetting.PATTERN: A, ClipSlotSetting.MORPH_TO: B, ClipSlotSetting.REPEAT: 2}, song, track=LEAD)
        self.assert_refused('a morph needs a repeat of 2', ClipSlot, {ClipSlotSetting.PATTERN: A, ClipSlotSetting.MORPH_TO: B, ClipSlotSetting.MORPH_STYLE: morph_style_name(BlendMode.LEFT)}, song, track=LEAD)
        self.assert_refused('loop must be true or false', ClipSlot, {ClipSlotSetting.PATTERN: A, ClipSlotSetting.LOOP: YES}, song, track=LEAD)


class TestScene(RoundTrip):

    def test_round_trip(self):
        data = {SceneSetting.NAME: VERSE, SceneSetting.REPEAT: 2, SceneSetting.SCALE: MAIN, SceneSetting.TEMPO_START: 100, SceneSetting.TEMPO_END: 120, SceneSetting.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: A}}}
        self.assert_round_trip(Scene, data, a_song())
        self.assert_round_trip(Scene, {}, a_song())

    def test_values_and_defaults(self):
        scene = Scene.from_data(data={SceneSetting.REPEAT: 3, SceneSetting.TEMPO_START: 100, SceneSetting.TEMPO_END: 120, SceneSetting.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: A}}}, where=HERE, song=a_song())
        self.assertEqual([scene.get_tempo(place) for place in range(3)], [100, 110, 120])
        self.assertEqual(scene.get_track_names(), [LEAD])
        self.assertEqual(scene.get_clip_slot(LEAD).get_pattern_name(), A)
        self.assertIsNone(scene.get_clip_slot(BASS))
        plain = Scene.from_data(data={}, where=HERE, song=a_song())
        self.assertEqual((plain.get_name(), plain.get_repeat(), plain.get_scale_name(), plain.get_tempo(0)), (None, 1, None, None))

    def test_refusals(self):
        song = a_song()
        self.assert_refused('expected scene settings', Scene, [], song)
        for repeat in (MIN_REPEAT - 1, MAX_SCENE_REPEAT + 1):
            self.assert_refused(ERR_BAD_REPEAT.format(lowest=MIN_REPEAT, highest=MAX_SCENE_REPEAT, value=repeat), Scene, {SceneSetting.REPEAT: repeat}, song)
        self.assert_refused('no track called (drums)', Scene, {Section.TRACKS: {DRUMS: {ClipSlotSetting.PATTERN: A}}}, song)
        self.assert_refused('no scale called (other)', Scene, {SongSetting.SCALE: OTHER}, song)
        self.assert_refused('needs both tempo_start and tempo_end', Scene, {SceneSetting.TEMPO_START: 90}, song)


class TestSetlistAndSong(RoundTrip):

    def test_round_trip(self):
        self.assertEqual(a_song().to_data(), song_from_data(a_song().to_data()).to_data())
        data = {SetlistSetting.TITLE: A_TITLE, Section.SONGS: {VERSE: {SongSetting.TEMPO: 90, SceneSetting.TRACKS: {}, Section.SCENES: []}}}
        self.assertEqual(Setlist.from_data(data=data).to_data(), data)

    def test_an_empty_file_is_an_empty_set_with_defaults_and_no_songs(self):
        for data in [None, {}]:
            setlist = Setlist.from_data(data=data)
            self.assertEqual(setlist.to_data(), {})
            self.assertEqual(setlist.get_song_names(), [])
            self.assertEqual((setlist.get_step_size(), setlist.get_default_octave(), setlist.get_default_drum_octave()), (Fraction(1, 16), 5, 3))

    def test_an_empty_song_has_the_defaults(self):
        song = song_from_data({})
        self.assertEqual(song.to_data(), {})
        self.assertEqual((song.get_tempo(), song.get_seed(), song.get_step_size()), (120, None, Fraction(1, 16)))
        self.assertEqual(song.get_time_signature().to_text(), DEFAULT_TIME_SIGNATURE)
        self.assertEqual((song.get_default_octave(), song.get_default_drum_octave(), song.get_scale_name()), (5, 3, None))
        self.assertEqual((song.get_track_names(), song.get_scenes()), ([], []))

    def test_a_song_time_signature_is_read_and_written_and_a_pattern_can_have_its_own(self):
        song = song_from_data({SongSetting.TIME_SIGNATURE: WALTZ})
        self.assertEqual(song.get_time_signature(), TimeSignature.from_text(WALTZ))
        self.assertEqual(song.to_data()[SongSetting.TIME_SIGNATURE], WALTZ)
        song.set_time_signature(COMPOUND_DUPLE)
        self.assertEqual(song.get_time_signature().beat_length(), Fraction(3, 8))
        plain = Pattern.from_data(data={PatternSetting.STEPS: 1}, where=HERE)
        own = Pattern.from_data(data={PatternSetting.STEPS: 1, PatternSetting.TIME_SIGNATURE: WALTZ}, where=HERE)
        self.assertIsNone(plain.get_time_signature())
        self.assertIsNone(plain.get_written_time_signature())
        self.assertEqual(song.get_pattern_time_signature(plain), song.get_time_signature())
        self.assertEqual(song.get_pattern_time_signature(own), TimeSignature.from_text(WALTZ))
        self.assertEqual(own.to_data()[PatternSetting.TIME_SIGNATURE], WALTZ)
        self.assertEqual(own.copy().get_written_time_signature(), WALTZ)
        own.set_time_signature(None)
        self.assertNotIn(PatternSetting.TIME_SIGNATURE, own.to_data())

    def test_the_entry_size_is_the_patterns_then_the_songs_then_one_step(self):
        song = song_from_data({SongSetting.ENTRY_SIZE: EIGHTH})
        self.assertEqual(song.get_entry_size(), Fraction(1, 8))
        self.assertEqual(song.to_data()[SongSetting.ENTRY_SIZE], EIGHTH)
        plain = Pattern.from_data(data={PatternSetting.STEPS: 1}, where=HERE)
        own = Pattern.from_data(data={PatternSetting.STEPS: 1, PatternSetting.ENTRY_SIZE: QUARTER}, where=HERE)
        self.assertIsNone(plain.get_entry_size())
        self.assertEqual(song.entry_size_for(plain), Fraction(1, 8))
        self.assertEqual(song.entry_size_for(own), Fraction(1, 4))
        self.assertEqual(own.to_data()[PatternSetting.ENTRY_SIZE], QUARTER)
        self.assertEqual(own.copy().get_written_entry_size(), QUARTER)
        song.set_entry_size(None)
        self.assertEqual(song.entry_size_for(plain), song.get_step_size())
        self.assertNotIn(SongSetting.ENTRY_SIZE, song.to_data())
        own.set_entry_size(None)
        self.assertNotIn(PatternSetting.ENTRY_SIZE, own.to_data())
        self.assert_refused('entry_size: expected an integer or a fraction', Song, {SongSetting.ENTRY_SIZE: 0.5}, setlist=Setlist.new())
        self.assert_refused('entry_size: a length can be at most 4', Pattern, {PatternSetting.STEPS: 1, PatternSetting.ENTRY_SIZE: 5})

    def test_time_signatures_are_checked(self):
        self.assert_refused('time_signature: time signature must be beats over a note value', Song, {SongSetting.TIME_SIGNATURE: NOT_A_SIGNATURE}, setlist=Setlist.new())
        self.assert_refused('time_signature: time signature must be beats over a note value', Pattern, {PatternSetting.STEPS: 1, PatternSetting.TIME_SIGNATURE: NOT_A_SIGNATURE})

    def test_a_file_from_before_sets_is_read_as_a_set_of_one_song(self):
        data = {SongSetting.TEMPO: 90, Section.TRACKS: {LEAD: {}}, Section.SCENES: []}
        setlist = Setlist.from_data(data=data, one_song_name=VERSE)
        self.assertEqual(setlist.get_song_names(), [VERSE])
        self.assertEqual(setlist.get_song(VERSE).get_tempo(), 90)
        self.assertEqual(setlist.get_song(VERSE).get_track_names(), [LEAD])

    def test_it_looks_up_its_named_objects(self):
        song = a_song()
        self.assertTrue(song.has_pattern(A) and song.has_track(LEAD) and song.has_chain(X) and song.has_scale(MAIN))
        self.assertTrue(song.has_generator(kind=GeneratorKind.ARP, name=UP))
        self.assertFalse(song.has_generator(kind=GeneratorKind.AUTO_RATCHET, name=UP))
        self.assertEqual(song.get_track_names(), [LEAD, BASS])
        self.assertEqual(song.get_pattern(B).get_value(row=Row.DEGREE, step=0), 5)

    def test_setlist_refusals(self):
        self.assert_refused(ERR_NOT_A_SETLIST, Setlist, [1])
        self.assert_refused('unknown setting (themes)', Setlist, {THEMES: {}})
        self.assert_refused(TITLE_MUST_BE_TEXT, Setlist, {SetlistSetting.TITLE: 3})
        self.assert_refused('step_size: expected an integer or a fraction', Setlist, {PatternSetting.STEP_SIZE: '0.25'})
        self.assert_refused('step_size: a length can be at most 4', Setlist, {PatternSetting.STEP_SIZE: 8})
        self.assert_refused('pattern (a): steps must be', Setlist, {Section.PATTERNS: {A: {PatternSetting.STEPS: 0}}})
        self.assert_refused('arps: expected settings by name', Setlist, {Section.ARPS: [UP]})
        self.assert_refused('songs: expected songs by name', Setlist, {Section.SONGS: [VERSE]})

    def test_song_refusals_name_the_song(self):
        setlist = a_song().get_setlist()
        self.assert_refused("song (verse): expected a song's settings", Song, [1], setlist=setlist)
        self.assert_refused('song (verse): scale: no scale called (other)', Song, {SongSetting.SCALE: OTHER}, setlist=setlist)
        self.assert_refused('song (verse): tracks: expected tracks by name', Song, {Section.TRACKS: [LEAD]}, setlist=setlist)
        self.assert_refused('song (verse): scenes: expected a list of scenes', Song, {Section.SCENES: {VERSE: {}}}, setlist=setlist)


if __name__ == '__main__':
    unittest.main()
