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

"""internal_tools/serve_docs.py, one quick check of its main path: a page is found with or without its suffix. A tool fails loudly when it is run, so one check is enough (.claude/TESTING.md)."""

import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'internal_tools'))

import serve_docs  # noqa: E402
from serve_docs import file_for  # noqa: E402

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

    def test_a_page_is_found_with_or_without_its_suffix(self):
        page = (self.root / (PAGE + serve_docs.PAGE_SUFFIX)).resolve()
        self.assertEqual(self.found(serve_docs.BASE + PAGE), page)
        self.assertEqual(self.found(serve_docs.BASE + PAGE + serve_docs.PAGE_SUFFIX), page)

if __name__ == '__main__':
    unittest.main()
