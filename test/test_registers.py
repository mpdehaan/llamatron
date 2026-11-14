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

"""The registers AX to DX: what steps add to them, how they stop or wrap, and the notes and velocities that use them.

Most tests say what they expect as the register values each note should see, like [ADD,
MAXIMUM, MAXIMUM], and scale_notes turns those into the notes of C major they move C3 to.
"""

import unittest

from llamatron.music.midi import HALF_STEPS_PER_OCTAVE
from llamatron.composition.clip_slot import morph_style_name
from llamatron.composition.defaults import DEFAULT_REGISTER_MAXIMUM, DEFAULT_REGISTER_MINIMUM, DEFAULT_REGISTER_VALUE
from llamatron.composition.file_format import (
    AtLimit, REGISTER_ADD_ROWS, REGISTER_NAMES, REGISTER_NOTE_ROWS, REGISTER_VELOCITY_ROWS, ClipSlotSetting, PatternSetting,
    RegisterName, RegisterSetting, RegisterUse, Row, ScaleSetting, SceneSetting, Section, SongSetting,
)
from llamatron.composition.limits import MAX_REGISTER_VALUE, MIN_REGISTER_VALUE
from llamatron.composition.named_scale import scale_type_name
from llamatron.generators.blend import BlendMode
from llamatron.music.midi import MAX_VELOCITY, MIN_VELOCITY
from llamatron.composition.song_file_error import SongFileError
from llamatron.music.note import NoteName
from llamatron.exporters.timing import timed_events
from rendering import render_data, song_from_data
from llamatron.music.scale import ScaleType

AX = RegisterName.AX
BX = RegisterName.BX
CX = RegisterName.CX
DX = RegisterName.DX
# Every pattern here plays middle C, MIDI note 60, in C major, unless a register moves it.
OCTAVE = 5
ROOT = 60
C_MAJOR_STEPS = [0, 2, 4, 5, 7, 9, 11]
# A quarter note a step, so that every step is easy to tell apart.
STEP_SIZE = '1/4'
VELOCITY = 100

# Names the tests give to their own things, and other values they use.
LEAD = 'lead'
MAIN = 'main'
X = 'x'
BASS = 'bass'
COUNT = 'count'
TUNE = 'tune'
COUNTER = 'counter'
Y = 'y'
EX = 'EX'
YES = 'yes'
LOUD = 'loud'


def scale_notes(values):
    """Return the MIDI notes that register values move C3 to, along C major, one for each value."""
    return [scale_note(value) for value in values]


def scale_note(value):
    octaves, place = divmod(value, len(C_MAJOR_STEPS))
    return ROOT + octaves * HALF_STEPS_PER_OCTAVE + C_MAJOR_STEPS[place]


def pattern(steps, **rows):
    """Return a pattern of steps that all play C3 unless rows say otherwise."""
    return {PatternSetting.STEPS: steps, PatternSetting.STEP_SIZE: STEP_SIZE, Row.DEGREE: [1] * steps, Row.OCTAVE: [OCTAVE] * steps, **rows}


def song(*, patterns, scenes, registers=None, tracks=(LEAD,)):
    data = {
        Section.SCALES: {MAIN: {ScaleSetting.ROOT: NoteName.C, ScaleSetting.TYPE: scale_type_name(ScaleType.MAJOR)}}, SongSetting.SCALE: MAIN,
        Section.PATTERNS: patterns, Section.TRACKS: {name: {} for name in tracks}, Section.SCENES: scenes,
    }
    if registers:
        data[Section.REGISTERS] = registers
    return data


def one_clip(*, rows, steps=1, repeat=1, registers=None, drum=False):
    """Return a song whose lead plays one pattern, with rows, repeated."""
    made = pattern(steps, **rows)
    if drum:
        made.update({PatternSetting.DRUM: True, Row.DEGREE: [NoteName.C] * steps})
    return song(patterns={X: made}, scenes=[{SceneSetting.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: X, ClipSlotSetting.REPEAT: repeat}}}], registers=registers)


def every_step(*, value, steps=1):
    """Return a row with the same value on every step."""
    return [value] * steps


def played(*, data, scene=1, track=LEAD):
    """Return (pitch, velocity) for each note a track plays in a scene, in time order."""
    grid = render_data(data)
    found = grid.get_clip(row=grid.get_rows()[scene - 1], column=[t for t in grid.get_columns() if t.get_name() == track][0])
    return [(pitch, velocity) for _, _, pitch, velocity in sorted(timed_events(clip=found, scale=found.get_scale())[0])]


def pitches(data, **where):
    return [pitch for pitch, _ in played(data=data, **where)]


def velocities(data, **where):
    return [velocity for _, velocity in played(data=data, **where)]


# AX's rows, which most tests use.
ADDS = REGISTER_ADD_ROWS[AX]
USES_NOTE = REGISTER_NOTE_ROWS[AX]
USES_VELOCITY = REGISTER_VELOCITY_ROWS[AX]
# What a step holds on a +Note or +Vel row: adds the register, subtracts it, or neither.
ADDS_IT = RegisterUse.ADD
SUBTRACTS_IT = RegisterUse.SUBTRACT
OFF = RegisterUse.OFF


class TestWhetherASongAddsToRegisters(unittest.TestCase):
    """Render plays a first pass to record register changes only in songs where a step adds to a register.

    The other tests here cover songs that add. These cover the ones that don't, which play the
    same way, and the check that tells the two apart.
    """

    ADD = 1
    NO_ADD = 0
    DEFAULT = 2

    def test_a_song_adds_when_a_step_has_a_non_zero_change(self):
        self.assertTrue(song_from_data(one_clip(rows={ADDS: [self.ADD]})).changes_registers())

    def test_a_song_does_not_add_with_no_change_rows_or_only_zeros(self):
        self.assertFalse(song_from_data(one_clip(rows={})).changes_registers())
        self.assertFalse(song_from_data(one_clip(rows={ADDS: [self.NO_ADD]})).changes_registers())
        self.assertFalse(song_from_data(one_clip(rows={USES_NOTE: [ADDS_IT], USES_VELOCITY: [ADDS_IT]})).changes_registers())

    def test_a_change_row_of_zeros_plays_the_same_as_no_change_row(self):
        registers = {AX: {RegisterSetting.DEFAULT: self.DEFAULT}}
        with_zeros = one_clip(rows={ADDS: every_step(value=self.NO_ADD, steps=2), USES_NOTE: every_step(value=ADDS_IT, steps=2)}, steps=2, registers=registers)
        without = one_clip(rows={USES_NOTE: every_step(value=ADDS_IT, steps=2)}, steps=2, registers=registers)
        self.assertEqual(played(data=with_zeros), played(data=without))
        self.assertEqual(pitches(without), scale_notes([self.DEFAULT, self.DEFAULT]))

    def test_a_song_that_does_not_add_uses_the_defaults_on_every_track_and_scene(self):
        patterns = {X: pattern(1, **{USES_NOTE: [ADDS_IT], USES_VELOCITY: [ADDS_IT], Row.VELOCITY: [VELOCITY]})}
        scenes = [
            {SceneSetting.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: X}, BASS: {ClipSlotSetting.PATTERN: X}}},
            {SceneSetting.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: X}}},
        ]
        data = song(patterns=patterns, scenes=scenes, registers={AX: {RegisterSetting.DEFAULT: self.DEFAULT}}, tracks=(LEAD, BASS))
        expected = [(scale_note(self.DEFAULT), VELOCITY + self.DEFAULT)]
        self.assertEqual(played(data=data, scene=1, track=LEAD), expected)
        self.assertEqual(played(data=data, scene=1, track=BASS), expected)
        self.assertEqual(played(data=data, scene=2, track=LEAD), expected)


class TestWhetherAPatternUsesRegisters(unittest.TestCase):
    """A pattern whose steps neither add to a register nor use one plays without asking the registers anything.

    The other tests here cover patterns that do ask. These cover the ones that don't, which must
    play as they would if they had asked and been told nothing applied to them.
    """

    DEFAULT = 2
    REGISTERS = {AX: {RegisterSetting.DEFAULT: DEFAULT}}
    STEPS = 2

    def test_rows_switched_off_play_the_same_as_no_rows(self):
        off = every_step(value=OFF, steps=self.STEPS)
        switched_off = one_clip(rows={USES_NOTE: off, USES_VELOCITY: off}, steps=self.STEPS, registers=self.REGISTERS)
        without = one_clip(rows={}, steps=self.STEPS, registers=self.REGISTERS)
        self.assertEqual(played(data=switched_off), played(data=without))
        # Neither is moved by the register's value, which a step that uses the register is.
        self.assertEqual(pitches(without), scale_notes([0, 0]))
        using = one_clip(rows={USES_NOTE: every_step(value=ADDS_IT, steps=self.STEPS)}, steps=self.STEPS, registers=self.REGISTERS)
        self.assertEqual(pitches(using), scale_notes([self.DEFAULT, self.DEFAULT]))

    def test_a_pattern_that_uses_none_is_not_moved_by_what_another_track_adds(self):
        counting = pattern(self.STEPS, **{ADDS: every_step(value=1, steps=self.STEPS), USES_NOTE: every_step(value=ADDS_IT, steps=self.STEPS)})
        clips = {LEAD: {ClipSlotSetting.PATTERN: X}, BASS: {ClipSlotSetting.PATTERN: COUNT}}
        data = song(patterns={X: pattern(self.STEPS), COUNT: counting}, scenes=[{SceneSetting.TRACKS: clips}], tracks=(LEAD, BASS))
        self.assertEqual(pitches(data, track=LEAD), scale_notes([0, 0]))
        self.assertEqual(pitches(data, track=BASS), scale_notes([1, 2]))

    def test_a_pattern_that_only_adds_moves_another_that_only_uses(self):
        adding = pattern(self.STEPS, **{ADDS: every_step(value=1, steps=self.STEPS)})
        reading = pattern(self.STEPS, **{USES_NOTE: every_step(value=ADDS_IT, steps=self.STEPS)})
        clips = {LEAD: {ClipSlotSetting.PATTERN: X}, BASS: {ClipSlotSetting.PATTERN: COUNT}}
        data = song(patterns={X: adding, COUNT: reading}, scenes=[{SceneSetting.TRACKS: clips}], tracks=(LEAD, BASS))
        # The lead adds and is not moved. The bass comes after the lead at the same moment, so each of its steps sees that step's add.
        self.assertEqual(pitches(data, track=LEAD), scale_notes([0, 0]))
        self.assertEqual(pitches(data, track=BASS), scale_notes([1, 2]))


class TestAddingAndUsing(unittest.TestCase):

    ADD = 1

    def test_a_step_adds_before_it_uses_the_value(self):
        data = one_clip(rows={ADDS: [0, self.ADD, 0], USES_NOTE: every_step(value=ADDS_IT, steps=3)}, steps=3)
        self.assertEqual(pitches(data), scale_notes([0, self.ADD, self.ADD]))

    def test_the_value_builds_up_across_repeats(self):
        data = one_clip(rows={ADDS: [self.ADD], USES_NOTE: [ADDS_IT]}, repeat=3)
        self.assertEqual(pitches(data), scale_notes([self.ADD, 2 * self.ADD, 3 * self.ADD]))

    def test_only_steps_that_use_a_register_move(self):
        data = one_clip(rows={ADDS: [self.ADD, 0], USES_NOTE: [OFF, ADDS_IT]}, steps=2)
        self.assertEqual(pitches(data), scale_notes([0, self.ADD]))

    def test_a_step_with_no_note_still_adds(self):
        data = one_clip(rows={Row.DEGREE: [None, 1], ADDS: [self.ADD, 0], USES_NOTE: [OFF, ADDS_IT]}, steps=2)
        self.assertEqual(pitches(data), scale_notes([self.ADD]))

    def test_each_register_is_separate_and_the_ones_used_add_up(self):
        other_add = 2
        rows = {ADDS: [self.ADD], REGISTER_ADD_ROWS[BX]: [other_add], USES_NOTE: [ADDS_IT], REGISTER_NOTE_ROWS[BX]: [OFF]}
        self.assertEqual(pitches(one_clip(rows=rows)), scale_notes([self.ADD]))
        rows[REGISTER_NOTE_ROWS[BX]] = [ADDS_IT]
        self.assertEqual(pitches(one_clip(rows=rows)), scale_notes([self.ADD + other_add]))

    def test_it_starts_at_its_default(self):
        default = 2
        data = one_clip(rows={USES_NOTE: [ADDS_IT]}, registers={AX: {RegisterSetting.DEFAULT: default}})
        self.assertEqual(pitches(data), scale_notes([default]))

    def test_a_step_that_subtracts_moves_down_by_the_registers_value(self):
        # The user's design of 2026-11-09: - on a +Note row subtracts the register, where the row was a toggle that could only add.
        data = one_clip(rows={ADDS: [self.ADD, 0, 0], USES_NOTE: [SUBTRACTS_IT, ADDS_IT, OFF]}, steps=3)
        self.assertEqual(pitches(data), scale_notes([-self.ADD, self.ADD, 0]))

    def test_adding_one_register_and_subtracting_another_nets_the_difference(self):
        other_add = 3
        rows = {ADDS: [self.ADD], REGISTER_ADD_ROWS[BX]: [other_add], USES_NOTE: [ADDS_IT], REGISTER_NOTE_ROWS[BX]: [SUBTRACTS_IT]}
        self.assertEqual(pitches(one_clip(rows=rows)), scale_notes([self.ADD - other_add]))

    def test_a_file_from_before_the_change_holding_true_still_adds(self):
        data = one_clip(rows={ADDS: [self.ADD, 0], USES_NOTE: [False, True]}, steps=2)
        self.assertEqual(pitches(data), scale_notes([0, self.ADD]))

    def test_a_ratchet_adds_once_and_every_slice_uses_the_same_value(self):
        slices = 3
        data = one_clip(rows={Row.RATCHET: [slices], ADDS: [self.ADD], USES_NOTE: [ADDS_IT]})
        self.assertEqual(pitches(data), scale_notes([self.ADD] * slices))

    def test_a_note_pushed_past_the_midi_range_moves_by_octaves_to_fit(self):
        # Every register at its highest, all moving one of the highest notes.
        registers = {name: {RegisterSetting.MAXIMUM: MAX_REGISTER_VALUE, RegisterSetting.ALLOWED_INC_MAX: MAX_REGISTER_VALUE} for name in REGISTER_NAMES}
        rows = {Row.OCTAVE: [10]}
        for name in REGISTER_NAMES:
            rows.update({REGISTER_ADD_ROWS[name]: [MAX_REGISTER_VALUE], REGISTER_NOTE_ROWS[name]: [ADDS_IT]})
        self.assertEqual(len(pitches(one_clip(rows=rows, registers=registers))), 1)


class TestLimits(unittest.TestCase):

    def test_it_stops_at_the_maximum(self):
        add = 1
        maximum = 2
        data = one_clip(rows={ADDS: [add], USES_NOTE: [ADDS_IT]}, repeat=4, registers={AX: {RegisterSetting.MAXIMUM: maximum}})
        self.assertEqual(pitches(data), scale_notes([add, maximum, maximum, maximum]))

    def test_it_stops_at_the_minimum(self):
        add = -1
        minimum = -1
        data = one_clip(rows={ADDS: [add], USES_NOTE: [ADDS_IT]}, repeat=3, registers={AX: {RegisterSetting.MINIMUM: minimum}})
        self.assertEqual(pitches(data), scale_notes([minimum] * 3))

    def test_wrapping_jumps_to_the_other_end_and_drops_what_is_left(self):
        # Two adds go past the maximum, and land on the minimum rather than past it.
        add = 2
        maximum = 3
        registers = {AX: {RegisterSetting.MAXIMUM: maximum, RegisterSetting.AT_LIMIT: AtLimit.OVERFLOW}}
        data = one_clip(rows={ADDS: [add], USES_NOTE: [ADDS_IT]}, repeat=4, registers=registers)
        lowest = DEFAULT_REGISTER_MINIMUM
        self.assertEqual(pitches(data), scale_notes([add, lowest, add, lowest]))

    def test_wrapping_below_the_minimum_jumps_to_the_maximum(self):
        add = -1
        minimum = -1
        maximum = 1
        registers = {AX: {RegisterSetting.MINIMUM: minimum, RegisterSetting.MAXIMUM: maximum, RegisterSetting.AT_LIMIT: AtLimit.OVERFLOW}}
        data = one_clip(rows={ADDS: [add], USES_NOTE: [ADDS_IT]}, repeat=3, registers=registers)
        self.assertEqual(pitches(data), scale_notes([minimum, maximum, maximum + add]))


class TestVelocity(unittest.TestCase):

    LOWEST = {AX: {RegisterSetting.MINIMUM: MIN_REGISTER_VALUE}}

    def test_the_value_is_added_to_the_velocity(self):
        add = -20
        data = one_clip(rows={Row.VELOCITY: [VELOCITY], ADDS: [add], USES_VELOCITY: [ADDS_IT]}, repeat=3, registers=self.LOWEST)
        self.assertEqual(velocities(data), [VELOCITY + add, VELOCITY + 2 * add, VELOCITY + 3 * add])

    def test_the_velocity_stays_in_the_midi_range(self):
        rows = {Row.VELOCITY: [MIN_VELOCITY + 1], ADDS: [-2], USES_VELOCITY: [ADDS_IT]}
        self.assertEqual(velocities(one_clip(rows=rows, registers=self.LOWEST)), [MIN_VELOCITY])

    def test_a_step_that_subtracts_takes_the_value_off_the_velocity(self):
        # The add stays within the register's default maximum.
        add = DEFAULT_REGISTER_MAXIMUM // 2
        rows = {Row.VELOCITY: [VELOCITY, VELOCITY, VELOCITY], ADDS: [add, 0, 0], USES_VELOCITY: [SUBTRACTS_IT, ADDS_IT, OFF]}
        self.assertEqual(velocities(one_clip(rows=rows, steps=3)), [VELOCITY - add, VELOCITY + add, VELOCITY])

    def test_a_drum_pattern_can_use_registers_for_velocity(self):
        add = -10
        data = one_clip(rows={ADDS: [add], USES_VELOCITY: [ADDS_IT]}, repeat=2, drum=True, registers=self.LOWEST)
        self.assertEqual(velocities(data), [MAX_VELOCITY + add, MAX_VELOCITY + 2 * add])

    def test_a_drum_pattern_cannot_move_notes_with_registers(self):
        with self.assertRaises(SongFileError):
            song_from_data(one_clip(rows={USES_NOTE: [ADDS_IT]}, drum=True))
        song_from_data(one_clip(rows={USES_NOTE: [OFF]}, drum=True))


class TestSharing(unittest.TestCase):

    STEPS = 3
    ADD = 1
    ONE_STEP = {'x': pattern(1, **{ADDS: [ADD], USES_NOTE: [ADDS_IT]})}

    def counted(self, tracks):
        """Return a song where a silent counter adds to AX on each step and the lead plays it."""
        patterns = {
            COUNT: {PatternSetting.STEPS: self.STEPS, PatternSetting.STEP_SIZE: STEP_SIZE, ADDS: every_step(value=self.ADD, steps=self.STEPS)},
            TUNE: pattern(self.STEPS, **{USES_NOTE: every_step(value=ADDS_IT, steps=self.STEPS)}),
        }
        clip_slots = {COUNTER: {ClipSlotSetting.PATTERN: COUNT}, LEAD: {ClipSlotSetting.PATTERN: TUNE}}
        return song(patterns=patterns, scenes=[{SceneSetting.TRACKS: clip_slots}], tracks=tracks)

    def scene(self, **settings):
        return {SceneSetting.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: X}}, **settings}

    def test_one_track_can_drive_another(self):
        expected = [self.ADD * count for count in range(1, self.STEPS + 1)]
        self.assertEqual(pitches(self.counted((COUNTER, LEAD))), scale_notes(expected))

    def test_at_the_same_moment_tracks_go_in_track_order(self):
        # The lead comes first, so it only hears each count on its next step.
        expected = [self.ADD * count for count in range(self.STEPS)]
        self.assertEqual(pitches(self.counted((LEAD, COUNTER))), scale_notes(expected))

    def test_values_carry_into_the_next_scene_unless_it_resets(self):
        data = song(patterns=self.ONE_STEP, scenes=[self.scene(), self.scene(), self.scene(**{SceneSetting.RESET: [AX]})])
        found = [pitches(data, scene=number) for number in (1, 2, 3)]
        self.assertEqual(found, [scale_notes([self.ADD]), scale_notes([2 * self.ADD]), scale_notes([self.ADD])])

    def test_a_repeating_scene_resets_only_as_it_first_starts(self):
        repeat = 3
        data = song(patterns=self.ONE_STEP, scenes=[self.scene(repeat=repeat, **{SceneSetting.RESET: [AX]})])
        found = [pitches(data, scene=number) for number in range(1, repeat + 1)]
        self.assertEqual(found, [scale_notes([self.ADD * count]) for count in range(1, repeat + 1)])

    def test_a_reset_only_resets_the_registers_it_names(self):
        patterns = {
            X: pattern(1, **{ADDS: [self.ADD], REGISTER_ADD_ROWS[BX]: [self.ADD]}),
            Y: pattern(1, **{REGISTER_NOTE_ROWS[BX]: [ADDS_IT]}),
        }
        scenes = [self.scene(), {SceneSetting.RESET: [AX], SceneSetting.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: Y}}}]
        self.assertEqual(pitches(song(patterns=patterns, scenes=scenes), scene=2), scale_notes([self.ADD]))

    def test_a_morph_target_uses_the_registers_but_does_not_add(self):
        target_add = 5
        patterns = {**self.ONE_STEP, Y: pattern(1, **{ADDS: [target_add], USES_NOTE: [ADDS_IT]})}
        clip_slots = {LEAD: {ClipSlotSetting.PATTERN: X, ClipSlotSetting.REPEAT: 2, ClipSlotSetting.MORPH_TO: Y, ClipSlotSetting.MORPH_STYLE: morph_style_name(BlendMode.LEFT)}}
        # The second repeat is all target, which sees the first pattern's two adds and none of its own.
        self.assertEqual(pitches(song(patterns=patterns, scenes=[{SceneSetting.TRACKS: clip_slots}])), scale_notes([self.ADD, 2 * self.ADD]))


class TestTheFile(unittest.TestCase):

    def test_settings_and_resets_save_and_load(self):
        registers = {AX: {RegisterSetting.MAXIMUM: 3, RegisterSetting.AT_LIMIT: AtLimit.OVERFLOW}, DX: {RegisterSetting.MINIMUM: -100}}
        data = one_clip(rows={ADDS: [1], USES_NOTE: [ADDS_IT]}, registers=registers)
        data[Section.SCENES][0][SceneSetting.RESET] = [AX, DX]
        saved = song_from_data(data).to_data()
        self.assertEqual(saved[Section.REGISTERS], registers)
        self.assertEqual(saved[Section.SCENES][0][SceneSetting.RESET], [AX, DX])

    def test_registers_the_file_leaves_out_have_their_defaults(self):
        register = song_from_data({}).get_register(CX)
        self.assertEqual(
            (register.get_default(), register.get_minimum(), register.get_maximum(), register.get_at_limit(), register.resets_each_scene()),
            (DEFAULT_REGISTER_VALUE, DEFAULT_REGISTER_MINIMUM, DEFAULT_REGISTER_MAXIMUM, AtLimit.STOP, False),
        )

    def test_bad_settings_are_refused(self):
        for registers in [
            {EX: {}}, {AX: {RegisterSetting.MAXIMUM: MAX_REGISTER_VALUE + 1}},
            {AX: {RegisterSetting.MINIMUM: DEFAULT_REGISTER_VALUE + 1}},
            {AX: {RegisterSetting.DEFAULT: DEFAULT_REGISTER_MAXIMUM + 1}},
            {AX: {RegisterSetting.WRAP: YES}}, {AX: {RegisterSetting.AT_LIMIT: YES}}, {AX: {RegisterSetting.RESET_EACH_SCENE: YES}}, {AX: {LOUD: 1}}, {AX: {RegisterSetting.MAXIMUM: 1.5}}, [AX],
        ]:
            with self.subTest(registers=registers), self.assertRaises(SongFileError):
                song_from_data(one_clip(rows={}, registers=registers))

    def test_bad_resets_are_refused(self):
        for reset in [[EX], AX, [AX, AX]]:
            data = one_clip(rows={})
            data[Section.SCENES][0][SceneSetting.RESET] = reset
            with self.subTest(reset=reset), self.assertRaises(SongFileError):
                song_from_data(data)

    def test_bad_rows_are_refused(self):
        for rows in [
            {ADDS: [MAX_REGISTER_VALUE + 1]}, {ADDS: [MIN_REGISTER_VALUE - 1]}, {REGISTER_ADD_ROWS[BX]: [X]},
            {REGISTER_NOTE_ROWS[CX]: [2]}, {REGISTER_VELOCITY_ROWS[DX]: [-2]}, {REGISTER_VELOCITY_ROWS[DX]: [X]},
        ]:
            with self.subTest(rows=rows), self.assertRaises(SongFileError):
                song_from_data(one_clip(rows=rows))


if __name__ == '__main__':
    unittest.main()
