# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A Guitarify in Strum mode: a chord's notes sounding one after another, at the very end of a clip.

Each test plays C major triads, four quarter notes, a bar at 120 beats a minute, where a whole
note lasts two seconds, so 8 milliseconds between strings is 1/250 of a whole note.
"""

import unittest

from llamatron.engine.generators import guitarify as guitarify_plugin
from llamatron.engine.generators.guitarify import model as guitarify_model
from llamatron.engine.timing.timing import timed_events
from llamatron.math.rational import Rational
from llamatron.model.file.song_file_error import SongFileError
from llamatron.model.schema.file_format import ClipSlotSetting, GuitarifySetting, PatternSetting, Row, SceneSetting, Section, SongSetting, StrumDirection
from tests.engine.realizer import test_registers
from tests.engine.realizer.test_registers import pattern, song
from tests.support.rendering import render_song, setlist_from_data, song_from_data

TRIAD = '3'
SEVENTH = '7'
TEMPO = 120
STEPS = 4
A_SEED = 3
NORMAL_GAP = Rational(1, 250)
WIDEST_SPREAD = guitarify_model.MAX_GUITAR_SPREAD
WIDEST_GAP = Rational(3, 100)
C = 60
E = 64
G = 67
STRUMMED = 'strummed'
STRUMMED_CHAIN = 'strummed chain'
PLAYED = 'played'
VELOCITY = 100
NONE = 0
FADE = 20
LOOSE = 50
TOP_THREE = 3


def chords(*, settings=None, steps=STEPS, step_size='1/4', rows=None, guitars=None):
    """Return a song whose lead plays triads on every step through one chain of Guitarify generators, each (name, settings); by
    default one Guitarify in Strum mode with the settings given, its fade and loose timing none and every string on an upstroke."""
    made = dict(pattern(steps, **{Row.CHORD: [TRIAD] * steps, Row.VELOCITY: [VELOCITY] * steps, **(rows or {})}), **{PatternSetting.STEP_SIZE: step_size})
    clip_slot = {ClipSlotSetting.PATTERN: test_registers.X, ClipSlotSetting.CHAINS: [STRUMMED_CHAIN]}
    data = song(patterns={test_registers.X: made}, scenes=[{SceneSetting.TRACKS: {test_registers.LEAD: clip_slot}}])
    data[SongSetting.TEMPO] = TEMPO
    if guitars is None:
        guitars = [(STRUMMED, strum_mode(**(settings or {})))]
    data[guitarify_plugin.SECTION] = dict(guitars)
    data[Section.CHAINS] = {STRUMMED_CHAIN: [{guitarify_plugin.NAME: name} for name, _ in guitars]}
    return data


def strum_mode(**settings):
    """Return a Guitarify's settings in Strum mode with no fade, no loose timing and every string on an upstroke, then those given."""
    return {
        GuitarifySetting.MODE: guitarify_model.STRUM, GuitarifySetting.FADE: NONE, GuitarifySetting.LOOSE_TIMING: NONE,
        GuitarifySetting.UPSTROKE: guitarify_model.EVERY_STRING, **settings,
    }


def events(data, *, seed=None):
    grid = render_song(song_from_data(data), seed=seed)
    clip = grid.get_clip(row=grid.get_rows()[0], column=grid.get_columns()[0])
    return sorted(timed_events(clip=clip, scale=clip.get_scale())[0])


def first_chord(data, *, seed=None):
    """Return (start, pitch, velocity) of the first chord's notes, in the order they sound, drawn from a seed where one is given."""
    return [(start, pitch, velocity) for start, _, pitch, velocity in events(data, seed=seed) if start < Rational(1, 8)]


class TestStrumMode(unittest.TestCase):

    def test_a_downstroke_plays_low_to_high_a_spread_apart(self):
        played = first_chord(chords(settings={GuitarifySetting.DIRECTION: StrumDirection.DOWN}))
        self.assertEqual(played, [(0, C, VELOCITY), (NORMAL_GAP, E, VELOCITY), (2 * NORMAL_GAP, G, VELOCITY)])

    def test_an_upstroke_plays_high_to_low(self):
        played = first_chord(chords(settings={GuitarifySetting.DIRECTION: StrumDirection.UP}))
        self.assertEqual([pitch for _, pitch, _ in played], [G, E, C])

    def test_the_spread_is_in_milliseconds_whatever_the_tempo(self):
        data = chords(settings={GuitarifySetting.DIRECTION: StrumDirection.DOWN, GuitarifySetting.SPREAD: WIDEST_SPREAD})
        self.assertEqual(first_chord(data)[1][0], WIDEST_GAP)
        data[SongSetting.TEMPO] = TEMPO // 2
        self.assertEqual(first_chord(data)[1][0], WIDEST_GAP / 2)

    def test_every_note_still_ends_with_its_chord(self):
        played = events(chords(settings={GuitarifySetting.DIRECTION: StrumDirection.DOWN}))
        self.assertEqual({end for start, end, _, _ in played if start < Rational(1, 8)}, {Rational(1, 4)})

    def test_by_the_beat_is_the_direction_left_out_down_on_a_beat_and_up_between(self):
        played = events(chords(steps=2, step_size='1/8'))
        on_the_beat = [pitch for start, _, pitch, _ in played if start < Rational(1, 16)]
        between = [pitch for start, _, pitch, _ in played if start >= Rational(1, 8)]
        self.assertEqual(on_the_beat, [C, E, G])
        self.assertEqual(between, [G, E, C])

    def test_down_up_alternates_chord_by_chord(self):
        played = events(chords(settings={GuitarifySetting.DIRECTION: StrumDirection.DOWN_UP}, steps=2))
        second = [pitch for start, _, pitch, _ in played if start >= Rational(1, 4)]
        self.assertEqual(second, [G, E, C])

    def test_a_fade_makes_the_last_string_that_much_quieter(self):
        played = first_chord(chords(settings={GuitarifySetting.DIRECTION: StrumDirection.DOWN, GuitarifySetting.FADE: FADE}))
        self.assertEqual([velocity for _, _, velocity in played], [VELOCITY, 90, 80])

    def test_an_upstroke_on_the_top_strings_leaves_the_lowest_out(self):
        settings = {GuitarifySetting.DIRECTION: StrumDirection.UP, GuitarifySetting.UPSTROKE: TOP_THREE}
        self.assertEqual(len(first_chord(chords(settings=settings, rows={Row.CHORD: [SEVENTH] * STEPS}))), TOP_THREE)

    def test_loose_timing_varies_the_gaps_the_same_way_every_time_with_a_seed(self):
        data = chords(settings={GuitarifySetting.DIRECTION: StrumDirection.DOWN, GuitarifySetting.LOOSE_TIMING: LOOSE})
        gaps = [start for start, _, _ in first_chord(data, seed=A_SEED)]
        self.assertNotEqual(gaps[1], NORMAL_GAP)
        self.assertEqual(gaps, [start for start, _, _ in first_chord(data, seed=A_SEED)])


class TestWhichStrumWins(unittest.TestCase):

    def test_guitar_mode_strums_nothing_at_the_end(self):
        played = first_chord(chords(guitars=[(PLAYED, {GuitarifySetting.STROKES: False, GuitarifySetting.SHAPE: False})]))
        self.assertEqual({start for start, _, _ in played}, {0})

    def test_the_last_guitarify_in_strum_mode_of_the_chains_wins(self):
        down = strum_mode(**{GuitarifySetting.DIRECTION: StrumDirection.DOWN})
        up = strum_mode(**{GuitarifySetting.DIRECTION: StrumDirection.UP})
        played = first_chord(chords(guitars=[(STRUMMED, down), (PLAYED, up)]))
        self.assertEqual([pitch for _, pitch, _ in played], [G, E, C])


class TestWhatAFileHolds(unittest.TestCase):

    def test_an_unknown_mode_or_direction_is_refused(self):
        for setting in (GuitarifySetting.MODE, GuitarifySetting.DIRECTION):
            with self.subTest(setting=setting), self.assertRaises(SongFileError):
                setlist_from_data(chords(settings={setting: 'sideways'}))
