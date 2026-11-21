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

"""The corpus layer of internal_tools/analysis_and_generation/, one quick check of its main path: a piece becomes the analyzers notes part by part with drums apart. A research tool fails loudly when it is run, so one check is enough (.claude/TESTING.md)."""

import os
import sys
import unittest

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir, 'internal_tools', 'analysis_and_generation')
sys.path.insert(0, TOOLS)
from corpus.piece import CorpusNote, Piece  # noqa: E402


DRUM_PART = 'kit'
BEATS = 4


class TestReading(unittest.TestCase):

    def test_a_piece_becomes_the_analyzers_notes_part_by_part_with_drums_apart(self):
        notes = (CorpusNote(start=0, length=1, pitch=60), CorpusNote(start=1, length=1, pitch=62), CorpusNote(start=0, length=0.5, pitch=36, part=DRUM_PART))
        performance = Piece(source='lakh-clean', identity='made up', notes=notes, drum_parts=frozenset({DRUM_PART})).performance()
        self.assertEqual(len(performance.tracks), 2)
        self.assertEqual([track.drum for track in performance.tracks], [False, True])
        self.assertEqual(float(performance.length), BEATS)


if __name__ == '__main__':
    unittest.main()
