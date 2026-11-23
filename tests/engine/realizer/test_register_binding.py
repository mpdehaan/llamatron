# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Register binding and the = rows: what a step sets a register to, and what a bound CC lane and a bound velocity send.

A step's sets come before its adds, a set is held to the
register's range, a
bound velocity stands in for a blank Velocity, and a bound CC lane sends its register's value at
the clip's start and whenever it changes, with the clip's own value winning at the same moment.
"""

import unittest

from llamatron.math.rational import Rational
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.file.song_file_error import SongFileError
from llamatron.model.objects.register import Register
from llamatron.model.objects.setlist import Setlist
from llamatron.model.schema import defaults as set_defaults, file_format, limits
from llamatron.model.schema.file_format import ClipSlotSetting, RegisterSetting, ResetBehavior, SceneSetting
from tests.engine.realizer import test_registers
from tests.engine.realizer.test_registers import one_clip, pitches, scale_notes, song
from tests.support.rendering import as_setlist, render_data

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
ARP_CHAIN = 'up chain'
SIXTEENTH = '1/16'
SIXTEENTH_TIME = Rational(1, 16)
CHORD = 'M'
ARP_NOTES = 4
# What two steps of offsets add, and AX after each of the four steps.
STEP_ADDS = [2, 3]
RUNNING_STEP_ADDS = [2, 5, 7, 10]
WIDE = {RegisterSetting.MINIMUM: limits.MIN_REGISTER_VALUE, RegisterSetting.MAXIMUM: limits.MAX_REGISTER_VALUE}


def registers(**defaults):
    """Return register settings giving each named register a default, across the widest range."""
    return {name: {**WIDE, RegisterSetting.DEFAULT: value} for name, value in defaults.items()}


def two_tracks(*, lead, driver, lead_track=None, registers_=None):
    """Return a song whose driver plays one pattern and whose lead plays another, in one scene, the driver first."""
    data = song(
        patterns={test_registers.X: lead, Y: driver},
        scenes=[{SceneSetting.TRACKS: {DRIVER: {ClipSlotSetting.PATTERN: Y}, test_registers.LEAD: {ClipSlotSetting.PATTERN: test_registers.X}}}],
        registers=registers_, tracks=(DRIVER, test_registers.LEAD),
    )
    data['tracks'][test_registers.LEAD] = lead_track or {}
    return data


def controls_of(data, *, track=test_registers.LEAD):
    """Return (time, CC number, value) for each CC value a track's clip sends in the first scene, in time order."""
    grid = render_data(data)
    column = [column for column in grid.get_columns() if column.get_name() == track][0]
    clip = grid.get_clip(row=grid.get_rows()[0], column=column)
    return [(control.get_time(), control.get_number(), control.get_value()) for control in clip.get_controls()]


class TestSetRows(unittest.TestCase):

    def test_a_set_comes_before_the_add_on_the_same_step(self):
        data = one_clip(rows={file_format.REGISTER_SET_ROWS[test_registers.AX]: [SET_TO], file_format.REGISTER_ADD_ROWS[test_registers.AX]: [ADDED], file_format.REGISTER_NOTE_ROWS[test_registers.AX]: [1]})
        self.assertEqual(pitches(data), scale_notes([SET_TO + ADDED]))

    def test_a_set_alone_changes_the_register_with_no_add_anywhere(self):
        data = one_clip(steps=2, rows={file_format.REGISTER_SET_ROWS[test_registers.AX]: [SET_TO, None], file_format.REGISTER_NOTE_ROWS[test_registers.AX]: [1, 1]})
        self.assertEqual(pitches(data), scale_notes([SET_TO, SET_TO]))

    def test_a_set_of_zero_sets_and_a_blank_leaves_the_register(self):
        data = one_clip(steps=2, rows={file_format.REGISTER_SET_ROWS[test_registers.AX]: [None, 0], file_format.REGISTER_NOTE_ROWS[test_registers.AX]: [1, 1]}, registers=registers(AX=SET_TO))
        self.assertEqual(pitches(data), scale_notes([SET_TO, 0]))

    def test_a_set_past_the_registers_maximum_stops_there_and_never_wraps(self):
        data = one_clip(rows={file_format.REGISTER_SET_ROWS[test_registers.AX]: [TOO_HIGH], file_format.REGISTER_NOTE_ROWS[test_registers.AX]: [1]}, registers={test_registers.AX: {RegisterSetting.RESET_BEHAVIOR: ResetBehavior.OVERFLOW}})
        self.assertEqual(pitches(data), scale_notes([10]))


class TestTheSettings(unittest.TestCase):
    """The track's bindings and the register's Allowed Inc Max, as a file holds them and as their setters change them."""

    def test_a_file_whose_adds_pass_the_limit_is_refused_and_opens_corrected_within_it(self):
        past = set_defaults.DEFAULT_ALLOWED_INC_MAX + ADDED
        data = as_setlist(one_clip(steps=2, rows={file_format.REGISTER_ADD_ROWS[test_registers.AX]: [past, -past]}))
        with self.assertRaises(SongFileError):
            Setlist.from_data(data=data)
        setlist, corrections = Setlist.from_data_corrected(data=data)
        self.assertEqual(len(corrections), 1)
        pattern = setlist.get_pattern(test_registers.X)
        self.assertEqual([pattern.get_value(row=file_format.REGISTER_ADD_ROWS[test_registers.AX], step=step) for step in (0, 1)], [set_defaults.DEFAULT_ALLOWED_INC_MAX, -set_defaults.DEFAULT_ALLOWED_INC_MAX])

    def test_a_registers_allowed_inc_max_defaults_to_enough_for_every_example_and_has_its_limits(self):
        self.assertEqual(Register().get_allowed_inc_max(), set_defaults.DEFAULT_ALLOWED_INC_MAX)
        register = Register()
        register.set_setting(name=RegisterSetting.ALLOWED_INC_MAX, value=limits.MIN_ALLOWED_INC_MAX)
        self.assertEqual(register.get_allowed_inc_max(), limits.MIN_ALLOWED_INC_MAX)
        for wrong in (limits.MIN_ALLOWED_INC_MAX - 1, limits.MAX_REGISTER_VALUE + 1):
            with self.subTest(value=wrong), self.assertRaises(InvalidValue):
                register.set_setting(name=RegisterSetting.ALLOWED_INC_MAX, value=wrong)


if __name__ == '__main__':
    unittest.main()
