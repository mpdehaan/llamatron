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

"""The corpus fetcher's checks, which need no network: only score files are kept, and no archive member may land outside its
collection's folder. Nothing here fetches anything (.claude/TESTING.md)."""

import os
import sys
import unittest

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, 'internal_tools', 'analysis_and_generation')
sys.path.insert(0, TOOLS)
import fetch_corpus  # noqa: E402

TOP = 'essen-folksong-collection-main'
SCORE = TOP + '/asia/china/han/han0001.krn'
CLIMBING = TOP + '/../../etc/passwd.krn'
ABSOLUTE = '/etc/passwd.krn'
README = TOP + '/README.txt'
YES_ANSWER = 'y'
NO_ANSWER = ''
UNKNOWN_SOURCE = 'no-such-source'


class TestFetchCorpus(unittest.TestCase):

    def test_only_score_files_are_kept(self):
        self.assertTrue(fetch_corpus.is_score(SCORE))
        self.assertFalse(fetch_corpus.is_score(README))

    def test_a_member_lands_under_its_collection_without_the_archive_folder(self):
        self.assertEqual(str(fetch_corpus.safe_member_path(SCORE)), 'asia/china/han/han0001.krn')

    def test_a_member_climbing_out_or_absolute_is_refused(self):
        self.assertIsNone(fetch_corpus.safe_member_path(CLIMBING))
        self.assertIsNone(fetch_corpus.safe_member_path(ABSOLUTE))
        self.assertIsNone(fetch_corpus.safe_member_path(TOP))

    def test_every_collection_names_how_it_comes(self):
        for name, kind, repository, branch in fetch_corpus.COLLECTIONS:
            self.assertIn(kind, (fetch_corpus.ARCHIVE, fetch_corpus.FILES), name)
            self.assertTrue(repository and branch, name)

    def test_every_dataset_names_how_it_comes_its_limit_and_its_terms(self):
        for name, kind, url, endings, megabytes, terms in fetch_corpus.DATASETS:
            self.assertIn(kind, (fetch_corpus.ARCHIVE, fetch_corpus.ZIP, fetch_corpus.SINGLE, fetch_corpus.DATAVERSE, fetch_corpus.MUTOPIA), name)
            self.assertTrue(url and endings and terms, name)
            self.assertGreater(megabytes, 0, name)

    def test_every_source_is_in_one_category_with_a_size_and_terms(self):
        listed = [name for _, _, names in fetch_corpus.CATEGORIES for name in names]
        self.assertEqual(sorted(listed), sorted(fetch_corpus.every_name()))
        for name in listed:
            self.assertGreater(fetch_corpus.megabytes_of(name), 0, name)
            self.assertTrue(fetch_corpus.terms_of(name), name)

    def test_only_the_categories_answered_yes_are_chosen(self):
        answers = iter([YES_ANSWER] + [NO_ANSWER] * (len(fetch_corpus.CATEGORIES) - 1))
        said = []
        chosen = fetch_corpus.asked(ask=lambda question: next(answers), say=said.append)
        self.assertEqual(tuple(chosen), fetch_corpus.CATEGORIES[0][2])
        self.assertTrue(any(fetch_corpus.CATEGORIES[-1][0] in line for line in said))

    def test_nobody_there_to_answer_chooses_nothing(self):
        def nobody(question):
            raise EOFError
        self.assertEqual(fetch_corpus.asked(ask=nobody, say=lambda line: None), [])

    def test_a_source_nobody_knows_is_refused_before_anything_is_fetched(self):
        with self.assertRaises(SystemExit):
            fetch_corpus.main(argv=[UNKNOWN_SOURCE])

    def test_only_the_kept_endings_are_kept_and_hidden_files_never(self):
        self.assertTrue(fetch_corpus.kept('song.MID', endings=('.mid',)))
        self.assertFalse(fetch_corpus.kept('._song.mid', endings=('.mid',)))
        self.assertFalse(fetch_corpus.kept('song.wav', endings=('.mid',)))


if __name__ == '__main__':
    unittest.main()
