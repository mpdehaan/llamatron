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
"""Drift: one process for the whole song, triggering every so often, moving from its version A to its version B, heard by every clip whose chain names it.

The user's design of 2026-11-11. Each test plays clips of four quarter-note steps, a bar of
4/4, so that a drift's triggers, a bar each unless set, fall on each repeat of a clip.
"""

import unittest

from llamatron.composition.file_format import (
    REGISTER_NOTE_ROWS, ClipSlotSetting, DriftDirection, GeneratorKind, RegisterSetting, Row, SceneSetting, Section,
)
from llamatron.composition.defaults import DEFAULT_VELOCITY
from llamatron.composition.file_format import DriftValue, DriftVersion
from llamatron.composition.generator_settings import DriftSetting, versioned
from llamatron.composition.limits import MAX_REGISTER_VALUE, MIN_REGISTER_VALUE
from llamatron.playback.drift import DriftPlay
from rendering import song_from_data
from test_registers import AX, LEAD, X, pattern, pitches, scale_notes, song, velocities

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


def drifting(*, drift, rows=None, repeat=BARS, seed=None, tracks=(LEAD,), more_scales=None):
    """Return a song whose tracks each play a bar of four quarter-note Cs, repeated, every clip's chain naming one drift."""
    data = song(
        patterns={X: pattern(STEPS, **(rows or {}))},
        scenes=[{SceneSetting.TRACKS: {track: {ClipSlotSetting.PATTERN: X, ClipSlotSetting.REPEAT: repeat, ClipSlotSetting.CHAIN: CHAIN} for track in tracks}}],
        tracks=tracks,
    )
    data[Section.DRIFTS] = {DRIFT: drift}
    data[Section.CHAINS] = {CHAIN: [{GeneratorKind.DRIFT: DRIFT}]}
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
        self.assertEqual(per_bar(velocities(data)), [DEFAULT_VELOCITY, DEFAULT_VELOCITY + SOFTER // 2, DEFAULT_VELOCITY + SOFTER, DEFAULT_VELOCITY + SOFTER])

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
        data = drifting(drift={a(DriftValue.DEGREE_RANDOM): 3, b(DriftValue.DEGREE_RANDOM): 3}, tracks=(LEAD, OTHER), seed=SEED)
        self.assertEqual(pitches(data, track=LEAD), pitches(data, track=OTHER))

    def test_a_seeded_drift_plays_the_same_every_time(self):
        data = drifting(drift={a(DriftValue.DEGREE_RANDOM): 3, b(DriftValue.DEGREE_RANDOM): 3}, seed=SEED)
        self.assertEqual(pitches(data), pitches(data))

    def test_its_adds_join_the_registers_once_a_trigger_however_many_clips_name_it(self):
        rows = {REGISTER_NOTE_ROWS[AX]: [1] * STEPS}
        data = drifting(drift={a(DriftValue.AX_ADD): 1, b(DriftValue.AX_ADD): 1}, rows=rows, tracks=(LEAD, OTHER))
        data[Section.REGISTERS] = {AX: {RegisterSetting.MINIMUM: MIN_REGISTER_VALUE, RegisterSetting.MAXIMUM: MAX_REGISTER_VALUE}}
        self.assertEqual(per_bar(pitches(data)), scale_notes([1, 2, 3, 4]))

    def test_a_clip_that_names_no_drift_hears_nothing(self):
        data = drifting(drift={a(DriftValue.VELOCITY): SOFTER, b(DriftValue.VELOCITY): SOFTER})
        del data[Section.SCENES][0][SceneSetting.TRACKS][LEAD][ClipSlotSetting.CHAIN]
        self.assertEqual(set(velocities(data)), {DEFAULT_VELOCITY})


if __name__ == '__main__':
    unittest.main()
