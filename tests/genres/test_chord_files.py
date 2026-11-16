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

"""The corpus's chord-file readers, on small examples written here, needing neither the network nor the fetched data: a chart
annotation's chords as degrees and its sections, and a rock corpus harmony file expanded."""

import tempfile
import unittest
from pathlib import Path

from corpus import chord_files

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


class TestBillboard(unittest.TestCase):

    def test_a_chord_is_its_degree_in_the_key_and_minor_is_lower_case(self):
        self.assertEqual(chord_files.chord_degree(chord='D:maj', tonic=G), 'V')
        self.assertEqual(chord_files.chord_degree(chord='E:min7', tonic=G), 'vi')
        self.assertEqual(chord_files.chord_degree(chord='Bb:maj', tonic=C), 'bVII')
        self.assertIsNone(chord_files.chord_degree(chord='N', tonic=C))

    def test_a_section_label_is_a_lower_case_word(self):
        self.assertTrue(chord_files.is_section_label('pre-chorus'))
        self.assertFalse(chord_files.is_section_label('(guitar)'))
        self.assertFalse(chord_files.is_section_label('A'))
        self.assertFalse(chord_files.is_section_label('silence'))

    def test_a_song_is_read_as_its_tonic_sections_and_bars(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'salami_chords.txt'
            path.write_text(BILLBOARD)
            tonic, sections, bars = chord_files.billboard_song(path)
        self.assertEqual(tonic, G)
        self.assertEqual(sections, ['intro', 'verse', 'solo'])
        self.assertEqual(bars[3], ['IV'])
        self.assertEqual(bars[-3], ['bIII'])


class TestRockCorpus(unittest.TestCase):

    def test_the_rules_expand_from_s_with_their_repeats(self):
        self.assertEqual(chord_files.expanded_rules(HARMONY), ['I', 'IV', 'V', 'I', 'I', 'IV', 'V', 'I', 'IV', 'V'])
        self.assertEqual(chord_files.numeral_root('bVII7'), 'bVII')
        self.assertEqual(chord_files.numeral_root('vi64'), 'vi')


if __name__ == '__main__':
    unittest.main()
