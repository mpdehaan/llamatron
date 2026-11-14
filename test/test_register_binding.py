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
"""Register binding, the = rows and the conditions: what a step sets a register to, when a note is silenced, and what a bound CC lane and a bound velocity send.

The user's design of 2026-11-11. A step's sets come before its adds, a set is held to the
register's range, a condition never stops a change, the conditions on a step must all hold, a
bound velocity stands in for a blank Velocity, and a bound CC lane sends its register's value at
the clip's start and whenever it changes, with the clip's own value winning at the same moment.
"""

import unittest

from llamatron.composition.file_format import (
    CONDITION_ROWS, REGISTER_ADD_ROWS, AtLimit, REGISTER_NOTE_ROWS, REGISTER_SET_ROWS, REGISTER_VELOCITY_ROWS, ClipSlotSetting, Comparison,
    REGISTER_NAMES, GeneratorKind, RegisterSetting, Row, SceneSetting, Section, TrackSetting,
)
from llamatron.composition.limits import MAX_REGISTER_VALUE, MIN_REGISTER_VALUE
from llamatron.composition.defaults import DEFAULT_ALLOWED_INC_MAX, DEFAULT_VELOCITY
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.limits import MIN_ALLOWED_INC_MAX
from llamatron.composition.register import Register
from llamatron.composition.song_file_error import SongFileError
from llamatron.composition.track import Track
from test_registers import EX
from llamatron.music.midi import MIN_CC_VALUE, MIN_VELOCITY
from llamatron.support.rational import Rational
from llamatron.composition.setlist import Setlist
from llamatron.composition.generator_settings import ARP_NOTE_ADDS, ARP_STEP_ADDS, ArpSetting, ArpSettings
from llamatron.generators.arp import REGISTERS as ARP_REGISTERS
from rendering import as_setlist, render_data
from test_registers import AX, BX, CX, LEAD, X, every_step, one_clip, pattern, pitches, scale_notes, song, velocities

# The other track the tests use, which changes the registers the lead or the pad reads.
DRIVER = 'driver'
PAD = 'pad'
Y = 'y'
# A step is a quarter note in every pattern here (test_registers.STEP_SIZE).
QUARTER = Rational(1, 4)
# Values the tests set and add.
SET_TO = 5
ADDED = 1
TOO_HIGH = 15
STEPS = 4
DRIVER_ADDS = 4
BRIGHTNESS = 74
OWN_VALUE = 100
RATCHET = 4
LOW = 2
HIGH = 4
VELOCITY_HELD = 50
OWN_VELOCITY = 90
BELOW_THE_FLOOR = -20
BELOW_ZERO = -5
# An arp of sixteenths over a quarter-note major chord plays four notes.
ARP = 'up'
SIXTEENTH = '1/16'
SIXTEENTH_TIME = Rational(1, 16)
CHORD = 'M'
ARP_NOTES = 4
# What two steps of offsets add, and AX after each of the four steps.
STEP_ADDS = [2, 3]
RUNNING_STEP_ADDS = [2, 5, 7, 10]
WIDE = {RegisterSetting.MINIMUM: MIN_REGISTER_VALUE, RegisterSetting.MAXIMUM: MAX_REGISTER_VALUE}


def registers(**defaults):
    """Return register settings giving each named register a default, across the widest range."""
    return {name: {**WIDE, RegisterSetting.DEFAULT: value} for name, value in defaults.items()}


def two_tracks(*, lead, driver, lead_track=None, registers_=None):
    """Return a song whose driver plays one pattern and whose lead plays another, in one scene, the driver first."""
    data = song(
        patterns={X: lead, Y: driver},
        scenes=[{SceneSetting.TRACKS: {DRIVER: {ClipSlotSetting.PATTERN: Y}, LEAD: {ClipSlotSetting.PATTERN: X}}}],
        registers=registers_, tracks=(DRIVER, LEAD),
    )
    data['tracks'][LEAD] = lead_track or {}
    return data


def controls_of(data, *, track=LEAD):
    """Return (time, CC number, value) for each CC value a track's clip sends in the first scene, in time order."""
    grid = render_data(data)
    column = [column for column in grid.get_columns() if column.get_name() == track][0]
    clip = grid.get_clip(row=grid.get_rows()[0], column=column)
    return [(control.get_time(), control.get_number(), control.get_value()) for control in clip.get_controls()]


class TestSetRows(unittest.TestCase):

    def test_a_set_comes_before_the_add_on_the_same_step(self):
        data = one_clip(rows={REGISTER_SET_ROWS[AX]: [SET_TO], REGISTER_ADD_ROWS[AX]: [ADDED], REGISTER_NOTE_ROWS[AX]: [1]})
        self.assertEqual(pitches(data), scale_notes([SET_TO + ADDED]))

    def test_a_set_alone_changes_the_register_with_no_add_anywhere(self):
        data = one_clip(steps=2, rows={REGISTER_SET_ROWS[AX]: [SET_TO, None], REGISTER_NOTE_ROWS[AX]: [1, 1]})
        self.assertEqual(pitches(data), scale_notes([SET_TO, SET_TO]))

    def test_a_set_of_zero_sets_and_a_blank_leaves_the_register(self):
        data = one_clip(steps=2, rows={REGISTER_SET_ROWS[AX]: [None, 0], REGISTER_NOTE_ROWS[AX]: [1, 1]}, registers=registers(AX=SET_TO))
        self.assertEqual(pitches(data), scale_notes([SET_TO, 0]))

    def test_a_set_past_the_registers_maximum_stops_there_and_never_wraps(self):
        data = one_clip(rows={REGISTER_SET_ROWS[AX]: [TOO_HIGH], REGISTER_NOTE_ROWS[AX]: [1]}, registers={AX: {RegisterSetting.AT_LIMIT: AtLimit.OVERFLOW}})
        self.assertEqual(pitches(data), scale_notes([10]))


class TestConditions(unittest.TestCase):

    def test_a_note_sounds_only_when_every_condition_holds(self):
        cases = [
            ({CONDITION_ROWS[BX]: [Comparison.LESS]}, 1),
            ({CONDITION_ROWS[BX]: [Comparison.MORE]}, 0),
            ({CONDITION_ROWS[BX]: [Comparison.LESS], CONDITION_ROWS[CX]: [Comparison.SAME]}, 1),
            ({CONDITION_ROWS[BX]: [Comparison.LESS], CONDITION_ROWS[CX]: [Comparison.MORE]}, 0),
        ]
        for rows, notes in cases:
            with self.subTest(rows=rows):
                data = one_clip(rows=rows, registers=registers(AX=LOW, BX=HIGH, CX=LOW))
                self.assertEqual(len(pitches(data)), notes)

    def test_a_silenced_note_still_sets_and_adds(self):
        rows = {CONDITION_ROWS[BX]: [Comparison.MORE, None], REGISTER_ADD_ROWS[AX]: [ADDED, None], REGISTER_NOTE_ROWS[AX]: [0, 1]}
        data = one_clip(steps=2, rows=rows, registers=registers(AX=LOW, BX=HIGH))
        self.assertEqual(pitches(data), scale_notes([LOW + ADDED]))

    def test_a_ratchet_sounds_every_slice_or_none(self):
        for comparison, notes in ((Comparison.LESS, RATCHET), (Comparison.MORE, 0)):
            with self.subTest(comparison=comparison):
                data = one_clip(rows={CONDITION_ROWS[BX]: [comparison], Row.RATCHET: [RATCHET]}, registers=registers(AX=LOW, BX=HIGH))
                self.assertEqual(len(pitches(data)), notes)

    def test_a_condition_reads_what_a_track_to_the_left_changed_at_the_same_moment(self):
        lead = pattern(1, **{CONDITION_ROWS[BX]: [Comparison.SAME]})
        driver = pattern(1, **{REGISTER_ADD_ROWS[AX]: [HIGH - LOW]})
        self.assertEqual(len(pitches(two_tracks(lead=lead, driver=driver, registers_=registers(AX=LOW, BX=HIGH)))), 1)


class TestBoundVelocity(unittest.TestCase):

    def test_a_blank_velocity_plays_at_the_bound_register_and_a_steps_own_velocity_wins(self):
        rows = {Row.VELOCITY: [None, OWN_VELOCITY]}
        data = one_clip(steps=2, rows=rows, registers=registers(BX=VELOCITY_HELD))
        data['tracks'][LEAD] = {TrackSetting.VELOCITY_REGISTER: BX}
        self.assertEqual(velocities(data), [VELOCITY_HELD, OWN_VELOCITY])

    def test_vel_adds_to_the_bound_velocity(self):
        data = one_clip(rows={REGISTER_VELOCITY_ROWS[AX]: [1]}, registers=registers(AX=ADDED, BX=VELOCITY_HELD))
        data['tracks'][LEAD] = {TrackSetting.VELOCITY_REGISTER: BX}
        self.assertEqual(velocities(data), [VELOCITY_HELD + ADDED])

    def test_a_bound_velocity_below_one_plays_at_the_lowest_velocity_rather_than_silencing(self):
        data = one_clip(rows={}, registers=registers(BX=BELOW_THE_FLOOR))
        data['tracks'][LEAD] = {TrackSetting.VELOCITY_REGISTER: BX}
        self.assertEqual(velocities(data), [MIN_VELOCITY])

    def test_an_unbound_track_plays_at_the_default(self):
        self.assertEqual(velocities(one_clip(rows={}, registers=registers(BX=VELOCITY_HELD))), [DEFAULT_VELOCITY])


class TestBoundControls(unittest.TestCase):

    BOUND = {TrackSetting.CC: [BRIGHTNESS, None, None, None], TrackSetting.CC1_REGISTER: AX}

    def driven(self, *, lead_rows=None, driver_add=DRIVER_ADDS, registers_=None):
        lead = pattern(STEPS, **(lead_rows or {}))
        driver = pattern(STEPS, **{REGISTER_ADD_ROWS[AX]: every_step(value=driver_add, steps=STEPS)})
        return two_tracks(lead=lead, driver=driver, lead_track=dict(self.BOUND), registers_=registers_ or registers(AX=0))

    def test_a_bound_lane_sends_the_register_at_the_start_and_at_every_change(self):
        expected = [(QUARTER * step, BRIGHTNESS, DRIVER_ADDS * (step + 1)) for step in range(STEPS)]
        self.assertEqual(controls_of(self.driven()), expected)

    def test_the_clips_own_value_wins_at_the_same_moment(self):
        sent = controls_of(self.driven(lead_rows={Row.CC1: [None, OWN_VALUE, None, None]}))
        self.assertEqual(sent[1], (QUARTER, BRIGHTNESS, OWN_VALUE))
        self.assertEqual(len(sent), STEPS)

    def test_a_change_that_sends_the_same_value_sends_nothing(self):
        # AX stops at its maximum without wrap, so after it gets there nothing changes what the lane would send.
        data = self.driven(registers_={AX: {RegisterSetting.MAXIMUM: DRIVER_ADDS * 2}})
        self.assertEqual([value for _, _, value in controls_of(data)], [DRIVER_ADDS, DRIVER_ADDS * 2])

    def test_a_register_below_zero_sends_the_lowest_cc_value(self):
        data = self.driven(driver_add=0, registers_=registers(AX=BELOW_ZERO))
        self.assertEqual(controls_of(data), [(Rational(0), BRIGHTNESS, MIN_CC_VALUE)])

    def test_a_bound_lane_with_no_cc_number_sends_nothing(self):
        data = self.driven()
        data['tracks'][LEAD] = {TrackSetting.CC1_REGISTER: AX}
        self.assertEqual(controls_of(data), [])

    def test_a_track_with_nothing_in_the_scene_sends_nothing(self):
        data = self.driven()
        del data['scenes'][0][SceneSetting.TRACKS][LEAD]
        grid = render_data(data)
        column = [column for column in grid.get_columns() if column.get_name() == LEAD][0]
        self.assertIsNone(grid.get_clip(row=grid.get_rows()[0], column=column))

    def test_an_unbound_lane_sends_nothing(self):
        data = self.driven()
        data['tracks'][LEAD] = {TrackSetting.CC: [BRIGHTNESS, None, None, None]}
        self.assertEqual(controls_of(data), [])

    def test_a_reset_scene_sends_the_default_again(self):
        data = self.driven()
        data['scenes'].append({SceneSetting.RESET: [AX, CX], SceneSetting.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: X}}})
        grid = render_data(data)
        column = [column for column in grid.get_columns() if column.get_name() == LEAD][0]
        second = grid.get_clip(row=grid.get_rows()[1], column=column)
        self.assertEqual([control.get_value() for control in second.get_controls()], [0])


class TestTheSettings(unittest.TestCase):
    """The track's bindings and the register's Allowed Inc Max, as a file holds them and as their setters change them."""

    def test_a_track_binds_each_lane_and_its_velocity_and_writes_only_what_is_bound(self):
        track = Track()
        self.assertFalse(track.binds_registers())
        track.set_cc_register(lane=2, register=CX)
        track.set_velocity_register(BX)
        self.assertEqual(track.get_cc_registers(), [None, None, CX, None])
        self.assertEqual(track.get_velocity_register(), BX)
        self.assertEqual(track.to_data(), {TrackSetting.CC3_REGISTER: CX, TrackSetting.VELOCITY_REGISTER: BX})
        self.assertEqual(track.copy().to_data(), track.to_data())
        track.set_cc_register(lane=2, register=None)
        track.set_velocity_register(None)
        self.assertEqual(track.to_data(), {})

    def test_a_track_refuses_a_register_that_doesnt_exist_from_a_file_and_from_its_setters(self):
        with self.assertRaises(SongFileError):
            Track.from_data(data={TrackSetting.CC1_REGISTER: EX}, where=LEAD)
        with self.assertRaises(InvalidValue):
            Track().set_cc_register(lane=0, register=EX)
        with self.assertRaises(InvalidValue):
            Track().set_velocity_register(EX)

    def test_a_file_whose_adds_pass_the_limit_is_refused_and_opens_corrected_within_it(self):
        past = DEFAULT_ALLOWED_INC_MAX + ADDED
        data = as_setlist(one_clip(steps=2, rows={REGISTER_ADD_ROWS[AX]: [past, -past]}))
        with self.assertRaises(SongFileError):
            Setlist.from_data(data=data)
        setlist, corrections = Setlist.from_data_corrected(data=data)
        self.assertEqual(len(corrections), 1)
        pattern = setlist.get_pattern(X)
        self.assertEqual([pattern.get_value(row=REGISTER_ADD_ROWS[AX], step=step) for step in (0, 1)], [DEFAULT_ALLOWED_INC_MAX, -DEFAULT_ALLOWED_INC_MAX])

    def test_a_registers_allowed_inc_max_defaults_to_enough_for_every_example_and_has_its_limits(self):
        self.assertEqual(Register().get_allowed_inc_max(), DEFAULT_ALLOWED_INC_MAX)
        register = Register()
        register.set_setting(name=RegisterSetting.ALLOWED_INC_MAX, value=MIN_ALLOWED_INC_MAX)
        self.assertEqual(register.get_allowed_inc_max(), MIN_ALLOWED_INC_MAX)
        for wrong in (MIN_ALLOWED_INC_MAX - 1, MAX_REGISTER_VALUE + 1):
            with self.subTest(value=wrong), self.assertRaises(InvalidValue):
                register.set_setting(name=RegisterSetting.ALLOWED_INC_MAX, value=wrong)



class TestArpAdds(unittest.TestCase):
    """An arpeggiator adds to the registers on every note it plays and on each step of its offsets, silent ones too, and its adds count whether or not the notes are heard."""

    def driven_by_an_arp(self, *, arp, driver_rows=None):
        """Return a song whose driver plays a quarter-note chord through an arp, and whose lead's CC 1 lane is bound to AX, the lead's clip a quarter note long."""
        driver = pattern(1, **{Row.CHORD: [CHORD], **(driver_rows or {})})
        data = two_tracks(lead=pattern(1), driver=driver, lead_track=dict(TestBoundControls.BOUND), registers_=registers(AX=0))
        data[Section.ARPS] = {ARP: {ArpSetting.STEP: SIXTEENTH, **arp}}
        data[Section.CHAINS] = {ARP: [{GeneratorKind.ARP: ARP}]}
        data[Section.SCENES][0][SceneSetting.TRACKS][DRIVER][ClipSlotSetting.CHAIN] = ARP
        return data

    def sent(self, data):
        return [(time, value) for time, _, value in controls_of(data)]

    def test_every_note_the_arp_plays_adds(self):
        data = self.driven_by_an_arp(arp={ARP_NOTE_ADDS[AX]: ADDED})
        self.assertEqual(self.sent(data), [(SIXTEENTH_TIME * place, ADDED * (place + 1)) for place in range(ARP_NOTES)])

    def test_each_step_of_the_offsets_adds_silent_ones_too(self):
        data = self.driven_by_an_arp(arp={ArpSetting.OFFSETS: [0, None], ARP_STEP_ADDS[AX]: STEP_ADDS})
        self.assertEqual([value for _, value in self.sent(data)], RUNNING_STEP_ADDS)

    def test_an_arps_adds_count_even_when_probability_silences_its_notes(self):
        data = self.driven_by_an_arp(arp={ARP_NOTE_ADDS[AX]: ADDED}, driver_rows={Row.PROBABILITY: [0]})
        self.assertEqual([value for _, value in self.sent(data)], [ADDED * (place + 1) for place in range(ARP_NOTES)])

    def test_an_arp_with_adds_counts_among_what_changes_the_registers(self):
        data = as_setlist(self.driven_by_an_arp(arp={ARP_NOTE_ADDS[AX]: ADDED}))
        self.assertTrue(Setlist.from_data(data=data).changes_registers())
        self.assertFalse(Setlist.from_data(data=as_setlist(self.driven_by_an_arp(arp={}))).changes_registers())

    def test_the_arp_names_the_registers_as_the_format_does(self):
        self.assertEqual(list(ARP_REGISTERS), REGISTER_NAMES)

    def test_inserting_and_removing_an_offset_keeps_the_step_adds_lined_up(self):
        settings = ArpSettings({ArpSetting.STEP: SIXTEENTH, ArpSetting.OFFSETS: [0, 0], ARP_STEP_ADDS[AX]: [ADDED, None]})
        settings.insert_offset(0)
        self.assertEqual(settings.get_step_adds(AX), [None, ADDED, None])
        settings.remove_offset(1)
        self.assertEqual(settings.get_step_adds(AX), [None, None])
        self.assertNotIn(ARP_STEP_ADDS[AX], settings.to_data())


if __name__ == '__main__':
    unittest.main()
