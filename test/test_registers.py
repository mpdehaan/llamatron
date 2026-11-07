# llamatron: a Python language and framework for producing MIDI clips.
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

"""The registers AX to DX: what steps add to them, how they stop or wrap, and the notes and velocities that use them.

Most tests say what they expect as the register values each note should see, like [ADD,
MAXIMUM, MAXIMUM], and scale_notes turns those into the notes of C major they move C3 to.
"""

import unittest

from llamatron.composition.defaults import DEFAULT_REGISTER_MAXIMUM, DEFAULT_REGISTER_MINIMUM, DEFAULT_REGISTER_VALUE
from llamatron.composition.file_format import (
    REGISTER_ADD_ROWS, REGISTER_NAMES, REGISTER_NOTE_ROWS, REGISTER_VELOCITY_ROWS, PatternSetting, RegisterName,
    RegisterSetting, Row, SceneSetting, Section,
)
from llamatron.composition.limits import MAX_REGISTER_VALUE, MAX_VELOCITY, MIN_REGISTER_VALUE, MIN_VELOCITY
from llamatron.composition.song import Song
from llamatron.composition.song_file_error import SongFileError
from llamatron.renderers.timing import timed_events
from rendering import render_data

AX = RegisterName.AX
BX = RegisterName.BX
CX = RegisterName.CX
DX = RegisterName.DX
# Every pattern here plays C3, MIDI note 60, in C major, unless a register moves it.
OCTAVE = 3
ROOT = 60
C_MAJOR_STEPS = [0, 2, 4, 5, 7, 9, 11]
HALF_STEPS_PER_OCTAVE = 12
# A quarter note a step, so that every step is easy to tell apart.
STEP_SIZE = '1/4'
VELOCITY = 100


def scale_notes(values):
    """Return the MIDI notes that register values move C3 to, along C major, one for each value."""
    return [scale_note(value) for value in values]


def scale_note(value):
    octaves, place = divmod(value, len(C_MAJOR_STEPS))
    return ROOT + octaves * HALF_STEPS_PER_OCTAVE + C_MAJOR_STEPS[place]


def pattern(steps, **rows):
    """Return a pattern of steps that all play C3 unless rows say otherwise."""
    return {PatternSetting.STEPS: steps, PatternSetting.STEP_SIZE: STEP_SIZE, Row.DEGREE: [1] * steps, Row.OCTAVE: [OCTAVE] * steps, **rows}


def song(patterns, scenes, registers=None, tracks=('lead',)):
    data = {
        Section.SCALES: {'main': {'root': 'C', 'type': 'major'}}, 'scale': 'main',
        Section.PATTERNS: patterns, Section.TRACKS: {name: {} for name in tracks}, Section.SCENES: scenes,
    }
    if registers:
        data[Section.REGISTERS] = registers
    return data


def one_clip(rows, steps=1, repeat=1, registers=None, drum=False):
    """Return a song whose lead plays one pattern, with rows, repeated."""
    made = pattern(steps, **rows)
    if drum:
        made.update({PatternSetting.DRUM: True, Row.DEGREE: ['C'] * steps})
    return song({'x': made}, [{SceneSetting.TRACKS: {'lead': {'pattern': 'x', 'repeat': repeat}}}], registers)


def every_step(value, steps=1):
    """Return a row with the same value on every step."""
    return [value] * steps


def played(data, scene=1, track='lead'):
    """Return (pitch, velocity) for each note a track plays in a scene, in time order."""
    grid = render_data(data)
    found = grid.get_clip(grid.scenes[scene - 1], [t for t in grid.tracks if t.name == track][0])
    return [(pitch, velocity) for _, _, pitch, velocity in sorted(timed_events(found, found.scale)[0])]


def pitches(data, **where):
    return [pitch for pitch, _ in played(data, **where)]


def velocities(data, **where):
    return [velocity for _, velocity in played(data, **where)]


# AX's rows, which most tests use.
ADDS = REGISTER_ADD_ROWS[AX]
USES_NOTE = REGISTER_NOTE_ROWS[AX]
USES_VELOCITY = REGISTER_VELOCITY_ROWS[AX]


class TestAddingAndUsing(unittest.TestCase):

    ADD = 1

    def test_a_step_adds_before_it_uses_the_value(self):
        data = one_clip({ADDS: [0, self.ADD, 0], USES_NOTE: every_step(True, 3)}, steps=3)
        self.assertEqual(pitches(data), scale_notes([0, self.ADD, self.ADD]))

    def test_the_value_builds_up_across_repeats(self):
        data = one_clip({ADDS: [self.ADD], USES_NOTE: [True]}, repeat=3)
        self.assertEqual(pitches(data), scale_notes([self.ADD, 2 * self.ADD, 3 * self.ADD]))

    def test_only_steps_that_use_a_register_move(self):
        data = one_clip({ADDS: [self.ADD, 0], USES_NOTE: [False, True]}, steps=2)
        self.assertEqual(pitches(data), scale_notes([0, self.ADD]))

    def test_a_step_with_no_note_still_adds(self):
        data = one_clip({Row.DEGREE: [None, 1], ADDS: [self.ADD, 0], USES_NOTE: [False, True]}, steps=2)
        self.assertEqual(pitches(data), scale_notes([self.ADD]))

    def test_each_register_is_separate_and_the_ones_used_add_up(self):
        other_add = 2
        rows = {ADDS: [self.ADD], REGISTER_ADD_ROWS[BX]: [other_add], USES_NOTE: [True], REGISTER_NOTE_ROWS[BX]: [False]}
        self.assertEqual(pitches(one_clip(rows)), scale_notes([self.ADD]))
        rows[REGISTER_NOTE_ROWS[BX]] = [True]
        self.assertEqual(pitches(one_clip(rows)), scale_notes([self.ADD + other_add]))

    def test_it_starts_at_its_default(self):
        default = 2
        data = one_clip({USES_NOTE: [True]}, registers={AX: {RegisterSetting.DEFAULT: default}})
        self.assertEqual(pitches(data), scale_notes([default]))

    def test_a_ratchet_adds_once_and_every_slice_uses_the_same_value(self):
        slices = 3
        data = one_clip({Row.RATCHET: [slices], ADDS: [self.ADD], USES_NOTE: [True]})
        self.assertEqual(pitches(data), scale_notes([self.ADD] * slices))

    def test_a_note_pushed_past_the_midi_range_moves_by_octaves_to_fit(self):
        # Every register at its highest, all moving one of the highest notes.
        registers = {name: {RegisterSetting.MAXIMUM: MAX_REGISTER_VALUE} for name in REGISTER_NAMES}
        rows = {Row.OCTAVE: [8]}
        for name in REGISTER_NAMES:
            rows.update({REGISTER_ADD_ROWS[name]: [MAX_REGISTER_VALUE], REGISTER_NOTE_ROWS[name]: [True]})
        self.assertEqual(len(pitches(one_clip(rows, registers=registers))), 1)


class TestLimits(unittest.TestCase):

    def test_it_stops_at_the_maximum(self):
        add = 1
        maximum = 2
        data = one_clip({ADDS: [add], USES_NOTE: [True]}, repeat=4, registers={AX: {RegisterSetting.MAXIMUM: maximum}})
        self.assertEqual(pitches(data), scale_notes([add, maximum, maximum, maximum]))

    def test_it_stops_at_the_minimum(self):
        add = -1
        minimum = -1
        data = one_clip({ADDS: [add], USES_NOTE: [True]}, repeat=3, registers={AX: {RegisterSetting.MINIMUM: minimum}})
        self.assertEqual(pitches(data), scale_notes([minimum] * 3))

    def test_wrapping_jumps_to_the_other_end_and_drops_what_is_left(self):
        # Two adds go past the maximum, and land on the minimum rather than past it.
        add = 2
        maximum = 3
        registers = {AX: {RegisterSetting.MAXIMUM: maximum, RegisterSetting.WRAP: True}}
        data = one_clip({ADDS: [add], USES_NOTE: [True]}, repeat=4, registers=registers)
        lowest = DEFAULT_REGISTER_MINIMUM
        self.assertEqual(pitches(data), scale_notes([add, lowest, add, lowest]))

    def test_wrapping_below_the_minimum_jumps_to_the_maximum(self):
        add = -1
        minimum = -1
        maximum = 1
        registers = {AX: {RegisterSetting.MINIMUM: minimum, RegisterSetting.MAXIMUM: maximum, RegisterSetting.WRAP: True}}
        data = one_clip({ADDS: [add], USES_NOTE: [True]}, repeat=3, registers=registers)
        self.assertEqual(pitches(data), scale_notes([minimum, maximum, maximum + add]))


class TestVelocity(unittest.TestCase):

    LOWEST = {AX: {RegisterSetting.MINIMUM: MIN_REGISTER_VALUE}}

    def test_the_value_is_added_to_the_velocity(self):
        add = -20
        data = one_clip({Row.VELOCITY: [VELOCITY], ADDS: [add], USES_VELOCITY: [True]}, repeat=3, registers=self.LOWEST)
        self.assertEqual(velocities(data), [VELOCITY + add, VELOCITY + 2 * add, VELOCITY + 3 * add])

    def test_the_velocity_stays_in_the_midi_range(self):
        rows = {Row.VELOCITY: [MIN_VELOCITY + 1], ADDS: [-2], USES_VELOCITY: [True]}
        self.assertEqual(velocities(one_clip(rows, registers=self.LOWEST)), [MIN_VELOCITY])

    def test_a_drum_pattern_can_use_registers_for_velocity(self):
        add = -10
        data = one_clip({ADDS: [add], USES_VELOCITY: [True]}, repeat=2, drum=True, registers=self.LOWEST)
        self.assertEqual(velocities(data), [MAX_VELOCITY + add, MAX_VELOCITY + 2 * add])

    def test_a_drum_pattern_cannot_move_notes_with_registers(self):
        with self.assertRaises(SongFileError):
            Song.from_data(one_clip({USES_NOTE: [True]}, drum=True))
        Song.from_data(one_clip({USES_NOTE: [False]}, drum=True))


class TestSharing(unittest.TestCase):

    STEPS = 3
    ADD = 1
    ONE_STEP = {'x': pattern(1, **{ADDS: [ADD], USES_NOTE: [True]})}

    def counted(self, tracks):
        """Return a song where a silent counter adds to AX on each step and the lead plays it."""
        patterns = {
            'count': {PatternSetting.STEPS: self.STEPS, PatternSetting.STEP_SIZE: STEP_SIZE, ADDS: every_step(self.ADD, self.STEPS)},
            'tune': pattern(self.STEPS, **{USES_NOTE: every_step(True, self.STEPS)}),
        }
        cells = {'counter': {'pattern': 'count'}, 'lead': {'pattern': 'tune'}}
        return song(patterns, [{SceneSetting.TRACKS: cells}], tracks=tracks)

    def scene(self, **settings):
        return {SceneSetting.TRACKS: {'lead': {'pattern': 'x'}}, **settings}

    def test_one_track_can_drive_another(self):
        expected = [self.ADD * count for count in range(1, self.STEPS + 1)]
        self.assertEqual(pitches(self.counted(('counter', 'lead'))), scale_notes(expected))

    def test_at_the_same_moment_tracks_go_in_track_order(self):
        # The lead comes first, so it only hears each count on its next step.
        expected = [self.ADD * count for count in range(self.STEPS)]
        self.assertEqual(pitches(self.counted(('lead', 'counter'))), scale_notes(expected))

    def test_values_carry_into_the_next_scene_unless_it_resets(self):
        data = song(self.ONE_STEP, [self.scene(), self.scene(), self.scene(**{SceneSetting.RESET: [AX]})])
        found = [pitches(data, scene=number) for number in (1, 2, 3)]
        self.assertEqual(found, [scale_notes([self.ADD]), scale_notes([2 * self.ADD]), scale_notes([self.ADD])])

    def test_a_repeating_scene_resets_only_as_it_first_starts(self):
        repeat = 3
        data = song(self.ONE_STEP, [self.scene(repeat=repeat, **{SceneSetting.RESET: [AX]})])
        found = [pitches(data, scene=number) for number in range(1, repeat + 1)]
        self.assertEqual(found, [scale_notes([self.ADD * count]) for count in range(1, repeat + 1)])

    def test_a_reset_only_resets_the_registers_it_names(self):
        patterns = {
            'x': pattern(1, **{ADDS: [self.ADD], REGISTER_ADD_ROWS[BX]: [self.ADD]}),
            'y': pattern(1, **{REGISTER_NOTE_ROWS[BX]: [True]}),
        }
        scenes = [self.scene(), {SceneSetting.RESET: [AX], SceneSetting.TRACKS: {'lead': {'pattern': 'y'}}}]
        self.assertEqual(pitches(song(patterns, scenes), scene=2), scale_notes([self.ADD]))

    def test_a_morph_target_uses_the_registers_but_does_not_add(self):
        target_add = 5
        patterns = {**self.ONE_STEP, 'y': pattern(1, **{ADDS: [target_add], USES_NOTE: [True]})}
        cells = {'lead': {'pattern': 'x', 'repeat': 2, 'morph_to': 'y', 'morph_style': 'left'}}
        # The second repeat is all target, which sees the first pattern's two adds and none of its own.
        self.assertEqual(pitches(song(patterns, [{SceneSetting.TRACKS: cells}])), scale_notes([self.ADD, 2 * self.ADD]))


class TestTheFile(unittest.TestCase):

    def test_settings_and_resets_save_and_load(self):
        registers = {AX: {RegisterSetting.MAXIMUM: 3, RegisterSetting.WRAP: True}, DX: {RegisterSetting.MINIMUM: -100}}
        data = one_clip({ADDS: [1], USES_NOTE: [True]}, registers=registers)
        data[Section.SCENES][0][SceneSetting.RESET] = [AX, DX]
        saved = Song.from_data(data).to_data()
        self.assertEqual(saved[Section.REGISTERS], registers)
        self.assertEqual(saved[Section.SCENES][0][SceneSetting.RESET], [AX, DX])

    def test_registers_the_file_leaves_out_have_their_defaults(self):
        register = Song.from_data({}).get_register(CX)
        self.assertEqual(
            (register.get_default(), register.get_minimum(), register.get_maximum(), register.wraps()),
            (DEFAULT_REGISTER_VALUE, DEFAULT_REGISTER_MINIMUM, DEFAULT_REGISTER_MAXIMUM, False),
        )

    def test_bad_settings_are_refused(self):
        for registers in [
            {'EX': {}}, {AX: {RegisterSetting.MAXIMUM: MAX_REGISTER_VALUE + 1}},
            {AX: {RegisterSetting.MINIMUM: DEFAULT_REGISTER_VALUE + 1}},
            {AX: {RegisterSetting.DEFAULT: DEFAULT_REGISTER_MAXIMUM + 1}},
            {AX: {RegisterSetting.WRAP: 'yes'}}, {AX: {'loud': 1}}, {AX: {RegisterSetting.MAXIMUM: 1.5}}, [AX],
        ]:
            with self.subTest(registers=registers), self.assertRaises(SongFileError):
                Song.from_data(one_clip({}, registers=registers))

    def test_bad_resets_are_refused(self):
        for reset in [['EX'], AX, [AX, AX]]:
            data = one_clip({})
            data[Section.SCENES][0][SceneSetting.RESET] = reset
            with self.subTest(reset=reset), self.assertRaises(SongFileError):
                Song.from_data(data)

    def test_bad_rows_are_refused(self):
        for rows in [
            {ADDS: [MAX_REGISTER_VALUE + 1]}, {ADDS: [MIN_REGISTER_VALUE - 1]}, {REGISTER_ADD_ROWS[BX]: ['x']},
            {REGISTER_NOTE_ROWS[CX]: [None]}, {REGISTER_VELOCITY_ROWS[DX]: [1]},
        ]:
            with self.subTest(rows=rows), self.assertRaises(SongFileError):
                Song.from_data(one_clip(rows))


if __name__ == '__main__':
    unittest.main()
