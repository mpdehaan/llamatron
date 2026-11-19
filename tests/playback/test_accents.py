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

"""Tests of accents and default velocities: a step's Accent switch, and the Default velocity and Accent of a track and of its instrument.

The lead plays a bar of sixteenth notes. A step with no velocity typed plays at the default
velocity of the track that plays it, the track's own over its instrument's, and an accented step
adds the track's accent on top of its instrument's, stopping at MIDI's loudest.
"""

import unittest

from llamatron.composition import defaults, limits
from llamatron.composition.file_format import InstrumentSetting, Row, Section, TrackSetting, VelocitySetting
from llamatron.composition.song_file_error import SongFileError
from llamatron.exporters.timing import timed_events
from llamatron.music import midi
from tests.playback import test_registers, test_shapes
from tests.playback.test_shapes import one_scene
from tests.support import song_testing
from tests.support.rendering import as_setlist, render_data, setlist_from_data

SYNTH = 'synth'
QUIET = 80
QUIETER = 60
TYPED = 100
TRACK_ACCENT = 20
INSTRUMENT_ACCENT = 10
HALF = 50
# The first step of every beat of a bar of sixteenths is accented.
STEPS_IN_BEAT = 4
ON_THE_BEATS = [step % STEPS_IN_BEAT == 0 for step in range(test_shapes.STEPS)]
NOT_A_NUMBER = 'loud'


def with_accents(*, track=None, instrument=None, rows=None, scene=None):
    """Return a set whose lead plays a bar of sixteenths accented on the beats, with settings for the track and, where given, an instrument the track plays."""
    data = as_setlist(one_scene(rows={Row.ACCENT: ON_THE_BEATS, **(rows or {})}, scene=scene))
    song = next(iter(data[Section.SONGS].values()))
    song[Section.TRACKS][test_registers.LEAD] = dict(track or {})
    if instrument is not None:
        data[Section.INSTRUMENTS] = {SYNTH: instrument}
        song[Section.TRACKS][test_registers.LEAD][TrackSetting.INSTRUMENT] = SYNTH
    return data


def played(data):
    """Return the velocity of every note the lead plays, in time order."""
    grid = render_data(data)
    clip = grid.get_clip(row=grid.get_rows()[0], column=grid.get_columns()[0])
    return [velocity for start, end, pitch, velocity in sorted(timed_events(clip=clip, scale=clip.get_scale())[0])]


def accented(*, plain, accent):
    """Return the velocities of a bar whose beats are accented: plain, and plain with the accent on each beat."""
    return [plain + accent if on else plain for on in ON_THE_BEATS]


class TestDefaultVelocity(unittest.TestCase):
    """What a step with no velocity typed plays at."""

    def test_a_track_with_no_instrument_and_no_default_plays_at_the_loudest(self):
        self.assertEqual(played(with_accents(track={TrackSetting.ACCENT: limits.MIN_STEP_ACCENT})), [defaults.DEFAULT_VELOCITY] * test_shapes.STEPS)

    def test_a_track_s_default_velocity_is_what_a_blank_step_plays_at(self):
        data = with_accents(track={TrackSetting.DEFAULT_VELOCITY: QUIET, TrackSetting.ACCENT: limits.MIN_STEP_ACCENT})
        self.assertEqual(played(data), [QUIET] * test_shapes.STEPS)

    def test_an_instrument_s_default_velocity_reaches_its_tracks(self):
        data = with_accents(track={TrackSetting.ACCENT: limits.MIN_STEP_ACCENT}, instrument={InstrumentSetting.DEFAULT_VELOCITY: QUIETER})
        self.assertEqual(played(data), [QUIETER] * test_shapes.STEPS)

    def test_a_track_s_default_velocity_wins_over_its_instrument_s(self):
        data = with_accents(track={TrackSetting.DEFAULT_VELOCITY: QUIET, TrackSetting.ACCENT: limits.MIN_STEP_ACCENT}, instrument={InstrumentSetting.DEFAULT_VELOCITY: QUIETER})
        self.assertEqual(played(data), [QUIET] * test_shapes.STEPS)

    def test_a_typed_velocity_is_left_alone(self):
        data = with_accents(track={TrackSetting.DEFAULT_VELOCITY: QUIET, TrackSetting.ACCENT: limits.MIN_STEP_ACCENT}, rows={Row.VELOCITY: [TYPED] * test_shapes.STEPS})
        self.assertEqual(played(data), [TYPED] * test_shapes.STEPS)

    def test_the_song_answers_a_track_s_default_velocity(self):
        setlist = setlist_from_data(with_accents(instrument={InstrumentSetting.DEFAULT_VELOCITY: QUIETER}))
        song = setlist.get_songs()[0]
        track = song.get_track(test_registers.LEAD)
        self.assertEqual(song.default_velocity_of(track), QUIETER)
        track.set_default_velocity(QUIET)
        self.assertEqual(song.default_velocity_of(track), QUIET)
        track.set_default_velocity(None)
        setlist.get_instrument(SYNTH).set_default_velocity(None)
        self.assertEqual(song.default_velocity_of(track), defaults.DEFAULT_VELOCITY)


class TestAccents(unittest.TestCase):
    """What a step with its Accent on adds."""

    def test_a_track_starts_with_an_accent_and_an_instrument_with_none(self):
        setlist = setlist_from_data(with_accents(instrument={}))
        song = setlist.get_songs()[0]
        self.assertEqual(song.get_track(test_registers.LEAD).get_accent(), defaults.DEFAULT_TRACK_ACCENT)
        self.assertEqual(setlist.get_instrument(SYNTH).get_accent(), defaults.DEFAULT_INSTRUMENT_ACCENT)
        self.assertEqual(song.accent_of(song.get_track(test_registers.LEAD)), defaults.DEFAULT_TRACK_ACCENT)

    def test_an_accented_step_adds_the_track_s_accent_to_the_default_velocity(self):
        data = with_accents(track={TrackSetting.DEFAULT_VELOCITY: QUIET, TrackSetting.ACCENT: TRACK_ACCENT})
        self.assertEqual(played(data), accented(plain=QUIET, accent=TRACK_ACCENT))

    def test_an_accented_step_adds_to_a_typed_velocity(self):
        data = with_accents(track={TrackSetting.ACCENT: TRACK_ACCENT}, rows={Row.VELOCITY: [TYPED] * test_shapes.STEPS})
        self.assertEqual(played(data), accented(plain=TYPED, accent=TRACK_ACCENT))

    def test_the_track_s_accent_is_added_to_its_instrument_s(self):
        data = with_accents(track={TrackSetting.DEFAULT_VELOCITY: QUIET, TrackSetting.ACCENT: TRACK_ACCENT}, instrument={InstrumentSetting.ACCENT: INSTRUMENT_ACCENT})
        self.assertEqual(played(data), accented(plain=QUIET, accent=TRACK_ACCENT + INSTRUMENT_ACCENT))

    def test_a_track_with_no_accent_typed_adds_the_default(self):
        data = with_accents(track={TrackSetting.DEFAULT_VELOCITY: QUIET})
        self.assertEqual(played(data), accented(plain=QUIET, accent=defaults.DEFAULT_TRACK_ACCENT))

    def test_an_accent_stops_at_the_loudest_velocity(self):
        data = with_accents(track={TrackSetting.ACCENT: TRACK_ACCENT})
        self.assertEqual(played(data), [midi.MAX_VELOCITY] * test_shapes.STEPS)

    def test_a_pattern_with_no_accents_plays_as_before(self):
        data = with_accents(track={TrackSetting.DEFAULT_VELOCITY: QUIET, TrackSetting.ACCENT: TRACK_ACCENT}, rows={Row.ACCENT: [False] * test_shapes.STEPS})
        self.assertEqual(played(data), [QUIET] * test_shapes.STEPS)

    def test_accents_keep_their_proportion_under_a_scene_s_velocity(self):
        data = with_accents(track={TrackSetting.DEFAULT_VELOCITY: QUIET, TrackSetting.ACCENT: TRACK_ACCENT}, scene={VelocitySetting.LEVEL: HALF})
        half = round(HALF * (QUIET + TRACK_ACCENT) / 100)
        self.assertEqual(played(data)[:STEPS_IN_BEAT], [half, QUIET // 2, QUIET // 2, QUIET // 2])


class TestAccentsInAFile(unittest.TestCase):
    """What a file refuses and what is written back."""

    def test_a_default_velocity_and_an_accent_out_of_range_are_refused(self):
        for settings in ({TrackSetting.DEFAULT_VELOCITY: midi.MAX_VELOCITY + 1}, {TrackSetting.ACCENT: limits.MAX_STEP_ACCENT + 1}, {TrackSetting.ACCENT: NOT_A_NUMBER}):
            with self.subTest(settings=settings), self.assertRaises(SongFileError):
                setlist_from_data(with_accents(track=settings))
        for settings in ({InstrumentSetting.DEFAULT_VELOCITY: midi.MIN_VELOCITY - 1}, {InstrumentSetting.ACCENT: limits.MIN_STEP_ACCENT - 1}):
            with self.subTest(settings=settings), self.assertRaises(SongFileError):
                setlist_from_data(with_accents(instrument=settings))

    def test_what_is_set_is_written_and_what_is_cleared_is_not(self):
        setlist = setlist_from_data(with_accents(track={TrackSetting.DEFAULT_VELOCITY: QUIET, TrackSetting.ACCENT: TRACK_ACCENT}, instrument={InstrumentSetting.ACCENT: INSTRUMENT_ACCENT}))
        track = setlist.get_songs()[0].get_track(test_registers.LEAD)
        instrument = setlist.get_instrument(SYNTH)
        self.assertEqual(track.to_data()[TrackSetting.DEFAULT_VELOCITY], QUIET)
        self.assertEqual(track.to_data()[TrackSetting.ACCENT], TRACK_ACCENT)
        self.assertEqual(instrument.to_data()[InstrumentSetting.ACCENT], INSTRUMENT_ACCENT)
        self.assertEqual(instrument.copy().get_accent(), INSTRUMENT_ACCENT)
        track.set_default_velocity(None)
        track.set_accent(None)
        instrument.set_accent(None)
        self.assertNotIn(TrackSetting.DEFAULT_VELOCITY, track.to_data())
        self.assertNotIn(TrackSetting.ACCENT, track.to_data())
        self.assertNotIn(InstrumentSetting.ACCENT, instrument.to_data())

    def test_an_accent_row_is_written_back(self):
        setlist = setlist_from_data(with_accents())
        pattern = setlist.get_pattern(song_testing.X)
        self.assertEqual(pattern.to_data()[Row.ACCENT], ON_THE_BEATS)
