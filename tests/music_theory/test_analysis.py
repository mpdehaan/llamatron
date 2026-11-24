# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""music_theory's analysis chapter: the key notes are in, and the chord that sounds, found from the notes alone."""

from typing import NamedTuple
import unittest

from llamatron.music_theory.analysis import chords, keys, roles

C = 0
A = 9
WHOLE = 1
HALF = 0.5


class Heard(NamedTuple):
    start: float
    end: float
    pitch: int


class Part(NamedTuple):
    name: str
    drum: bool
    notes: tuple


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


BEATS_PER_BAR = 4
BARS = 4


def timed(pairs):
    """Return notes from (start, length, pitch), one after another as written."""
    return tuple(Heard(start=start, end=start + length, pitch=pitch) for start, length, pitch in pairs)


def tune_low():
    """A singable tune in the middle register: steps and one leap, notes of several lengths, through all four bars."""
    pitches = [60, 62, 64, 62, 60, 65, 64, 62, 64, 65, 67, 65, 64, 62, 60, 59, 60, 62]
    lengths = [1, 0.5, 0.5, 1, 1, 1.5, 0.5, 1, 1, 0.5, 0.5, 1, 1, 0.5, 0.5, 1, 2, 2]
    start = 0
    pairs = []
    for pitch, length in zip(pitches, lengths):
        pairs.append((start, length, pitch))
        start += length
    return timed(pairs)


def arpeggio_high():
    """An even arpeggio above it: the same three notes in leaps, every one half a beat, a sequence rather than a tune."""
    return timed([(place * 0.5, 0.5, [72, 76, 79, 84][place % 4]) for place in range(BARS * BEATS_PER_BAR * 2)])


def bass_line():
    return timed([(bar * BEATS_PER_BAR, BEATS_PER_BAR, [36, 41, 43, 36][bar]) for bar in range(BARS)])


def held_chords():
    return timed([(bar * BEATS_PER_BAR, BEATS_PER_BAR, pitch) for bar in range(BARS) for pitch in (60, 64, 67)])


class TestRoles(unittest.TestCase):

    def roles(self, parts):
        found = roles.roles_of(parts=parts, bars=BARS, beats_per_bar=BEATS_PER_BAR)
        return {part.name: role for part, role in found.items()}

    def test_the_melody_is_the_line_that_moves_like_one_not_the_highest(self):
        found = self.roles([Part('tune', False, tune_low()), Part('arpeggio', False, arpeggio_high()), Part('bass', False, bass_line())])
        self.assertEqual(found, {'tune': roles.MELODY, 'arpeggio': roles.COUNTER, 'bass': roles.BASS})

    def test_long_chords_are_a_pad_and_drums_are_drums(self):
        found = self.roles([Part('tune', False, tune_low()), Part('chords', False, held_chords()), Part('kit', True, bass_line())])
        self.assertEqual(found, {'tune': roles.MELODY, 'chords': roles.PAD, 'kit': roles.DRUMS})
