# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The chord files' readers of internal_tools/analysis_and_generation/, one quick check of its main path: a song is read as its tonic sections and bars. A research tool fails loudly when it is run, so one check is enough (.claude/TESTING.md)."""

from corpus import chord_files
from pathlib import Path
import tempfile
import unittest

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


class TestBillboard(unittest.TestCase):

    def test_a_song_is_read_as_its_tonic_sections_and_bars(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'salami_chords.txt'
            path.write_text(BILLBOARD)
            tonic, sections, bars = chord_files.billboard_song(path)
        self.assertEqual(tonic, G)
        self.assertEqual(sections, ['intro', 'verse', 'solo'])
        self.assertEqual(bars[3], ['IV'])
        self.assertEqual(bars[-3], ['bIII'])


if __name__ == '__main__':
    unittest.main()
