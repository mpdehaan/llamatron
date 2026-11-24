# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""AutoChord, the Chords generator's mode that turns each single note into a chord (engine/generators/chords/auto_chord.py):
From scale builds the triad the scale builds on the note and leaves a note outside the scale alone, the fixed chords are built
on the note whatever the scale, Note on top ends the chord on the note, and a chord already written is left as it is."""

import unittest

from llamatron.engine.generators import chords as chords_plugin
from llamatron.engine.generators.chords import auto_chord, model as chords_model
from llamatron.engine.generators.chords.model import ChordsSetting
from llamatron.model.schema.file_format import Accidental, ClipSlotSetting, Row, SceneSetting, Section
from tests.engine.generators import test_follow_chords
from tests.engine.generators.test_follow_chords import pitches
from tests.support.song_playing import pattern, song

AUTO = 'auto chords'
CHAIN = 'chording'
FIGURE = 'figure'
# C, D and B of C major, and C sharp, outside it.
DEGREES = [1, 2, 7, 1]
E_FLAT = 63
G_SHARP = 68
F_SHARP = 66


def chorded(*, chord=None, on_top=False, figure_rows=None):
    """Return what the synth plays of a figure through an AutoChord of a chord, a chord a step."""
    settings = {ChordsSetting.MODE: chords_model.AUTO_CHORD}
    if chord is not None:
        settings[ChordsSetting.CHORD] = chord
    if on_top:
        settings[ChordsSetting.NOTE_ON_TOP] = True
    rows = {Row.DEGREE: DEGREES, **(figure_rows or {})}
    data = song(patterns={FIGURE: pattern(len(DEGREES), **rows)}, tracks=[test_follow_chords.SYNTH],
                scenes=[{SceneSetting.TRACKS: {test_follow_chords.SYNTH: {ClipSlotSetting.PATTERN: FIGURE, ClipSlotSetting.CHAINS: [CHAIN]}}}])
    data[chords_plugin.SECTION] = {AUTO: settings}
    data[Section.CHAINS] = {CHAIN: [{chords_plugin.NAME: AUTO}]}
    return pitches(data)[test_follow_chords.SYNTH]


class TestAutoChord(unittest.TestCase):

    def test_from_scale_builds_the_triad_the_scale_builds_on_each_note(self):
        self.assertEqual(chorded(), [[test_follow_chords.C, test_follow_chords.E, test_follow_chords.G], [test_follow_chords.D, test_follow_chords.F, test_follow_chords.A], [test_follow_chords.B, test_follow_chords.D + test_follow_chords.OCTAVE_UP, test_follow_chords.F + test_follow_chords.OCTAVE_UP], [test_follow_chords.C, test_follow_chords.E, test_follow_chords.G]])

    def test_a_fixed_chord_is_built_on_the_note_whatever_the_scale(self):
        self.assertEqual(chorded(chord=auto_chord.MINOR)[0], [test_follow_chords.C, E_FLAT, test_follow_chords.G])
        self.assertEqual(chorded(chord=auto_chord.AUGMENTED)[0], [test_follow_chords.C, test_follow_chords.E, G_SHARP])
        self.assertEqual(chorded(chord=auto_chord.DIMINISHED)[0], [test_follow_chords.C, E_FLAT, F_SHARP])
        self.assertEqual(chorded(chord=auto_chord.POWER)[0], [test_follow_chords.C, test_follow_chords.G, test_follow_chords.C + test_follow_chords.OCTAVE_UP])

    def test_note_on_top_ends_the_chord_on_the_note(self):
        self.assertEqual(chorded(on_top=True)[0], [test_follow_chords.E - test_follow_chords.OCTAVE_UP, test_follow_chords.G - test_follow_chords.OCTAVE_UP, test_follow_chords.C])

    def test_a_note_outside_the_scale_stays_a_single_note_and_a_written_chord_is_left_alone(self):
        played = chorded(figure_rows={Row.ACCIDENTAL: [None, None, None, Accidental.SHARP], Row.CHORD: [test_follow_chords.TRIAD, None, None, None]})
        self.assertEqual(played[0], [test_follow_chords.C, test_follow_chords.E, test_follow_chords.G])
        self.assertEqual(played[3], test_follow_chords.C + 1)
