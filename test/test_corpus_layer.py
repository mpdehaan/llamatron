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

"""The corpus layer for meta-analysis, on its own parts, needing neither the network nor the fetched data: every source's terms,
the opt-ins they allow and the credits they owe, an even sample, the Session's keys, and a piece becoming the analyzer's notes."""

import os
import sys
import unittest

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, 'internal_tools', 'analysis_and_generation')
sys.path.insert(0, TOOLS)
from corpus.piece import CorpusNote, Piece  # noqa: E402
from corpus.readers import READERS, session_key, spread  # noqa: E402
from corpus.identities import identity_of  # noqa: E402
from corpus.sources import SOURCES, SOURCES_BY_NAME, credits  # noqa: E402


DRUM_PART = 'kit'
BEATS = 4


class TestSources(unittest.TestCase):

    def test_every_source_has_terms_and_a_reader(self):
        for source in SOURCES:
            self.assertIn(source.name, READERS, source.name)
            self.assertTrue(source.terms.name, source.name)
            if source.terms.attribution:
                self.assertTrue(source.terms.credit, source.name)

    def test_credits_are_owed_once_and_not_for_the_public_domain(self):
        owed = credits(['weimar-jazz', 'weimar-jazz', 'billboard'])
        self.assertEqual(owed, [SOURCES_BY_NAME['weimar-jazz'].terms.credit])


class TestReading(unittest.TestCase):

    def test_a_sample_is_spread_evenly_and_keeps_its_order(self):
        self.assertEqual(spread(range(10), limit=5), [0, 2, 4, 6, 8])
        self.assertEqual(spread(range(3), limit=5), [0, 1, 2])

    def test_the_sessions_mode_becomes_an_abc_key(self):
        self.assertEqual(session_key('Edorian'), 'Edor')
        self.assertEqual(session_key('Gmajor'), 'Gmaj')
        self.assertEqual(session_key(None), 'C')

    def test_a_piece_becomes_the_analyzers_notes_part_by_part_with_drums_apart(self):
        notes = (CorpusNote(start=0, length=1, pitch=60), CorpusNote(start=1, length=1, pitch=62), CorpusNote(start=0, length=0.5, pitch=36, part=DRUM_PART))
        performance = Piece(source='lakh-clean', identity='made up', notes=notes, drum_parts=frozenset({DRUM_PART})).performance()
        self.assertEqual(len(performance.tracks), 2)
        self.assertEqual([track.drum for track in performance.tracks], [False, True])
        self.assertEqual(float(performance.length), BEATS)


class TestIdentities(unittest.TestCase):
    """One identity for each creator across sources, whatever the spelling, code or article."""

    def test_a_composer_is_one_person_by_code_full_name_or_surname(self):
        keys = {identity_of(name)[0] for name in ('DebussyC', 'Claude Debussy', 'debussy')}
        self.assertEqual(len(keys), 1)
        self.assertEqual(identity_of('DebussyC')[1], 'Claude Debussy')

    def test_two_bachs_stay_apart(self):
        self.assertNotEqual(identity_of('BachCPE')[0], identity_of('BachJS')[0])
        self.assertEqual(identity_of('Johann Sebastian Bach')[0], identity_of('BachJS')[0])

    def test_a_band_is_one_band_with_or_without_its_article_and_accents(self):
        self.assertEqual(identity_of('The Beatles')[0], identity_of('Beatles')[0])
        self.assertEqual(identity_of('Beyoncé')[0], identity_of('Beyonce')[0])
        self.assertEqual(identity_of(None), (None, None))


if __name__ == '__main__':
    unittest.main()
