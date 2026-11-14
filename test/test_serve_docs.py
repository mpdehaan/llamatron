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

"""Tests internal_tools/serve_docs.py, which serves the built documentation website as GitHub Pages does."""

import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'internal_tools'))

import serve_docs  # noqa: E402
from serve_docs import BASE, file_for, goes_to_base  # noqa: E402

PAGE = 'PATTERNS'
ASSET = 'assets/app.js'
TEXT = 'built'


class TestFileFor(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.folder.name)
        for name in (serve_docs.INDEX, PAGE + serve_docs.PAGE_SUFFIX, ASSET):
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            (self.root / name).write_text(TEXT)
        self.addCleanup(self.folder.cleanup)

    def found(self, path):
        return file_for(path=path, root=self.root)

    def test_the_base_is_the_front_page(self):
        self.assertEqual(self.found(BASE), (self.root / serve_docs.INDEX).resolve())

    def test_a_page_is_found_with_or_without_its_suffix(self):
        page = (self.root / (PAGE + serve_docs.PAGE_SUFFIX)).resolve()
        self.assertEqual(self.found(BASE + PAGE), page)
        self.assertEqual(self.found(BASE + PAGE + serve_docs.PAGE_SUFFIX), page)

    def test_a_query_or_a_fragment_is_ignored(self):
        page = (self.root / (PAGE + serve_docs.PAGE_SUFFIX)).resolve()
        self.assertEqual(self.found(BASE + PAGE + '?x=1#heading'), page)

    def test_an_asset_is_found(self):
        self.assertEqual(self.found(BASE + ASSET), (self.root / ASSET).resolve())

    def test_a_missing_page_is_not_found(self):
        self.assertIsNone(self.found(BASE + 'NOWHERE'))

    def test_nothing_outside_the_base_or_the_folder_is_served(self):
        self.assertIsNone(self.found('/' + PAGE))
        self.assertIsNone(self.found(BASE + '../secret'))
        self.assertIsNone(self.found(BASE + '%2e%2e/secret'))


class TestGoesToBase(unittest.TestCase):

    def test_the_top_and_the_base_without_its_slash_go_to_the_base(self):
        self.assertTrue(goes_to_base('/'))
        self.assertTrue(goes_to_base(BASE.rstrip('/')))

    def test_a_page_stays_where_it_is(self):
        self.assertFalse(goes_to_base(BASE))
        self.assertFalse(goes_to_base(BASE + PAGE))


class TestTheBuiltSite(unittest.TestCase):

    def test_the_committed_site_has_its_front_page_and_a_page_for_every_chapter(self):
        self.assertIsNotNone(file_for(path=BASE, root=serve_docs.SITE))
        for chapter in sorted((ROOT / 'docs').glob('*.md')):
            with self.subTest(chapter=chapter.name):
                self.assertIsNotNone(file_for(path=BASE + chapter.stem, root=serve_docs.SITE))


if __name__ == '__main__':
    unittest.main()
