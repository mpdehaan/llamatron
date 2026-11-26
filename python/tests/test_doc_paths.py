# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Every source, test, tool, example and screenshot path the documents name exists.

The documents for Claude and for people name files in backticks, like `src/llamatron/model/values/note.py`
or `internal_tools/compare_exports.py`. When a module moves, those names go stale unless something notices,
so this test reads every document and checks that each such path is a real file, so that a rename
has to carry its documentation with it.
"""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
DOCUMENTS = [
    ROOT / 'CLAUDE.md',
    ROOT / 'README.md',
    *sorted((ROOT / 'docs').rglob('*.md')),
    *sorted((ROOT / 'developer_docs').rglob('*.md')),
    # The synthesis notes stay on this computer only, out of git, so no path in them is held.
    *sorted(path for path in (ROOT / '.claude').rglob('*.md') if 'synthesis' not in path.parts),
]
# The guide, whose table of guides links every chapter in docs/.
DOCS = ROOT / 'docs'
GUIDE = DOCS / 'GUIDE.md'
GUIDE_LINK = ']({name})'
TABLE_ROW = '|'
# A path in backticks that starts in one of the repository's folders and ends in a file suffix.
PATH_IN_BACKTICKS = re.compile(r'`((?:src|test|internal_tools|user_scripts|examples|docs|developer_docs|python)/[A-Za-z0-9_./-]+\.(?:py|rs|toml|yml|svg|sh|md|mid|als|ly))`')
ENCODING = 'utf-8'
# Files the documents name that git ignores, so a new clone has none: Claude's own queue and its plans with their status, kept on one computer.
KEPT_OUT_OF_GIT = ('.claude/planning/DESIGNS.md', '.claude/planning/WIZARD_DESIGNS.md')
USER_SCRIPTS = ROOT / 'user_scripts'
USER_SCRIPTS_GUIDE = ROOT / 'docs' / 'USER_SCRIPTS.md'
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
                if path in KEPT_OUT_OF_GIT:
                    continue
                with self.subTest(document=document.relative_to(ROOT), path=path):
                    self.assertTrue((ROOT / path).is_file(), path)

    def test_the_status_files_are_ignored_by_git(self):
        ignored = (ROOT / '.gitignore').read_text(encoding=ENCODING).splitlines()
        for path in KEPT_OUT_OF_GIT:
            self.assertIn(path, ignored)

    def test_the_documents_name_some_paths(self):
        # If the pattern stopped matching, the test above would pass by checking nothing.
        self.assertGreater(len(paths_named_in(ROOT / 'CLAUDE.md')), 0)


class TestEveryChapterIsInTheGuide(unittest.TestCase):
    """Every guide in docs/ and its subfolders is linked from a row of one of docs/GUIDE.md's tables, so that the guide is the way in to all of them and the website's sidebar lists them."""

    def test_every_markdown_file_in_docs_is_linked_from_a_table_row_of_the_guide(self):
        rows = [line for line in GUIDE.read_text(encoding='utf-8').splitlines() if line.startswith(TABLE_ROW)]
        chapters = sorted(path.relative_to(DOCS).as_posix() for path in DOCS.rglob('*.md') if path != GUIDE)
        self.assertTrue(chapters)
        for name in chapters:
            with self.subTest(chapter=name):
                self.assertTrue(any(GUIDE_LINK.format(name=name) in row for row in rows))


class TestEveryUserScriptIsDescribed(unittest.TestCase):
    """docs/USER_SCRIPTS.md describes every script in user_scripts/, so that a new script can't arrive unexplained."""

    def test_every_script_has_a_section_in_user_scripts_md(self):
        text = USER_SCRIPTS_GUIDE.read_text(encoding=ENCODING)
        scripts = sorted(path.name for path in USER_SCRIPTS.glob(SCRIPT_FILES))
        self.assertTrue(scripts)
        for name in scripts:
            with self.subTest(script=name):
                self.assertIn(SCRIPT_HEADING.format(name=name), text)

    def test_every_script_says_what_it_does(self):
        for path in sorted(USER_SCRIPTS.glob(SCRIPT_FILES)):
            with self.subTest(script=path.name):
                self.assertIn(WHAT_IT_DOES, path.read_text(encoding=ENCODING))


if __name__ == '__main__':
    unittest.main()

