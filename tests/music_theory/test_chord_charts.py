# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The chords a chord chart prints (music_theory/harmony/chord_charts.py): a span's beats read as one chord where they belong
together, a real change kept, a power chord given the melody's third, each chord at its level, and the slashes each level
prints."""

import unittest

from llamatron.math.rational import Rational
from llamatron.model.schema.file_format import ChordSymbol
from llamatron.model.values.time_signature import TimeSignature
from llamatron.music_theory.harmony import chord_charts
from llamatron.music_theory.harmony.chord_charts import ChartChord, ChordLevel, HeardBeat, Stretch

BEAT = Rational(1, 4)
BAR = Rational(1, 2)
C = 0
E = 4
G = 7
A = 9
B = 11
NO_MELODY = {}


def charted(beats, *, level=ChordLevel.SEVENTHS, length=BAR, melody=NO_MELODY):
    """Return the chords of a stretch of 2/4, a chord heard over each bar, as a level prints them."""
    return chord_charts.charted_chords(beats=beats, stretch=Stretch(length=length, beat=BEAT, span=BAR), level=level, melody=melody)


class TestChordCharts(unittest.TestCase):

    def test_a_stride_bass_and_its_chord_read_as_one_chord(self):
        beats = [HeardBeat(start=0 * BEAT, root=C, symbol=ChordSymbol.POWER, bass=G), HeardBeat(start=BEAT, root=C, symbol=ChordSymbol.MAJOR, bass=None)]
        self.assertEqual(charted(beats), [ChartChord(start=0 * BEAT, end=BAR, root=C, symbol=ChordSymbol.MAJOR, bass=None)])

    def test_a_cadence_keeps_both_chords_and_at_sevenths_its_bass_on_the_fifth(self):
        beats = [HeardBeat(start=0 * BEAT, root=C, symbol=ChordSymbol.MAJOR, bass=G), HeardBeat(start=BEAT, root=G, symbol=ChordSymbol.DOMINANT7, bass=None)]
        self.assertEqual(charted(beats), [
            ChartChord(start=0 * BEAT, end=BEAT, root=C, symbol=ChordSymbol.MAJOR, bass=G),
            ChartChord(start=BEAT, end=BAR, root=G, symbol=ChordSymbol.DOMINANT7, bass=None),
        ])
        self.assertEqual([(chord.symbol, chord.bass) for chord in charted(beats, level=ChordLevel.TRIADS)], [(ChordSymbol.MAJOR, None), (ChordSymbol.MAJOR, None)])

    def test_a_tritone_arriving_on_the_same_root_starts_a_chord_anew(self):
        beats = [HeardBeat(start=0 * BEAT, root=C, symbol=ChordSymbol.MAJOR, bass=None), HeardBeat(start=BEAT, root=C, symbol=ChordSymbol.DOMINANT7, bass=None)]
        self.assertEqual([chord.symbol for chord in charted(beats)], [ChordSymbol.MAJOR, ChordSymbol.DOMINANT7])

    def test_a_power_chord_stays_unless_the_melody_sounds_its_third_on_a_beat(self):
        beats = [HeardBeat(start=0 * BEAT, root=C, symbol=ChordSymbol.POWER, bass=None)]
        self.assertEqual(charted(beats, level=ChordLevel.TRIADS)[0].symbol, ChordSymbol.POWER)
        self.assertEqual(charted(beats, level=ChordLevel.TRIADS, melody={BEAT: {E}})[0].symbol, ChordSymbol.MAJOR)
        self.assertEqual(charted(beats, melody={BEAT: {E - 1}})[0].symbol, ChordSymbol.MINOR)

    def test_each_level_prints_its_own_chord_types_and_a_two_note_chord_as_itself(self):
        for symbol, sevenths, triads in (
            (ChordSymbol.DOMINANT9, ChordSymbol.DOMINANT7, ChordSymbol.MAJOR), (ChordSymbol.MINOR11, ChordSymbol.MINOR7, ChordSymbol.MINOR),
            (ChordSymbol.MAJOR6, ChordSymbol.MAJOR, ChordSymbol.MAJOR), (ChordSymbol.HALF_DIMINISHED7, ChordSymbol.HALF_DIMINISHED7, ChordSymbol.DIMINISHED),
            (ChordSymbol.POWER, ChordSymbol.POWER, ChordSymbol.POWER),
        ):
            beats = [HeardBeat(start=0 * BEAT, root=C, symbol=symbol, bass=None)]
            self.assertEqual(charted(beats)[0].symbol, sevenths, symbol)
            self.assertEqual(charted(beats, level=ChordLevel.TRIADS)[0].symbol, triads, symbol)
            self.assertEqual(charted(beats, level=ChordLevel.AS_PLAYED)[0].symbol, symbol)

    def test_at_sevenths_a_bass_walking_by_step_keeps_its_slash_and_a_bass_that_leaps_loses_it(self):
        walking = [
            HeardBeat(start=0 * BEAT, root=C, symbol=ChordSymbol.MAJOR, bass=None), HeardBeat(start=BAR, root=C, symbol=ChordSymbol.MAJOR, bass=B),
            HeardBeat(start=2 * BAR, root=A, symbol=ChordSymbol.MINOR, bass=None),
        ]
        self.assertEqual([chord.bass for chord in charted(walking, length=3 * BAR)], [None, B, None])
        leaping = [HeardBeat(start=0 * BEAT, root=C, symbol=ChordSymbol.MAJOR, bass=E), HeardBeat(start=BAR, root=A, symbol=ChordSymbol.MINOR, bass=None)]
        self.assertEqual([chord.bass for chord in charted(leaping, length=2 * BAR)], [None, None])

    def test_as_played_prints_every_beat_as_heard(self):
        beats = [HeardBeat(start=0 * BEAT, root=C, symbol=ChordSymbol.POWER, bass=G), HeardBeat(start=BEAT, root=C, symbol=ChordSymbol.MAJOR, bass=None)]
        self.assertEqual(len(charted(beats, level=ChordLevel.AS_PLAYED)), 2)

    def test_a_chord_is_heard_over_half_a_bar_of_four_beats_and_a_bar_of_any_other(self):
        common = TimeSignature(beats=4, unit=4)
        self.assertEqual(chord_charts.chord_span(common), common.bar_length() / 2)
        waltz = TimeSignature(beats=3, unit=4)
        self.assertEqual(chord_charts.chord_span(waltz), waltz.bar_length())
