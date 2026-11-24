# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""music_theory's analysis chapter: the key notes are in, and the chord that sounds, found from the notes alone."""

from typing import NamedTuple
import unittest

from llamatron.music_theory.analysis import chords, keys

C = 0
A = 9
WHOLE = 1
HALF = 0.5


class Heard(NamedTuple):
    start: float
    end: float
    pitch: int


def held(pitches, *, length=WHOLE):
    """Return notes of the pitches one after another, each lasting a length."""
    return [Heard(start=place * length, end=(place + 1) * length, pitch=pitch) for place, pitch in enumerate(pitches)]


class TestKeys(unittest.TestCase):

    def test_a_major_scale_dwelling_on_its_tonic_triad_is_in_its_major_key(self):
        tune = held([60, 62, 64, 65, 67, 69, 71, 72, 67, 64, 60])
        self.assertEqual(keys.key_of_notes(tune)[:2], (C, keys.MAJOR))

    def test_the_same_notes_dwelling_on_the_relative_minor_triad_are_in_the_minor_key(self):
        tune = held([57, 60, 64, 57, 59, 60, 62, 64, 65, 64, 60, 57, 56, 57, 69, 57])
        self.assertEqual(keys.key_of_notes(tune)[:2], (A, keys.MINOR))

    def test_how_long_each_note_sounds_is_weighed_not_how_often_it_starts(self):
        weights = keys.pitch_weights(held([60, 60], length=HALF) + held([67], length=WHOLE))
        self.assertEqual(weights[C], WHOLE)
        self.assertEqual(weights[7], WHOLE)

    def test_nothing_sounding_is_c_major(self):
        self.assertEqual(keys.key_of_notes([])[:2], (C, keys.MAJOR))


class TestChords(unittest.TestCase):

    def weights(self, pitches):
        return keys.pitch_weights(held(pitches))

    def test_a_triad_is_its_chord_with_its_root(self):
        self.assertEqual(chords.chord_of(self.weights([60, 64, 67])), (C, chords.MAJOR))
        self.assertEqual(chords.chord_of(self.weights([57, 60, 64])), (A, chords.MINOR))

    def test_one_note_alone_and_silence_are_no_chord(self):
        self.assertIsNone(chords.chord_of(self.weights([48, 60])))
        self.assertIsNone(chords.chord_of([0.0] * 12))
