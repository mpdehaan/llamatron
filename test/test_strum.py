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
"""Strum: a chord's notes sounding one after another, the user's design of 2026-11-11.

Each test plays C major triads, four quarter notes, a bar at 120 beats a minute, where a whole
note lasts two seconds, so 8 milliseconds between strings is 1/250 of a whole note.
"""

import unittest

from llamatron.composition.file_format import (
    ClipSlotSetting, GeneratorKind, PatternSetting, Row, SceneSetting, Section, SongSetting, StrumDirection, StrumPart, StrumSpread, TrackSetting, UpstrokeStrings,
    strum_setting,
)
from llamatron.composition.song_file_error import SongFileError
from llamatron.exporters.timing import timed_events
from llamatron.support.rational import Rational
from rendering import render_data, setlist_from_data
from test_registers import LEAD, X, pattern, song

TRIAD = '3'
TEMPO = 120
STEPS = 4
NORMAL_GAP = Rational(1, 250)
HARP_GAP = Rational(7, 200)
C = 60
E = 64
G = 67
STRUMMED = 'strummed'
VELOCITY = 100


def chords(*, track=None, clip=None, rows=None, chain=None, generator=None, steps=STEPS, step_size='1/4'):
    """Return a song whose lead plays triads on every step, the track and the clip given strum settings, and the clip's chain naming a Strum generator."""
    made = dict(pattern(steps, **{Row.CHORD: [TRIAD] * steps, Row.VELOCITY: [VELOCITY] * steps, **(rows or {})}), **{PatternSetting.STEP_SIZE: step_size})
    clip_slot = {ClipSlotSetting.PATTERN: X, **(clip or {})}
    if chain:
        clip_slot[ClipSlotSetting.CHAINS] = [STRUMMED]
    data = song(patterns={X: made}, scenes=[{SceneSetting.TRACKS: {LEAD: clip_slot}}])
    data[SongSetting.TEMPO] = TEMPO
    data[Section.TRACKS][LEAD] = dict(track or {})
    if chain:
        data[Section.STRUMS] = {STRUMMED: generator or {}}
        data[Section.CHAINS] = {STRUMMED: [{GeneratorKind.STRUM: STRUMMED}]}
    return data


def events(data):
    grid = render_data(data)
    clip = grid.get_clip(row=grid.get_rows()[0], column=grid.get_columns()[0])
    return sorted(timed_events(clip=clip, scale=clip.get_scale())[0])


def first_chord(data):
    """Return (start, pitch, velocity) of the first chord's notes, in the order they sound."""
    return [(start, pitch, velocity) for start, _, pitch, velocity in events(data) if start < Rational(1, 8)]


def strum(**parts):
    return {strum_setting(part): value for part, value in parts.items()}


class TestStrum(unittest.TestCase):

    def test_no_strum_plays_every_note_together(self):
        self.assertEqual({start for start, _, _ in first_chord(chords())}, {0})

    def test_a_downstroke_plays_low_to_high_a_spread_apart(self):
        played = first_chord(chords(track=strum(**{StrumPart.DIRECTION: StrumDirection.DOWN})))
        self.assertEqual(played, [(0, C, VELOCITY), (NORMAL_GAP, E, VELOCITY), (2 * NORMAL_GAP, G, VELOCITY)])

    def test_an_upstroke_plays_high_to_low(self):
        played = first_chord(chords(track=strum(**{StrumPart.DIRECTION: StrumDirection.UP})))
        self.assertEqual([pitch for _, pitch, _ in played], [G, E, C])

    def test_the_spread_is_in_milliseconds_whatever_the_tempo(self):
        data = chords(track=strum(**{StrumPart.DIRECTION: StrumDirection.DOWN, StrumPart.SPREAD: StrumSpread.HARP}))
        self.assertEqual(first_chord(data)[1][0], HARP_GAP)
        data[SongSetting.TEMPO] = TEMPO // 2
        self.assertEqual(first_chord(data)[1][0], HARP_GAP / 2)

    def test_every_note_still_ends_with_its_chord(self):
        played = events(chords(track=strum(**{StrumPart.DIRECTION: StrumDirection.DOWN})))
        self.assertEqual({end for start, end, _, _ in played if start < Rational(1, 8)}, {Rational(1, 4)})

    def test_by_the_beat_is_down_on_a_beat_and_up_between(self):
        data = chords(track=strum(**{StrumPart.DIRECTION: StrumDirection.BY_THE_BEAT}), steps=2, step_size='1/8')
        played = events(data)
        on_the_beat = [pitch for start, _, pitch, _ in played if start < Rational(1, 16)]
        between = [pitch for start, _, pitch, _ in played if start >= Rational(1, 8)]
        self.assertEqual(on_the_beat, [C, E, G])
        self.assertEqual(between, [G, E, C])

    def test_down_up_alternates_chord_by_chord(self):
        played = events(chords(track=strum(**{StrumPart.DIRECTION: StrumDirection.DOWN_UP}), steps=2))
        second = [pitch for start, _, pitch, _ in played if start >= Rational(1, 4)]
        self.assertEqual(second, [G, E, C])

    def test_a_fade_makes_the_last_string_that_much_quieter(self):
        played = first_chord(chords(track=strum(**{StrumPart.DIRECTION: StrumDirection.DOWN, StrumPart.FADE: 20})))
        self.assertEqual([velocity for _, _, velocity in played], [VELOCITY, 90, 80])

    def test_an_upstroke_on_the_top_strings_leaves_the_lowest_out(self):
        data = chords(track=strum(**{StrumPart.DIRECTION: StrumDirection.UP, StrumPart.UPSTROKE_STRINGS: UpstrokeStrings.TOP_3}), rows={Row.CHORD: ['7'] * STEPS})
        self.assertEqual(len(first_chord(data)), 3)

    def test_loose_timing_varies_the_gaps_the_same_way_every_time_with_a_seed(self):
        data = chords(track=strum(**{StrumPart.DIRECTION: StrumDirection.DOWN, StrumPart.LOOSE_TIMING: 50}))
        data[SongSetting.SEED] = 3
        gaps = [start for start, _, _ in first_chord(data)]
        self.assertNotEqual(gaps[1], NORMAL_GAP)
        self.assertEqual(gaps, [start for start, _, _ in first_chord(data)])


class TestWhichStrumWins(unittest.TestCase):

    def test_the_clip_wins_over_its_track(self):
        data = chords(track=strum(**{StrumPart.DIRECTION: StrumDirection.DOWN}), clip=strum(**{StrumPart.DIRECTION: StrumDirection.UP}))
        self.assertEqual([pitch for _, pitch, _ in first_chord(data)], [G, E, C])

    def test_a_clip_set_to_off_strums_nothing(self):
        data = chords(track=strum(**{StrumPart.DIRECTION: StrumDirection.DOWN}), clip=strum(**{StrumPart.DIRECTION: StrumDirection.OFF}))
        self.assertEqual({start for start, _, _ in first_chord(data)}, {0})

    def test_a_generator_wins_over_both_and_strums_by_the_beat_when_left_blank(self):
        data = chords(track=strum(**{StrumPart.DIRECTION: StrumDirection.UP}), chain=True, generator={})
        self.assertEqual([pitch for _, pitch, _ in first_chord(data)], [C, E, G])


class TestWhatAFileHolds(unittest.TestCase):

    def test_an_unknown_direction_is_refused(self):
        with self.assertRaises(SongFileError):
            setlist_from_data(chords(track=strum(**{StrumPart.DIRECTION: 'sideways'})))

    def test_a_fade_past_its_most_is_refused(self):
        with self.assertRaises(SongFileError):
            setlist_from_data(chords(track={TrackSetting.STRUM_DIRECTION: StrumDirection.DOWN, TrackSetting.STRUM_FADE: 51}))
