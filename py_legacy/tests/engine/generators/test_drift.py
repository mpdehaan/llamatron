# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Drift: one process for the whole song, triggering every so often, moving from its version A to its version B, heard by every clip whose chain names it.

Each test plays clips of four quarter-note steps, a bar of
4/4, so that a drift's triggers, a bar each unless set, fall on each repeat of a clip.
"""

import unittest

from llamatron.engine.generators import drift as drift_plugin
from llamatron.engine.generators.drift.model import DriftSetting, versioned
from llamatron.engine.generators.drift.play import DriftPlay
from llamatron.model.schema import defaults
from llamatron.model.schema.file_format import ClipSlotSetting, DriftDirection, DriftValue, DriftVersion, Row, SceneSetting, Section
from tests.support import song_playing
from tests.support.rendering import song_from_data
from tests.support.song_playing import pattern, pitches, scale_notes, song, velocities

DRIFT = 'sway'
CHAIN = 'swaying'
OTHER = 'other'
STEPS = 4
BARS = 4
SEED = 11
C_MINOR = 'C minor'
D = 'D'
D_MAJOR_SECOND = 64
E_FLAT = 63
# The default velocity is the loudest, so the tests drift softer.
SOFTER = -20


def a(value):
    return versioned(version=DriftVersion.A, value=value)


def b(value):
    return versioned(version=DriftVersion.B, value=value)


def drifting(*, drift, rows=None, repeat=BARS, seed=None, tracks=(song_playing.LEAD,), more_scales=None):
    """Return a song whose tracks each play a bar of four quarter-note Cs, repeated, every clip's chain naming one drift."""
    data = song(
        patterns={song_playing.X: pattern(STEPS, **(rows or {}))},
        scenes=[{SceneSetting.TRACKS: {track: {ClipSlotSetting.PATTERN: song_playing.X, ClipSlotSetting.REPEAT: repeat, ClipSlotSetting.CHAINS: [CHAIN]} for track in tracks}}],
        tracks=tracks,
    )
    data[drift_plugin.SECTION] = {DRIFT: drift}
    data[Section.CHAINS] = {CHAIN: [{drift_plugin.NAME: DRIFT}]}
    if seed is not None:
        data['seed'] = seed
    if more_scales:
        data[Section.SCALES].update(more_scales)
    return data


def per_bar(values):
    """Return the first value of each bar of four."""
    return values[::STEPS]


class TestDriftPositions(unittest.TestCase):

    def play(self, *, direction, steps=2):
        return DriftPlay(song=song_from_data(drifting(drift={DriftSetting.STEPS_TO_B: steps, DriftSetting.DIRECTION: direction})), seed=SEED)

    def test_each_direction_moves_its_way_from_a(self):
        expected = {
            DriftDirection.FORWARD: [0, 0.5, 1, 1, 1],
            DriftDirection.LOOP: [0, 0.5, 1, 0, 0.5],
            DriftDirection.PENDULUM: [0, 0.5, 1, 0.5, 0],
        }
        for direction, positions in expected.items():
            with self.subTest(direction=direction):
                play = self.play(direction=direction)
                self.assertEqual([play.position(name=DRIFT, trigger=trigger) for trigger in range(len(positions))], positions)

    def test_a_brownian_drift_starts_at_a_and_stays_between_a_and_b(self):
        play = self.play(direction=DriftDirection.BROWNIAN, steps=3)
        positions = [play.position(name=DRIFT, trigger=trigger) for trigger in range(50)]
        self.assertEqual(positions[0], 0)
        self.assertTrue(all(0 <= position <= 1 for position in positions))
        self.assertGreater(len(set(positions)), 1)


class TestWhatADriftDoes(unittest.TestCase):

    def test_velocity_moves_from_a_to_b_a_trigger_at_a_time(self):
        data = drifting(drift={DriftSetting.STEPS_TO_B: 2, b(DriftValue.VELOCITY): SOFTER})
        self.assertEqual(per_bar(velocities(data)), [defaults.DEFAULT_VELOCITY, defaults.DEFAULT_VELOCITY + SOFTER // 2, defaults.DEFAULT_VELOCITY + SOFTER, defaults.DEFAULT_VELOCITY + SOFTER])

    def test_a_probability_of_minus_100_silences_every_note(self):
        self.assertEqual(velocities(drifting(drift={a(DriftValue.PROBABILITY): -100, b(DriftValue.PROBABILITY): -100})), [])

    def test_a_degree_moves_every_note_along_the_scale(self):
        self.assertEqual(set(pitches(drifting(drift={a(DriftValue.DEGREE): 2, b(DriftValue.DEGREE): 2}))), set(scale_notes([2])))

    def test_a_scale_override_plays_the_degrees_in_another_scale(self):
        rows = {Row.DEGREE: [3] * STEPS}
        drift = {a(DriftValue.SCALE): C_MINOR, b(DriftValue.SCALE): C_MINOR, a(DriftValue.SCALE_PROBABILITY): 100, b(DriftValue.SCALE_PROBABILITY): 100}
        data = drifting(drift=drift, rows=rows, more_scales={C_MINOR: {'root': 'C', 'type': 'minor'}})
        self.assertEqual(set(pitches(data)), {E_FLAT})

    def test_a_root_override_plays_the_scale_from_another_root(self):
        rows = {Row.DEGREE: [2] * STEPS}
        data = drifting(drift={a(DriftValue.ROOT): D, b(DriftValue.ROOT): D, a(DriftValue.ROOT_PROBABILITY): 100, b(DriftValue.ROOT_PROBABILITY): 100}, rows=rows)
        self.assertEqual(set(pitches(data)), {D_MAJOR_SECOND})

    def test_two_tracks_naming_one_drift_hear_the_same_random_degree(self):
        data = drifting(drift={a(DriftValue.DEGREE_RANDOM): 3, b(DriftValue.DEGREE_RANDOM): 3}, tracks=(song_playing.LEAD, OTHER), seed=SEED)
        self.assertEqual(pitches(data, track=song_playing.LEAD), pitches(data, track=OTHER))

    def test_a_seeded_drift_plays_the_same_every_time(self):
        data = drifting(drift={a(DriftValue.DEGREE_RANDOM): 3, b(DriftValue.DEGREE_RANDOM): 3}, seed=SEED)
        self.assertEqual(pitches(data), pitches(data))

    def test_a_clip_that_names_no_drift_hears_nothing(self):
        data = drifting(drift={a(DriftValue.VELOCITY): SOFTER, b(DriftValue.VELOCITY): SOFTER})
        del data[Section.SCENES][0][SceneSetting.TRACKS][song_playing.LEAD][ClipSlotSetting.CHAINS]
        self.assertEqual(set(velocities(data)), {defaults.DEFAULT_VELOCITY})


if __name__ == '__main__':
    unittest.main()
