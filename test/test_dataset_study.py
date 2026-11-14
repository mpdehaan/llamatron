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

"""The dataset study's readers, on small examples written here, needing neither the network nor the fetched data: a Billboard
annotation's chords as degrees and its sections, a rock corpus harmony file expanded, a jazz solo's measures and a drum
performance's swing and ghost notes."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

import mido

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, 'internal_tools', 'analysis_and_generation')
sys.path.insert(0, TOOLS)
import dataset_study  # noqa: E402

C = 0
G = 7
BILLBOARD = '''# title: Made Up
# artist: Nobody
# metre: 4/4
# tonic: G

0.0\tsilence
0.3\tA, intro, | G:maj | G:maj |, (guitar)
5.4\tB, verse, | G:maj | C:maj | D:maj | E:min |, (voice
15.8\tC, solo, | C:maj | Bb:maj | G:maj | G:maj |, (guitar)
'''
HARMONY = '''% made up
VP: I IV | V I |
Ch: IV | V |
S: [G] $VP*2 $Ch
'''
TICKS = 480
CLOSED_HAT = 42
SNARE = 38
KICK = 36
GHOST = 25
LOUD = 100
SWUNG_OFFBEAT = 2 / 3
BEATS = 16


class TestBillboard(unittest.TestCase):

    def test_a_chord_is_its_degree_in_the_key_and_minor_is_lower_case(self):
        self.assertEqual(dataset_study.chord_degree(chord='D:maj', tonic=G), 'V')
        self.assertEqual(dataset_study.chord_degree(chord='E:min7', tonic=G), 'vi')
        self.assertEqual(dataset_study.chord_degree(chord='Bb:maj', tonic=C), 'bVII')
        self.assertIsNone(dataset_study.chord_degree(chord='N', tonic=C))

    def test_a_section_label_is_a_lower_case_word(self):
        self.assertTrue(dataset_study.is_section_label('pre-chorus'))
        self.assertFalse(dataset_study.is_section_label('(guitar)'))
        self.assertFalse(dataset_study.is_section_label('A'))
        self.assertFalse(dataset_study.is_section_label('silence'))

    def test_a_song_is_read_as_its_tonic_sections_and_bars(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'salami_chords.txt'
            path.write_text(BILLBOARD)
            tonic, sections, bars = dataset_study.billboard_song(path)
        self.assertEqual(tonic, G)
        self.assertEqual(sections, ['intro', 'verse', 'solo'])
        self.assertEqual(bars[3], ['IV'])
        self.assertEqual(bars[-3], ['bIII'])


class TestRockCorpus(unittest.TestCase):

    def test_the_rules_expand_from_s_with_their_repeats(self):
        self.assertEqual(dataset_study.expanded_rules(HARMONY), ['I', 'IV', 'V', 'I', 'I', 'IV', 'V', 'I', 'IV', 'V'])
        self.assertEqual(dataset_study.numeral_root('bVII7'), 'bVII')
        self.assertEqual(dataset_study.numeral_root('vi64'), 'vi')


class TestJazzSolo(unittest.TestCase):

    def test_a_solo_is_measured_by_density_steps_range_space_and_loudness(self):
        notes = [(beat * 0.5, 60 + (beat % 3), 0.25, 70.0 + beat) for beat in range(16)]
        measured = dataset_study.solo_measures(notes=notes, beats=8)
        self.assertEqual(measured['density'], 2.0)
        self.assertEqual(measured['steps'], 1.0)
        self.assertGreater(measured['space'], 0.4)
        self.assertGreater(measured['dynamics'], 0)
        self.assertIsNone(dataset_study.solo_measures(notes=notes[:1], beats=8))


class TestDrums(unittest.TestCase):

    def test_swung_hats_and_ghosted_snares_are_measured(self):
        song = mido.MidiFile(ticks_per_beat=TICKS)
        track = mido.MidiTrack()
        song.tracks.append(track)
        events = []
        for beat in range(BEATS):
            events.append((beat * TICKS, CLOSED_HAT, LOUD))
            events.append((int((beat + SWUNG_OFFBEAT) * TICKS), CLOSED_HAT, LOUD))
            events.append((beat * TICKS, SNARE if beat % 2 else KICK, LOUD))
            events.append((int((beat + 0.75) * TICKS), SNARE, GHOST))
        now = 0
        for time, note, velocity in sorted(events):
            track.append(mido.Message('note_on', note=note, velocity=velocity, time=time - now, channel=9))
            now = time
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'groove.mid'
            song.save(str(path))
            measured = dataset_study.drum_measures(path)
        self.assertAlmostEqual(measured['swing'], SWUNG_OFFBEAT, places=2)
        self.assertGreater(measured['ghosts'], 0.5)
        self.assertEqual(measured['ride'], 0.0)


if __name__ == '__main__':
    unittest.main()
