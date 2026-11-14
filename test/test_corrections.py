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
"""The corrections offered when a set file holds values that can't be used (composition/corrections.py).

A whole number outside its range takes the nearest end, a length that is too long the longest
allowed, and a choice outside its fixed list the default. Everything else wrong with a file is
refused as it always was, reading stays strict unless the corrected read is asked for, and no
file is ever changed. The two sets these tests open are in test/sample_sets, since a set made to
test the program never lives in examples/.
"""

import copy
import os
import unittest

import yaml

from llamatron.composition.clip_slot import FIRST_MORPH_STYLE
from llamatron.composition.corrections import LEFT_OUT, Correction, changed_count, place_without
from llamatron.composition.file_format import (
    CC_ROWS, LIVE_OCTAVE_OFFSET, REGISTER_ADD_ROWS, ClipSlotSetting, GrooveSetting, PatternSetting, RegisterName, RegisterSetting, Row,
    SceneSetting, Section, SetlistSetting, SongSetting, TrackSetting,
)
from llamatron.composition.generator_settings import ArpSetting
from llamatron.composition.limits import (
    MAX_CLIP_REPEAT, MAX_GATE, MAX_GROOVE_AMOUNT, MAX_GROOVE_CELL_LENGTH, MAX_OCTAVE, MAX_PROBABILITY, MAX_RATCHET, MAX_RATCHET_OFFSET,
    MAX_REGISTER_VALUE, MAX_SCENE_REPEAT, MAX_STEP_SIZE, MAX_TRANSPOSE,
    MIN_DEGREE, MIN_GROOVE_AMOUNT, MIN_OCTAVE, MIN_PROBABILITY, MIN_RATCHET, MIN_REGISTER_VALUE, MIN_REPEAT,
)
from llamatron.composition.pattern import nearest_step_value
from llamatron.composition.setlist import Setlist
from llamatron.composition.song_file_error import SongFileError
from llamatron.generators.arp import MAX_OCTAVE_RANGE, MAX_OFFSET
from llamatron.music.midi import MAX_CC_VALUE, MAX_VELOCITY, MIN_CC_VALUE, MIN_VELOCITY
from llamatron.strings.errors import ERR_OCTAVE_RANGE_BACKWARDS
from llamatron.strings.messages import MSG_CORRECTED, MSG_CORRECTED_SEVERAL, MSG_CORRECTED_TO_DEFAULT
from llamatron.strings.names import MSG_THE_FILE

# The two sets made for these tests.
SAMPLE_SETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sample_sets')
OUT_OF_RANGE = os.path.join(SAMPLE_SETS, 'out_of_range.yml')
OUT_OF_RANGE_AND_BROKEN = os.path.join(SAMPLE_SETS, 'out_of_range_and_broken.yml')
READ_BYTES = 'rb'
# The names in the data the tests build.
TUNE = 'tune'
LEAD = 'lead'
VERSE = 'verse'
UP = 'up'
SHUFFLE = 'shuffle'
NOT_A_NAME = 'nothing'
NOT_A_CHOICE = 'sideways'
NOT_A_NUMBER = 'loud'
HALF = 1.5
EIGHTH = '1/8'
QUARTER = '1/4'
STEPS = 4
FIRST_SCENE = 0
A_DEGREE = 3
A_VELOCITY = 90
STRAIGHT = 0
FAR_TOO_MANY = 1000
# What a path through a set's data finds where the data holds nothing.
ABSENT = object()
# A file written before llamatron numbered octaves from C0, which numbered them as Live does.
A_VERSION_WITH_LIVE_OCTAVES = '1.0.20'
# A place and a setting, for the tests of a correction on its own.
A_PLACE = 'song (verse), track (lead)'
A_PLACE_WITH_THE_NAME = 'song (verse), tempo'
TEMPO = 'tempo'


def with_pattern(settings):
    """Return a set's data with one pattern that has the settings and rows given."""
    return {Section.PATTERNS: {TUNE: {PatternSetting.STEPS: STEPS, **settings}}}


def with_song(settings):
    return {Section.SONGS: {VERSE: settings}}


def with_track(settings):
    return with_song({Section.TRACKS: {LEAD: settings}})


def with_scene(settings):
    return with_song({Section.TRACKS: {LEAD: {}}, Section.SCENES: [{SceneSetting.TRACKS: {}, **settings}]})


def with_clip(settings):
    """Return a set's data with one pattern, and one song whose one track plays it in one scene, as a clip with the settings given."""
    clip = {ClipSlotSetting.PATTERN: TUNE, **settings}
    return {**with_pattern({}), **with_song({Section.TRACKS: {LEAD: {}}, Section.SCENES: [{SceneSetting.TRACKS: {LEAD: clip}}]})}


def with_register(settings):
    return with_song({Section.REGISTERS: {RegisterName.AX: settings}})


def with_groove(settings):
    return {Section.GROOVES: {SHUFFLE: {GrooveSetting.CELLS: [STRAIGHT, STRAIGHT], **settings}}}


def with_arp(settings):
    return {Section.ARPS: {UP: {ArpSetting.STEP: EIGHTH, **settings}}}


def value_at(*, data, path):
    """Return what data holds along a path of keys and places, or ABSENT where it holds nothing."""
    for key in path:
        if isinstance(data, dict) and key not in data:
            return ABSENT
        data = data[key]
    return data


PATTERN = (Section.PATTERNS, TUNE)
SONG = (Section.SONGS, VERSE)
TRACK = (*SONG, Section.TRACKS, LEAD)
SCENE = (*SONG, Section.SCENES, FIRST_SCENE)
CLIP = (*SCENE, SceneSetting.TRACKS, LEAD)
REGISTER = (*SONG, Section.REGISTERS, RegisterName.AX)
GROOVE = (Section.GROOVES, SHUFFLE)
ARP = (Section.ARPS, UP)
AX_ADD = REGISTER_ADD_ROWS[RegisterName.AX]
FIRST_CC = CC_ROWS[0]
# Every value a file can hold that has an allowed value near it: the data that holds the wrong value, where the
# value is in the set's data, and what is there once the set is read corrected. LEFT_OUT is a setting taken out.
CORRECTED = [
    # The set's own settings.
    ({SetlistSetting.DEFAULT_OCTAVE: MAX_OCTAVE + 1}, (SetlistSetting.DEFAULT_OCTAVE,), MAX_OCTAVE),
    ({SetlistSetting.DEFAULT_DRUM_OCTAVE: MIN_OCTAVE - 1}, (SetlistSetting.DEFAULT_DRUM_OCTAVE,), MIN_OCTAVE),
    ({SetlistSetting.STEP_SIZE: MAX_STEP_SIZE * 2}, (SetlistSetting.STEP_SIZE,), MAX_STEP_SIZE),
    ({SetlistSetting.OCTAVE_LABELS: NOT_A_CHOICE}, (SetlistSetting.OCTAVE_LABELS,), LEFT_OUT),
    # A song.
    (with_song({SongSetting.ENTRY_SIZE: MAX_GATE + 1}), (*SONG, SongSetting.ENTRY_SIZE), MAX_GATE),
    # A track.
    (with_track({TrackSetting.TRANSPOSE: MAX_TRANSPOSE + 1}), (*TRACK, TrackSetting.TRANSPOSE), MAX_TRANSPOSE),
    (with_track({TrackSetting.TRANSPOSE: -MAX_TRANSPOSE - 1}), (*TRACK, TrackSetting.TRANSPOSE), -MAX_TRANSPOSE),
    (with_track({TrackSetting.LOWEST_OCTAVE: MIN_OCTAVE - 1}), (*TRACK, TrackSetting.LOWEST_OCTAVE), MIN_OCTAVE),
    (with_track({TrackSetting.HIGHEST_OCTAVE: MAX_OCTAVE + 1}), (*TRACK, TrackSetting.HIGHEST_OCTAVE), MAX_OCTAVE),
    # A scene.
    (with_scene({SceneSetting.REPEAT: MIN_REPEAT - 1}), (*SCENE, SceneSetting.REPEAT), MIN_REPEAT),
    (with_scene({SceneSetting.REPEAT: MAX_SCENE_REPEAT + 1}), (*SCENE, SceneSetting.REPEAT), MAX_SCENE_REPEAT),
    # A clip.
    (with_clip({ClipSlotSetting.REPEAT: MIN_REPEAT - 1}), (*CLIP, ClipSlotSetting.REPEAT), MIN_REPEAT),
    (with_clip({ClipSlotSetting.REPEAT: MAX_CLIP_REPEAT + 1}), (*CLIP, ClipSlotSetting.REPEAT), MAX_CLIP_REPEAT),
    (with_clip({ClipSlotSetting.DIRECTION: NOT_A_CHOICE}), (*CLIP, ClipSlotSetting.DIRECTION), LEFT_OUT),
    (
        with_clip({ClipSlotSetting.REPEAT: MIN_REPEAT + 1, ClipSlotSetting.MORPH_TO: TUNE, ClipSlotSetting.MORPH_STYLE: NOT_A_CHOICE}),
        (*CLIP, ClipSlotSetting.MORPH_STYLE), FIRST_MORPH_STYLE,
    ),
    # A pattern's settings.
    (with_pattern({PatternSetting.DIRECTION: NOT_A_CHOICE}), (*PATTERN, PatternSetting.DIRECTION), LEFT_OUT),
    (with_pattern({PatternSetting.STEP_SIZE: MAX_STEP_SIZE + 1}), (*PATTERN, PatternSetting.STEP_SIZE), MAX_STEP_SIZE),
    (with_pattern({PatternSetting.ENTRY_SIZE: MAX_GATE + 1}), (*PATTERN, PatternSetting.ENTRY_SIZE), MAX_GATE),
    # A pattern's rows, where every step that needs it is corrected at once.
    (
        with_pattern({Row.DEGREE: [A_DEGREE] * STEPS, Row.VELOCITY: [MAX_VELOCITY + 1, None, MIN_VELOCITY - 1, A_VELOCITY]}),
        (*PATTERN, Row.VELOCITY), [MAX_VELOCITY, None, MIN_VELOCITY, A_VELOCITY],
    ),
    (
        with_pattern({Row.DEGREE: [A_DEGREE] * STEPS, Row.PROBABILITY: [MAX_PROBABILITY + 1, MIN_PROBABILITY - 1, None, None]}),
        (*PATTERN, Row.PROBABILITY), [MAX_PROBABILITY, MIN_PROBABILITY, None, None],
    ),
    (with_pattern({Row.DEGREE: [MIN_DEGREE - 1, A_DEGREE, None, None]}), (*PATTERN, Row.DEGREE), [MIN_DEGREE, A_DEGREE, None, None]),
    (
        with_pattern({Row.DEGREE: [A_DEGREE] * STEPS, Row.OCTAVE: [MAX_OCTAVE + 1, MIN_OCTAVE - 1, None, None]}),
        (*PATTERN, Row.OCTAVE), [MAX_OCTAVE, MIN_OCTAVE, None, None],
    ),
    (
        with_pattern({Row.DEGREE: [A_DEGREE] * STEPS, Row.RATCHET: [MIN_RATCHET - 1, None, None, None]}),
        (*PATTERN, Row.RATCHET), [MIN_RATCHET, None, None, None],
    ),
    (
        with_pattern({Row.DEGREE: [A_DEGREE] * STEPS, Row.RATCHET: [MAX_RATCHET + 1, MIN_RATCHET, None, None]}),
        (*PATTERN, Row.RATCHET), [MAX_RATCHET, MIN_RATCHET, None, None],
    ),
    (
        with_pattern({Row.DEGREE: [A_DEGREE] * STEPS, Row.RATCHET_OFFSET: [MAX_RATCHET_OFFSET + 1, -MAX_RATCHET_OFFSET - 1, None, None]}),
        (*PATTERN, Row.RATCHET_OFFSET), [MAX_RATCHET_OFFSET, -MAX_RATCHET_OFFSET, None, None],
    ),
    (
        with_pattern({Row.DEGREE: [A_DEGREE] * STEPS, Row.GATE: [QUARTER, MAX_GATE + 1, None, None]}),
        (*PATTERN, Row.GATE), [QUARTER, MAX_GATE, None, None],
    ),
    (with_pattern({FIRST_CC: [MAX_CC_VALUE + 1, MIN_CC_VALUE - 1, None, None]}), (*PATTERN, FIRST_CC), [MAX_CC_VALUE, MIN_CC_VALUE, None, None]),
    (
        with_pattern({AX_ADD: [MAX_REGISTER_VALUE + 1, MIN_REGISTER_VALUE - 1, None, None]}),
        (*PATTERN, AX_ADD), [MAX_REGISTER_VALUE, MIN_REGISTER_VALUE, None, None],
    ),
    # A register.
    (with_register({RegisterSetting.MAXIMUM: MAX_REGISTER_VALUE + 1}), (*REGISTER, RegisterSetting.MAXIMUM), MAX_REGISTER_VALUE),
    (with_register({RegisterSetting.MINIMUM: MIN_REGISTER_VALUE - 1}), (*REGISTER, RegisterSetting.MINIMUM), MIN_REGISTER_VALUE),
    # A groove.
    (
        with_groove({GrooveSetting.CELLS: [MAX_GROOVE_AMOUNT + 1, STRAIGHT, MIN_GROOVE_AMOUNT - 1]}),
        (*GROOVE, GrooveSetting.CELLS), [MAX_GROOVE_AMOUNT, STRAIGHT, MIN_GROOVE_AMOUNT],
    ),
    (with_groove({GrooveSetting.CELL_LENGTH: MAX_GROOVE_CELL_LENGTH + 1}), (*GROOVE, GrooveSetting.CELL_LENGTH), MAX_GROOVE_CELL_LENGTH),
    # An arpeggiator.
    (with_arp({ArpSetting.OCTAVE_RANGE: MAX_OCTAVE_RANGE + 1}), (*ARP, ArpSetting.OCTAVE_RANGE), MAX_OCTAVE_RANGE),
    (with_arp({ArpSetting.ORDER: NOT_A_CHOICE}), (*ARP, ArpSetting.ORDER), LEFT_OUT),
    (with_arp({ArpSetting.OCTAVE_JUMP: NOT_A_CHOICE}), (*ARP, ArpSetting.OCTAVE_JUMP), LEFT_OUT),
    (with_arp({ArpSetting.OFFSETS: [MAX_OFFSET + 1, None, -MAX_OFFSET - 1]}), (*ARP, ArpSetting.OFFSETS), [MAX_OFFSET, None, -MAX_OFFSET]),
]
# Data with something wrong that no allowed value is near, which is refused as it always was.
REFUSED = [
    with_clip({ClipSlotSetting.CHAIN: NOT_A_NAME}),
    with_clip({ClipSlotSetting.MORPH_TO: NOT_A_NAME, ClipSlotSetting.MORPH_STYLE: FIRST_MORPH_STYLE, ClipSlotSetting.REPEAT: MIN_REPEAT + 1}),
    with_clip({ClipSlotSetting.LOOP: 1}),
    with_song({SongSetting.SCALE: NOT_A_NAME}),
    with_song({SongSetting.TEMPO: NOT_A_NUMBER}),
    with_song({NOT_A_NAME: A_DEGREE}),
    with_song({Section.SCENES: NOT_A_NAME}),
    with_track({TrackSetting.TRANSPOSE: NOT_A_NUMBER}),
    with_track({TrackSetting.TRANSPOSE: HALF}),
    with_track({TrackSetting.DRUM: 1}),
    with_track({NOT_A_NAME: A_DEGREE}),
    with_pattern({Row.DEGREE: [A_DEGREE] * STEPS, Row.VELOCITY: [NOT_A_NUMBER, None, None, None]}),
    with_pattern({Row.DEGREE: [A_DEGREE] * STEPS, Row.VELOCITY: [MAX_VELOCITY + 1]}),
    with_pattern({Row.DEGREE: [A_DEGREE] * STEPS, Row.TIE: [True, False, False, False]}),
    with_pattern({PatternSetting.DRUM: True, Row.DEGREE: [STRAIGHT, None, None, None]}),
    with_pattern({PatternSetting.STEP_SIZE: STRAIGHT}),
    with_pattern({PatternSetting.STEP_SIZE: NOT_A_NUMBER}),
    with_groove({GrooveSetting.CELLS: []}),
    with_arp({ArpSetting.SEED: NOT_A_NUMBER}),
    {NOT_A_NAME: A_DEGREE},
    {SetlistSetting.TITLE: A_DEGREE},
    [NOT_A_NAME],
]


class TestCorrection(unittest.TestCase):
    """One correction on its own: what it does to the data and how it's described."""

    def test_applying_one_puts_the_value_in_the_data(self):
        data = {TEMPO: FAR_TOO_MANY}
        Correction(holder=data, key=TEMPO, name=TEMPO, found=FAR_TOO_MANY, used=A_VELOCITY).apply()
        self.assertEqual(data, {TEMPO: A_VELOCITY})

    def test_applying_one_that_leaves_the_setting_out_takes_it_out_of_the_data(self):
        data = {TEMPO: FAR_TOO_MANY, LEAD: A_DEGREE}
        Correction(holder=data, key=TEMPO, name=TEMPO, found=FAR_TOO_MANY, used=LEFT_OUT).apply()
        self.assertEqual(data, {LEAD: A_DEGREE})

    def test_it_says_where_what_was_found_and_what_is_used(self):
        correction = Correction(holder={}, key=TEMPO, name=TEMPO, found=FAR_TOO_MANY, used=A_VELOCITY)
        correction.set_place(A_PLACE)
        self.assertEqual(correction.described(), MSG_CORRECTED.format(where=A_PLACE, name=TEMPO, found=FAR_TOO_MANY, used=A_VELOCITY))
        self.assertEqual((correction.get_name(), correction.get_found(), correction.get_used()), (TEMPO, FAR_TOO_MANY, A_VELOCITY))
        self.assertIsNone(correction.get_count())

    def test_a_setting_taken_out_is_said_to_become_the_default(self):
        correction = Correction(holder={}, key=TEMPO, name=TEMPO, found=NOT_A_CHOICE, used=LEFT_OUT)
        correction.set_place(A_PLACE)
        self.assertEqual(correction.described(), MSG_CORRECTED_TO_DEFAULT.format(where=A_PLACE, name=TEMPO, found=NOT_A_CHOICE))

    def test_a_list_is_one_line_with_a_count_of_the_values_changed(self):
        found = [FAR_TOO_MANY, None, A_VELOCITY, FAR_TOO_MANY]
        used = [A_VELOCITY, None, A_VELOCITY, A_VELOCITY]
        correction = Correction(holder={}, key=Row.VELOCITY, name=Row.VELOCITY, found=found, used=used)
        correction.set_place(A_PLACE)
        self.assertEqual(correction.get_count(), 2)
        self.assertEqual(correction.described(), MSG_CORRECTED_SEVERAL.format(where=A_PLACE, name=Row.VELOCITY, count=2))
        self.assertEqual(changed_count(found=found, used=used), 2)
        self.assertIsNone(changed_count(found=FAR_TOO_MANY, used=A_VELOCITY))

    def test_a_place_never_names_the_setting_twice(self):
        self.assertEqual(place_without(where=A_PLACE_WITH_THE_NAME, name=TEMPO), 'song (verse)')
        self.assertEqual(place_without(where=A_PLACE, name=TEMPO), A_PLACE)
        self.assertEqual(place_without(where=TEMPO, name=TEMPO), MSG_THE_FILE)
        self.assertEqual(place_without(where=None, name=TEMPO), MSG_THE_FILE)


class TestEveryValueWithOneNearItIsCorrected(unittest.TestCase):
    """Each setting and each row of each class, wrong in one value: read strictly it is refused, and read corrected it has the nearest allowed value."""

    def test_reading_strictly_refuses_and_carries_the_correction(self):
        for data, path, expected in CORRECTED:
            with self.subTest(path=path), self.assertRaises(SongFileError) as refused:
                Setlist.from_data(data=copy.deepcopy(data), one_song_name=VERSE)
            self.assertIsNotNone(refused.exception.get_correction(), path)

    def test_reading_corrected_puts_the_nearest_allowed_value_there(self):
        for data, path, expected in CORRECTED:
            with self.subTest(path=path):
                setlist, corrections = Setlist.from_data_corrected(data=data, one_song_name=VERSE)
                self.assertEqual(len(corrections), 1)
                self.assertEqual(value_at(data=setlist.to_data(), path=path), ABSENT if expected is LEFT_OUT else expected)

    def test_the_correction_says_what_was_found_and_what_is_used(self):
        for data, path, expected in CORRECTED:
            with self.subTest(path=path):
                setlist, corrections = Setlist.from_data_corrected(data=data, one_song_name=VERSE)
                self.assertEqual(corrections[0].get_found(), value_at(data=data, path=path))
                self.assertEqual(corrections[0].get_used(), expected)
                self.assertEqual(corrections[0].get_name(), path[-1])

    def test_the_data_given_is_left_as_it_was(self):
        for data, path, expected in CORRECTED:
            with self.subTest(path=path):
                before = copy.deepcopy(data)
                Setlist.from_data_corrected(data=data, one_song_name=VERSE)
                self.assertEqual(data, before)

    def test_the_corrected_set_reads_strictly_once_written(self):
        for data, path, expected in CORRECTED:
            with self.subTest(path=path):
                setlist, corrections = Setlist.from_data_corrected(data=data, one_song_name=VERSE)
                Setlist.from_data(data=setlist.to_data())

    def test_data_with_nothing_wrong_needs_no_corrections(self):
        setlist, corrections = Setlist.from_data_corrected(data=with_clip({}))
        self.assertEqual(corrections, [])
        self.assertEqual(setlist.to_data(), Setlist.from_data(data=with_clip({})).to_data())

    def test_a_row_is_corrected_once_however_many_steps_need_it(self):
        row = [MAX_VELOCITY + 1] * STEPS
        setlist, corrections = Setlist.from_data_corrected(data=with_pattern({Row.DEGREE: [A_DEGREE] * STEPS, Row.VELOCITY: row}))
        self.assertEqual(len(corrections), 1)
        self.assertEqual(corrections[0].get_count(), STEPS)
        self.assertEqual(setlist.get_pattern(TUNE).to_data()[Row.VELOCITY], [MAX_VELOCITY] * STEPS)

    def test_several_wrong_values_are_each_corrected_in_the_order_the_file_is_read(self):
        data = {
            SetlistSetting.DEFAULT_OCTAVE: MAX_OCTAVE + 1,
            **with_pattern({PatternSetting.DIRECTION: NOT_A_CHOICE, FIRST_CC: [MAX_CC_VALUE + 1, None, None, None]}),
            **with_track({TrackSetting.TRANSPOSE: MAX_TRANSPOSE + 1}),
        }
        setlist, corrections = Setlist.from_data_corrected(data=data, one_song_name=VERSE)
        self.assertEqual(
            [correction.get_name() for correction in corrections],
            [SetlistSetting.DEFAULT_OCTAVE, PatternSetting.DIRECTION, FIRST_CC, TrackSetting.TRANSPOSE],
        )
        self.assertEqual(corrections[-1].get_place(), 'song (verse), track (lead)')
        self.assertEqual(corrections[0].get_place(), MSG_THE_FILE)
        self.assertEqual(corrections[1].get_place(), 'pattern (tune)')
        self.assertEqual(corrections[2].get_place(), 'pattern (tune)')


class TestTheNearestStepValue(unittest.TestCase):

    def test_a_row_with_limits_has_the_nearest_end(self):
        self.assertEqual(nearest_step_value(row=Row.VELOCITY, value=MAX_VELOCITY + 1, drum=False), MAX_VELOCITY)
        self.assertEqual(nearest_step_value(row=Row.VELOCITY, value=A_VELOCITY, drum=False), A_VELOCITY)
        self.assertEqual(nearest_step_value(row=Row.GATE, value=MAX_GATE + 1, drum=False), MAX_GATE)
        self.assertIsNone(nearest_step_value(row=Row.VELOCITY, value=None, drum=False))

    def test_a_drum_pattern_has_no_nearest_note_letter(self):
        self.assertIsNot(nearest_step_value(row=Row.DEGREE, value=STRAIGHT, drum=True), MIN_DEGREE)
        self.assertEqual(nearest_step_value(row=Row.DEGREE, value=STRAIGHT, drum=False), MIN_DEGREE)


class TestWhatIsStillRefused(unittest.TestCase):
    """A name that doesn't exist, an unknown setting, the wrong structure and a value of the wrong type have no correction."""

    def test_reading_strictly_refuses_with_no_correction(self):
        for data in REFUSED:
            with self.subTest(data=data), self.assertRaises(SongFileError) as refused:
                Setlist.from_data(data=copy.deepcopy(data), one_song_name=VERSE)
            self.assertIsNone(refused.exception.get_correction(), data)

    def test_reading_corrected_refuses_in_the_same_words(self):
        for data in REFUSED:
            with self.subTest(data=data):
                with self.assertRaises(SongFileError) as strictly:
                    Setlist.from_data(data=copy.deepcopy(data), one_song_name=VERSE)
                with self.assertRaises(SongFileError) as corrected:
                    Setlist.from_data_corrected(data=data, one_song_name=VERSE)
                self.assertEqual(str(corrected.exception), str(strictly.exception))

    def test_one_problem_with_no_correction_refuses_a_file_whose_other_values_could_be_corrected(self):
        data = {SetlistSetting.DEFAULT_OCTAVE: MAX_OCTAVE + 1, **with_clip({ClipSlotSetting.CHAIN: NOT_A_NAME})}
        with self.assertRaisesRegex(SongFileError, NOT_A_NAME):
            Setlist.from_data_corrected(data=data, one_song_name=VERSE)

    def test_two_values_that_no_longer_fit_each_other_once_corrected_are_refused(self):
        data = with_track({TrackSetting.LOWEST_OCTAVE: MAX_OCTAVE + 1, TrackSetting.HIGHEST_OCTAVE: MIN_OCTAVE})
        with self.assertRaises(SongFileError) as refused:
            Setlist.from_data_corrected(data=data, one_song_name=VERSE)
        self.assertIn(ERR_OCTAVE_RANGE_BACKWARDS.format(lowest=MAX_OCTAVE, highest=MIN_OCTAVE), str(refused.exception))

    def test_going_back_to_earlier_data_stays_strict(self):
        setlist = Setlist.new()
        with self.assertRaises(SongFileError):
            setlist.restore({SetlistSetting.DEFAULT_OCTAVE: MAX_OCTAVE + 1})


class TestOlderFilesAreCorrectedToo(unittest.TestCase):

    def test_a_file_of_one_song_is_read_as_a_set_and_then_corrected(self):
        data = {Section.TRACKS: {LEAD: {TrackSetting.TRANSPOSE: MAX_TRANSPOSE + 1}}, Section.SCENES: []}
        setlist, corrections = Setlist.from_data_corrected(data=data, one_song_name=VERSE)
        self.assertEqual(setlist.get_song(VERSE).get_track(LEAD).get_transpose(), MAX_TRANSPOSE)
        self.assertEqual(corrections[0].get_place(), 'song (verse), track (lead)')

    def test_an_octave_in_lives_numbers_is_moved_before_it_is_corrected(self):
        data = {SetlistSetting.VERSION: A_VERSION_WITH_LIVE_OCTAVES, SetlistSetting.DEFAULT_OCTAVE: MAX_OCTAVE}
        setlist, corrections = Setlist.from_data_corrected(data=data)
        self.assertEqual(corrections[0].get_found(), MAX_OCTAVE + LIVE_OCTAVE_OFFSET)
        self.assertEqual(setlist.get_default_octave(), MAX_OCTAVE)


class TestTheSampleSets(unittest.TestCase):
    """The two files made for these tests, read the way the tracker and the command line read a file."""

    def file_bytes(self, path):
        with open(path, READ_BYTES) as file:
            return file.read()

    def written(self, path):
        with open(path) as file:
            return yaml.safe_load(file)

    def test_the_set_with_every_value_near_an_allowed_one_is_refused_strictly_and_opens_corrected(self):
        with self.assertRaises(SongFileError) as refused:
            Setlist.read_file(OUT_OF_RANGE)
        self.assertIsNotNone(refused.exception.get_correction())
        setlist, corrections = Setlist.read_file_corrected(OUT_OF_RANGE)
        self.assertGreater(len(corrections), 1)
        Setlist.from_data(data=setlist.to_data())

    def test_every_velocity_step_out_of_range_is_one_correction(self):
        written = self.written(OUT_OF_RANGE)[Section.PATTERNS][TUNE][Row.VELOCITY]
        too_loud = [value for value in written if value is not None and value > MAX_VELOCITY]
        setlist, corrections = Setlist.read_file_corrected(OUT_OF_RANGE)
        velocities = [correction for correction in corrections if correction.get_name() == Row.VELOCITY]
        self.assertEqual(len(velocities), 1)
        self.assertEqual(velocities[0].get_count(), len(too_loud))
        self.assertGreater(len(too_loud), 1)

    def test_reading_a_file_corrected_never_changes_the_file(self):
        before = self.file_bytes(OUT_OF_RANGE)
        Setlist.read_file_corrected(OUT_OF_RANGE)
        self.assertEqual(self.file_bytes(OUT_OF_RANGE), before)

    def test_the_set_with_a_name_that_does_not_exist_is_refused_either_way(self):
        with self.assertRaises(SongFileError):
            Setlist.read_file(OUT_OF_RANGE_AND_BROKEN)
        with self.assertRaises(SongFileError) as refused:
            Setlist.read_file_corrected(OUT_OF_RANGE_AND_BROKEN)
        self.assertIsNone(refused.exception.get_correction())
        chain = self.written(OUT_OF_RANGE_AND_BROKEN)[Section.SONGS][VERSE][Section.SCENES][FIRST_SCENE][SceneSetting.TRACKS][LEAD][ClipSlotSetting.CHAINS][0]
        self.assertIn(chain, str(refused.exception))


if __name__ == '__main__':
    unittest.main()
