# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The chords a lead sheet prints, estimated from notes (music_theory/harmony/chord_estimate.py): the triad covering the most
time in each bar, a bar's halves where they clearly differ, a seventh only where the accompaniment sounds it, a power chord
where no third sounds, and the chords of the key preferred."""

import unittest

from llamatron.exporters.pdf.printed_song import PrintedNote
from llamatron.math.rational import Rational
from llamatron.model.objects.named_scale import NamedScale
from llamatron.model.schema.file_format import ChordSymbol, ScaleKind
from llamatron.model.values.note import NoteName
from llamatron.music_theory.harmony import chord_estimate
from llamatron.music_theory.harmony.chord_estimate import ChordLevel, Music

BAR = Rational(1)
HALF = Rational(1, 2)
C_MAJOR = NamedScale(root=NoteName.C, kind=ScaleKind.MAJOR)
C = 60
E = 64
F = 65
G = 67
A = 69
B_FLAT = 70


def held(*pitches, start=0 * BAR, end=BAR):
    """Return notes held together from a start to an end."""
    return [PrintedNote(start=start, end=end, pitch=pitch) for pitch in pitches]


def estimated(notes, *, tune=(), level=ChordLevel.TRIADS, bars=1):
    """Return the chords of notes over so many bars of 4/4 in C major, as (start, end, root, symbol)."""
    music = Music(notes=tuple(notes), tune=frozenset(tune))
    spans = [(bar * BAR, (bar + 1) * BAR) for bar in range(bars)]
    return [tuple(chord) for chord in chord_estimate.estimated_chords(music=music, bars=spans, scale_at=lambda _: C_MAJOR, level=level)]


class TestChordEstimate(unittest.TestCase):

    def test_a_bar_of_one_chord_and_a_bar_whose_halves_differ(self):
        self.assertEqual(estimated(held(C, E, G)), [(0 * BAR, BAR, C % 12, ChordSymbol.MAJOR)])
        halves = held(C, E, G, end=HALF) + held(F, A, C + 12, start=HALF)
        self.assertEqual(estimated(halves), [(0 * BAR, HALF, C % 12, ChordSymbol.MAJOR), (HALF, BAR, F % 12, ChordSymbol.MAJOR)])

    def test_a_chord_carrying_on_into_the_next_bar_is_one_chord(self):
        self.assertEqual(estimated(held(C, E, G, end=2 * BAR), bars=2), [(0 * BAR, 2 * BAR, C % 12, ChordSymbol.MAJOR)])

    def test_a_seventh_only_at_sevenths_and_only_where_the_accompaniment_sounds_it(self):
        notes = held(C, E, G, B_FLAT)
        self.assertEqual(estimated(notes)[0][3], ChordSymbol.MAJOR)
        self.assertEqual(estimated(notes, level=ChordLevel.SEVENTHS)[0][3], ChordSymbol.DOMINANT7)
        self.assertEqual(estimated(notes, tune=notes[3:], level=ChordLevel.SEVENTHS)[0][3], ChordSymbol.MAJOR)

    def test_a_root_and_fifth_with_no_third_is_a_power_chord(self):
        self.assertEqual(estimated(held(C, G))[0][3], ChordSymbol.POWER)
