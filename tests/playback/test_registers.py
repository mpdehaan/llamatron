# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The registers AX to DX: what steps add to them, how they hold, roll round or turn round at their ends, and the notes and velocities that use them.

Most tests say what they expect as the register values each note should see, like [ADD,
MAXIMUM, MAXIMUM], and scale_notes turns those into the notes of C major they move C3 to.
"""

import unittest

from llamatron.exporters.timing import timed_events
from llamatron.generators.blend import BlendMode
from llamatron.model.file.song_file_error import SongFileError
from llamatron.model.objects.clip_slot import morph_style_name
from llamatron.model.objects.named_scale import scale_type_name
from llamatron.model.schema import defaults, file_format, limits
from llamatron.model.schema.file_format import ClipSlotSetting, PatternSetting, RegisterName, RegisterSetting, RegisterUse, ResetBehavior, Row, ScaleSetting, SceneSetting, Section, SongSetting
from llamatron.model.values import midi
from llamatron.model.values.note import NoteName
from llamatron.model.values.scale import ScaleType
from llamatron.user_strings import errors
from tests.support.rendering import render_data, setlist_from_data, song_from_data

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


def scale_notes(values):
    """Return the MIDI notes that register values move C3 to, along C major, one for each value."""
    return [scale_note(value) for value in values]


def scale_note(value):
    octaves, place = divmod(value, len(C_MAJOR_STEPS))
    return ROOT + octaves * midi.HALF_STEPS_PER_OCTAVE + C_MAJOR_STEPS[place]


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
ADDS = file_format.REGISTER_ADD_ROWS[AX]
USES_NOTE = file_format.REGISTER_NOTE_ROWS[AX]
USES_VELOCITY = file_format.REGISTER_VELOCITY_ROWS[AX]
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
        rows = {ADDS: [self.ADD], file_format.REGISTER_ADD_ROWS[BX]: [other_add], USES_NOTE: [ADDS_IT], file_format.REGISTER_NOTE_ROWS[BX]: [OFF]}
        self.assertEqual(pitches(one_clip(rows=rows)), scale_notes([self.ADD]))
        rows[file_format.REGISTER_NOTE_ROWS[BX]] = [ADDS_IT]
        self.assertEqual(pitches(one_clip(rows=rows)), scale_notes([self.ADD + other_add]))

    def test_it_starts_at_its_default(self):
        default = 2
        data = one_clip(rows={USES_NOTE: [ADDS_IT]}, registers={AX: {RegisterSetting.DEFAULT: default}})
        self.assertEqual(pitches(data), scale_notes([default]))

    def test_a_step_that_subtracts_moves_down_by_the_registers_value(self):
        # - on a +Note row subtracts the register, where the row was a toggle that could only add.
        data = one_clip(rows={ADDS: [self.ADD, 0, 0], USES_NOTE: [SUBTRACTS_IT, ADDS_IT, OFF]}, steps=3)
        self.assertEqual(pitches(data), scale_notes([-self.ADD, self.ADD, 0]))

    def test_adding_one_register_and_subtracting_another_nets_the_difference(self):
        other_add = 3
        rows = {ADDS: [self.ADD], file_format.REGISTER_ADD_ROWS[BX]: [other_add], USES_NOTE: [ADDS_IT], file_format.REGISTER_NOTE_ROWS[BX]: [SUBTRACTS_IT]}
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
        registers = {name: {RegisterSetting.MAXIMUM: limits.MAX_REGISTER_VALUE, RegisterSetting.ALLOWED_INC_MAX: limits.MAX_REGISTER_VALUE} for name in file_format.REGISTER_NAMES}
        rows = {Row.OCTAVE: [10]}
        for name in file_format.REGISTER_NAMES:
            rows.update({file_format.REGISTER_ADD_ROWS[name]: [limits.MAX_REGISTER_VALUE], file_format.REGISTER_NOTE_ROWS[name]: [ADDS_IT]})
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

    def test_overflow_rolls_round_to_the_other_end_keeping_what_is_left(self):
        # AX runs 0 to 4 and each pass adds 3: 3, 6 which is 1, 4, 7 which is 2, 5 which is 0.
        add = 3
        maximum = 4
        registers = {AX: {RegisterSetting.MAXIMUM: maximum, RegisterSetting.RESET_BEHAVIOR: ResetBehavior.OVERFLOW}}
        data = one_clip(rows={ADDS: [add], USES_NOTE: [ADDS_IT]}, repeat=5, registers=registers)
        self.assertEqual(pitches(data), scale_notes([3, 1, 4, 2, 0]))

    def test_overflow_below_the_minimum_rolls_round_to_the_maximum(self):
        add = -1
        minimum = -1
        maximum = 1
        registers = {AX: {RegisterSetting.MINIMUM: minimum, RegisterSetting.MAXIMUM: maximum, RegisterSetting.RESET_BEHAVIOR: ResetBehavior.OVERFLOW}}
        data = one_clip(rows={ADDS: [add], USES_NOTE: [ADDS_IT]}, repeat=3, registers=registers)
        self.assertEqual(pitches(data), scale_notes([minimum, maximum, maximum + add]))

    def test_reset_clip_goes_to_the_minimum_past_the_maximum(self):
        registers = {AX: {RegisterSetting.MAXIMUM: 3, RegisterSetting.RESET_BEHAVIOR: ResetBehavior.RESET_CLIP}}
        data = one_clip(rows={ADDS: [2], USES_NOTE: [ADDS_IT]}, repeat=4, registers=registers)
        self.assertEqual(pitches(data), scale_notes([2, 0, 2, 0]))

    def test_reverse_walks_up_and_back_down(self):
        registers = {AX: {RegisterSetting.MAXIMUM: 3, RegisterSetting.RESET_BEHAVIOR: ResetBehavior.REVERSE}}
        data = one_clip(rows={ADDS: [1], USES_NOTE: [ADDS_IT]}, repeat=8, registers=registers)
        self.assertEqual(pitches(data), scale_notes([1, 2, 3, 2, 1, 0, 1, 2]))

    def test_a_set_puts_a_reversed_register_back_to_counting_forward(self):
        # Four steps: the fourth sets AX to 1 once it has turned round at 2, and the adds after it count up again.
        registers = {AX: {RegisterSetting.MAXIMUM: 2, RegisterSetting.RESET_BEHAVIOR: ResetBehavior.REVERSE}}
        rows = {ADDS: [1, 1, 1, 0, 1, 1], file_format.REGISTER_SET_ROWS[AX]: [None, None, None, 1, None, None], USES_NOTE: [ADDS_IT] * 6}
        data = one_clip(steps=6, rows=rows, registers=registers)
        self.assertEqual(pitches(data), scale_notes([1, 2, 1, 1, 2, 1]))

    def test_a_reversed_register_keeps_counting_the_other_way_into_the_next_scene_unless_the_scene_resets_it(self):
        registers = {AX: {RegisterSetting.MAXIMUM: 2, RegisterSetting.RESET_BEHAVIOR: ResetBehavior.REVERSE}}
        slot = {ClipSlotSetting.PATTERN: X, ClipSlotSetting.REPEAT: 3}
        for resets, heard in (([], [0, 1, 2]), ([AX], [1, 2, 1])):
            with self.subTest(resets=resets):
                scenes = [{SceneSetting.TRACKS: {LEAD: slot}}, {SceneSetting.TRACKS: {LEAD: slot}, SceneSetting.RESET: resets}]
                data = song(patterns={X: pattern(1, **{ADDS: [1], USES_NOTE: [ADDS_IT]})}, scenes=scenes, registers=registers)
                self.assertEqual(pitches(data), scale_notes([1, 2, 1]))
                self.assertEqual(pitches(data, scene=2), scale_notes(heard))


class TestVelocity(unittest.TestCase):

    LOWEST = {AX: {RegisterSetting.MINIMUM: limits.MIN_REGISTER_VALUE}}

    def test_the_value_is_added_to_the_velocity(self):
        add = -20
        data = one_clip(rows={Row.VELOCITY: [VELOCITY], ADDS: [add], USES_VELOCITY: [ADDS_IT]}, repeat=3, registers=self.LOWEST)
        self.assertEqual(velocities(data), [VELOCITY + add, VELOCITY + 2 * add, VELOCITY + 3 * add])

    def test_the_velocity_stays_in_the_midi_range(self):
        rows = {Row.VELOCITY: [midi.MIN_VELOCITY + 1], ADDS: [-2], USES_VELOCITY: [ADDS_IT]}
        self.assertEqual(velocities(one_clip(rows=rows, registers=self.LOWEST)), [midi.MIN_VELOCITY])

    def test_a_step_that_subtracts_takes_the_value_off_the_velocity(self):
        # The add stays within the register's default maximum.
        add = defaults.DEFAULT_REGISTER_MAXIMUM // 2
        rows = {Row.VELOCITY: [VELOCITY, VELOCITY, VELOCITY], ADDS: [add, 0, 0], USES_VELOCITY: [SUBTRACTS_IT, ADDS_IT, OFF]}
        self.assertEqual(velocities(one_clip(rows=rows, steps=3)), [VELOCITY - add, VELOCITY + add, VELOCITY])

    def test_a_drum_pattern_can_use_registers_for_velocity(self):
        add = -10
        data = one_clip(rows={ADDS: [add], USES_VELOCITY: [ADDS_IT]}, repeat=2, drum=True, registers=self.LOWEST)
        self.assertEqual(velocities(data), [midi.MAX_VELOCITY + add, midi.MAX_VELOCITY + 2 * add])

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
            X: pattern(1, **{ADDS: [self.ADD], file_format.REGISTER_ADD_ROWS[BX]: [self.ADD]}),
            Y: pattern(1, **{file_format.REGISTER_NOTE_ROWS[BX]: [ADDS_IT]}),
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
        registers = {AX: {RegisterSetting.MAXIMUM: 3, RegisterSetting.RESET_BEHAVIOR: ResetBehavior.OVERFLOW}, DX: {RegisterSetting.MINIMUM: -100}}
        data = one_clip(rows={ADDS: [1], USES_NOTE: [ADDS_IT]}, registers=registers)
        data[Section.SCENES][0][SceneSetting.RESET] = [AX, DX]
        saved = song_from_data(data).to_data()
        self.assertEqual(saved[Section.REGISTERS], registers)
        self.assertEqual(saved[Section.SCENES][0][SceneSetting.RESET], [AX, DX])

    def test_registers_the_file_leaves_out_have_their_defaults(self):
        register = song_from_data({}).get_register(CX)
        self.assertEqual(
            (register.get_default(), register.get_minimum(), register.get_maximum(), register.get_reset_behavior(), register.resets_each_scene()),
            (defaults.DEFAULT_REGISTER_VALUE, defaults.DEFAULT_REGISTER_MINIMUM, defaults.DEFAULT_REGISTER_MAXIMUM, ResetBehavior.CLIP, False),
        )

    def test_bad_settings_are_refused(self):
        for registers in [
            {EX: {}}, {AX: {RegisterSetting.MAXIMUM: limits.MAX_REGISTER_VALUE + 1}},
            {AX: {RegisterSetting.MINIMUM: defaults.DEFAULT_REGISTER_VALUE + 1}},
            {AX: {RegisterSetting.DEFAULT: defaults.DEFAULT_REGISTER_MAXIMUM + 1}},
            {AX: {RegisterSetting.RESET_BEHAVIOR: YES}}, {AX: {RegisterSetting.RESET_EACH_SCENE: YES}}, {AX: {RegisterSetting.MAXIMUM: 1.5}}, [AX],
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
            {ADDS: [limits.MAX_REGISTER_VALUE + 1]}, {ADDS: [limits.MIN_REGISTER_VALUE - 1]}, {file_format.REGISTER_ADD_ROWS[BX]: [X]},
            {file_format.REGISTER_NOTE_ROWS[CX]: [2]}, {file_format.REGISTER_VELOCITY_ROWS[DX]: [-2]}, {file_format.REGISTER_VELOCITY_ROWS[DX]: [X]},
        ]:
            with self.subTest(rows=rows), self.assertRaises(SongFileError):
                song_from_data(one_clip(rows=rows))


if __name__ == '__main__':
    unittest.main()


# A song's narrower limit on what a step may add to a register, and adds within and past it.
NARROW_LIMIT = 3
PAST_NARROW = NARROW_LIMIT + 1
STEPS_ADDING = 2
UNPLAYED = 'unplayed'


def adding(*, adds, registers=None):
    """Return a song whose lead plays a pattern that adds to AX on each step, with a second pattern no clip plays that adds the same."""
    rows = {Row.AX_ADD: adds}
    patterns = {X: pattern(STEPS_ADDING, **rows), UNPLAYED: pattern(STEPS_ADDING, **rows)}
    return song(patterns=patterns, scenes=[{SceneSetting.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: X}}}], registers=registers)


class TestWhatAStepMayAdd(unittest.TestCase):
    """The limit is looked up only for a pattern that adds anything, so both kinds of pattern are held here."""

    def narrow(self):
        return {AX: {RegisterSetting.ALLOWED_INC_MAX: NARROW_LIMIT}}

    def test_a_pattern_that_adds_nothing_is_read_whatever_the_limit(self):
        setlist = setlist_from_data(adding(adds=[None, 0], registers=self.narrow()))
        self.assertFalse(setlist.get_pattern(X).adds_anything(Row.AX_ADD))
        self.assertFalse(setlist_from_data(song(patterns={X: pattern(1)}, scenes=[])).get_pattern(X).adds_anything(Row.AX_ADD))

    def test_a_file_that_adds_within_the_limit_is_read_and_one_past_it_is_refused(self):
        setlist = setlist_from_data(adding(adds=[NARROW_LIMIT, -NARROW_LIMIT], registers=self.narrow()))
        self.assertTrue(setlist.get_pattern(X).adds_anything(Row.AX_ADD))
        with self.assertRaises(SongFileError) as refused:
            setlist_from_data(adding(adds=[None, PAST_NARROW], registers=self.narrow()))
        self.assertIn(errors.ERR_ADD_PAST_ALLOWED.format(row=Row.AX_ADD, register=AX, most=NARROW_LIMIT), str(refused.exception))
        with self.assertRaises(SongFileError):
            setlist_from_data(adding(adds=[defaults.DEFAULT_ALLOWED_INC_MAX + 1, None]))

    def test_holding_adds_within_the_limit_lowers_those_past_it_in_patterns_a_song_plays(self):
        setlist = setlist_from_data(adding(adds=[PAST_NARROW, -1]))
        setlist.get_song(setlist.first_song_name()).set_register_setting(name=AX, setting=RegisterSetting.ALLOWED_INC_MAX, value=NARROW_LIMIT)
        setlist.hold_adds_within_limits()
        self.assertEqual(setlist.get_pattern(X).to_data()[Row.AX_ADD], [NARROW_LIMIT, -1])
        # No song plays the other pattern, so no limit holds it.
        self.assertEqual(setlist.get_pattern(UNPLAYED).to_data()[Row.AX_ADD], [PAST_NARROW, -1])
