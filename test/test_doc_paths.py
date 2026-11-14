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
"""Every source, test, tool, example and screenshot path the documents name exists.

The documents for Claude and for people name files in backticks, like `src/llamatron/music/note.py`
or `internal_tools/compare_exports.py`. When a module moves, those names go stale unless something notices,
so this test reads every document and checks that each such path is a real file, so that a rename
has to carry its documentation with it.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = [
    ROOT / 'CLAUDE.md',
    ROOT / 'GUIDE.md',
    ROOT / 'INSTALL.md',
    ROOT / 'README.md',
    *sorted((ROOT / 'dev_notes').glob('*.md')),
    *sorted((ROOT / 'docs').rglob('*.md')),
    *sorted((ROOT / '.claude').glob('*.md')),
]
# The guide, whose table of guides links every chapter in docs/, the user's rule.
GUIDE = ROOT / 'GUIDE.md'
DOCS = ROOT / 'docs'
GUIDE_LINK = '](docs/{name})'
TABLE_ROW = '|'
# A path in backticks that starts in one of the repository's folders and ends in a file suffix.
PATH_IN_BACKTICKS = re.compile(r'`((?:src|test|internal_tools|user_scripts|examples|docs|dev_notes)/[A-Za-z0-9_./-]+\.(?:py|yml|svg|sh|md|mid|als|ly))`')
ENCODING = 'utf-8'
USER_SCRIPTS = ROOT / 'user_scripts'
USER_SCRIPTS_GUIDE = ROOT / 'docs' / 'USER_SCRIPTS.md'
# The genre library's user scripts, kept off the website and out of docs/USER_SCRIPTS.md until the user decides (115 B); they will
# have a documentation page of their own then.
GATED_GENRE_SCRIPTS = ('describe_style.sh',)
SCRIPT_FILES = '*.sh'
SCRIPT_HEADING = '### `{name}`'
WHAT_IT_DOES = '# What it does:'


def paths_named_in(document):
    """Return the repository paths a document names in backticks, in order, without repeats."""
    found = PATH_IN_BACKTICKS.findall(document.read_text(encoding=ENCODING))
    return list(dict.fromkeys(found))


class TestDocumentPaths(unittest.TestCase):

    def test_every_path_the_documents_name_exists(self):
        for document in DOCUMENTS:
            for path in paths_named_in(document):
                with self.subTest(document=document.relative_to(ROOT), path=path):
                    self.assertTrue((ROOT / path).is_file(), path)

    def test_the_documents_name_some_paths(self):
        # If the pattern stopped matching, the test above would pass by checking nothing.
        self.assertGreater(len(paths_named_in(ROOT / 'CLAUDE.md')), 0)


class TestEveryChapterIsInTheGuide(unittest.TestCase):
    """Every guide in docs/ and its subfolders is linked from a row of one of GUIDE.md's tables, the user's rule, so that the guide is the way in to all of them and the website's sidebar lists them."""

    def test_every_markdown_file_in_docs_is_linked_from_a_table_row_of_the_guide(self):
        rows = [line for line in GUIDE.read_text(encoding='utf-8').splitlines() if line.startswith(TABLE_ROW)]
        chapters = sorted(path.relative_to(DOCS).as_posix() for path in DOCS.rglob('*.md'))
        self.assertTrue(chapters)
        for name in chapters:
            with self.subTest(chapter=name):
                self.assertTrue(any(GUIDE_LINK.format(name=name) in row for row in rows))


class TestEveryUserScriptIsDescribed(unittest.TestCase):
    """docs/USER_SCRIPTS.md describes every script in user_scripts/, the user's rule, so that a new script can't arrive unexplained."""

    def test_every_script_has_a_section_in_user_scripts_md(self):
        text = USER_SCRIPTS_GUIDE.read_text(encoding=ENCODING)
        scripts = sorted(path.name for path in USER_SCRIPTS.glob(SCRIPT_FILES) if path.name not in GATED_GENRE_SCRIPTS)
        self.assertTrue(scripts)
        for name in scripts:
            with self.subTest(script=name):
                self.assertIn(SCRIPT_HEADING.format(name=name), text)

    def test_the_gated_genre_scripts_exist_and_stay_off_the_website_for_now(self):
        text = USER_SCRIPTS_GUIDE.read_text(encoding=ENCODING)
        for name in GATED_GENRE_SCRIPTS:
            with self.subTest(script=name):
                self.assertTrue((USER_SCRIPTS / name).is_file())
                self.assertNotIn(SCRIPT_HEADING.format(name=name), text)

    def test_every_script_says_what_it_does(self):
        for path in sorted(USER_SCRIPTS.glob(SCRIPT_FILES)):
            with self.subTest(script=path.name):
                self.assertIn(WHAT_IT_DOES, path.read_text(encoding=ENCODING))


if __name__ == '__main__':
    unittest.main()
