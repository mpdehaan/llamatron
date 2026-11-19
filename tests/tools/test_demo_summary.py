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
"""Tests of internal_tools/demo_summary.py: every column it names is a feature the feature report knows, the hello world demo's row reads as the set does, and the table lines up."""

import contextlib
import csv
import importlib.util
import io
import pathlib
import unittest

from llamatron.composition.setlist_reader import file_stem
from llamatron.tui import drawing
from llamatron.tui.document import Document
from llamatron.tui.text import clock

SCRIPT = pathlib.Path(__file__).resolve().parent.parent.parent / 'internal_tools' / 'demo_summary.py'
MODULE_NAME = 'demo_summary'
HELLO_WORLD = 'examples/learning/01_hello_world.yml'
TIE_DEMO = 'examples/learning/08_tie.yml'
HELLO_WORLD_SECONDS = 3
HELLO_WORLD_SCENES = '3'
HELLO_WORLD_TRACKS = '2'
CHORDS_COLUMN = 'chords'
REGISTERS_COLUMN = 'registers'
HEADING_LINES = 2
LEARNING_FOLDER = 'examples/learning'
# How many of the learning demos the test of what each introduces reads.
DEMOS_TRIED = 4
A_SECTION = '## A Demo: `01_a_demo.yml`'
HEADING_MARK = '#'
ANCHOR_JOIN = '-'
ANCHOR_KEPT = ' -'


def load_script():
    """Load the tool as a module, since internal_tools/ is not a package."""
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HIP_HOP = 'Hip hop'
HIP_HOP_PAGE = 'HIP_HOP.md'
CHILDRENS = "Children's"
CHILDRENS_PAGE = 'CHILDRENS.md'


class TestDemoSummary(unittest.TestCase):

    def setUp(self):
        self.tool = load_script()
        self.features = self.tool.load_features()

    def test_every_feature_a_column_names_is_one_the_feature_report_knows(self):
        self.assertEqual(self.tool.unknown_features(self.features), [])

    def cell(self, *, row, heading):
        return row[self.tool.headings().index(heading)]

    def test_the_hello_world_row_reads_as_the_set_does_with_a_check_mark_for_a_feature_used_and_nothing_for_one_not(self):
        row = self.tool.summary_row(path=HELLO_WORLD, features=self.features)
        self.assertEqual(self.cell(row=row, heading=self.tool.DESCRIPTION_HEADING), Document.load(HELLO_WORLD).setlist().get_description())
        self.assertEqual(self.cell(row=row, heading=self.tool.LENGTH_HEADING), clock(HELLO_WORLD_SECONDS))
        self.assertEqual(self.cell(row=row, heading=self.tool.SCENES_HEADING), HELLO_WORLD_SCENES)
        self.assertEqual(self.cell(row=row, heading=self.tool.TRACKS_HEADING), HELLO_WORLD_TRACKS)
        self.assertEqual(self.cell(row=row, heading=CHORDS_COLUMN), self.tool.USED)
        self.assertEqual(self.cell(row=row, heading=REGISTERS_COLUMN), self.tool.UNUSED)
        self.assertEqual(self.tool.UNUSED, drawing.NOTHING)

    def test_a_set_that_uses_a_registers_feature_is_marked_in_that_column(self):
        row = self.tool.summary_row(path=TIE_DEMO, features=self.features)
        self.assertEqual(self.cell(row=row, heading=REGISTERS_COLUMN), self.tool.USED)

    def printed(self, *argv):
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            self.assertEqual(self.tool.main(argv=list(argv)), self.tool.SUCCESS)
        return printed.getvalue().splitlines()

    def test_comma_separated_values_have_the_headings_and_a_row_per_set_that_a_reader_of_them_takes_apart(self):
        rows = list(csv.reader(self.printed(self.tool.OPTION_CSV, HELLO_WORLD, TIE_DEMO)))
        self.assertEqual(rows[0], self.tool.headings())
        self.assertEqual(rows[1:], [self.tool.summary_row(path=path, features=self.features) for path in [HELLO_WORLD, TIE_DEMO]])

    def test_the_features_tool_writes_a_row_per_feature_and_a_column_per_set(self):
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            self.features.main(argv=[self.tool.OPTION_CSV, HELLO_WORLD, TIE_DEMO])
        rows = list(csv.reader(printed.getvalue().splitlines()))
        self.assertEqual(rows[0], [self.features.CSV_FEATURE, self.features.short_name(HELLO_WORLD), self.features.short_name(TIE_DEMO)])
        self.assertEqual([row[0] for row in rows[1:]], [feature for feature, _ in self.features.FEATURES])
        used = self.features.features_used(TIE_DEMO)
        self.assertEqual([row[2] == self.features.CSV_USED for row in rows[1:]], [feature in used for feature, _ in self.features.FEATURES])

    def test_the_plain_table_has_a_heading_a_rule_and_a_row_per_set_with_every_heading_over_its_column(self):
        lines = self.printed(HELLO_WORLD, TIE_DEMO)
        self.assertEqual(len(lines), HEADING_LINES + 2)
        for heading in self.tool.headings():
            self.assertIn(heading, lines[0])
        self.assertEqual(set(lines[1].replace(self.tool.COLUMN_GAP, drawing.NOTHING)), {self.tool.RULE})
        self.assertTrue(lines[2].startswith(self.features.short_name(HELLO_WORLD)))
        self.assertEqual(len(lines[1]), max(len(line) for line in lines))

    def test_the_bordered_table_rules_every_row_and_edges_every_cell(self):
        lines = self.printed(self.tool.OPTION_FORMAT, self.tool.FORMAT_ASCII, HELLO_WORLD, TIE_DEMO)
        rule = lines[0]
        self.assertTrue(rule.startswith(self.tool.CORNER) and rule.endswith(self.tool.CORNER))
        self.assertEqual(lines[::2], [rule] * (len(lines) // 2 + 1))
        self.assertEqual(len({len(line) for line in lines}), 1)
        for line in lines[1::2]:
            self.assertEqual(line.count(self.tool.EDGE), len(self.tool.headings()) + 1)
        self.assertEqual(rule.count(self.tool.CORNER), len(self.tool.headings()) + 1)

    def test_the_markdown_table_has_a_heading_an_alignment_rule_and_a_row_per_set(self):
        lines = self.printed(self.tool.OPTION_FORMAT, self.tool.FORMAT_MARKDOWN, HELLO_WORLD, TIE_DEMO)
        self.assertEqual(len(lines), HEADING_LINES + 2)
        cells = [cell.strip() for cell in lines[0].strip(self.tool.EDGE).split(self.tool.EDGE)]
        self.assertEqual(cells, self.tool.headings())
        alignments = [cell.strip() for cell in lines[1].strip(self.tool.EDGE).split(self.tool.EDGE)]
        left = len(self.tool.LEFT_HEADINGS)
        numbers = len(self.tool.NUMBER_HEADINGS)
        self.assertEqual(alignments[:left], [self.tool.MARKDOWN_RULE] * left)
        self.assertEqual(alignments[left:left + numbers], [self.tool.MARKDOWN_RIGHT] * numbers)
        self.assertEqual(set(alignments[left + numbers:]), {self.tool.MARKDOWN_CENTER})
        self.assertIn(self.tool.USED, lines[2])

    def test_the_table_in_the_demos_document_is_current(self):
        lines = self.printed(self.tool.OPTION_CHECK)
        self.assertEqual(lines, [self.tool.MSG_UP_TO_DATE.format(path=self.tool.DEMOS_DOCUMENT.relative_to(self.tool.ROOT))])
        text = self.tool.DEMOS_DOCUMENT.read_text()
        self.assertLess(text.index(self.tool.MARKER_START), text.index(self.tool.MARKER_END))
        overview = text[text.index(self.tool.MARKER_START):text.index(self.tool.MARKER_END)]
        # The page lists no demo: it links the Tutorial Demos page and each genre's page, and each demo's summary, on its genre's page, holds its key, its tempo and the marks of the features it uses.
        self.assertNotIn(Document.load(HELLO_WORLD).setlist().get_description(), overview)
        self.assertNotIn(self.tool.USED, overview)
        self.assertIn(self.tool.DEMO_PAGE_LINK.format(page=self.tool.TUTORIAL_PAGE), overview)
        page = self.tool.DEMO_PAGES / self.tool.genre_page(self.tool.genre_of(HELLO_WORLD))
        self.assertIn(self.tool.DEMO_PAGE_LINK.format(page=page.name), overview)
        stem = file_stem(HELLO_WORLD)
        summary = page.read_text().split(self.tool.SUMMARY_START.format(stem=stem))[1].split(self.tool.SUMMARY_END.format(stem=stem))[0]
        self.assertIn(pathlib.Path(HELLO_WORLD).as_posix(), summary)
        key, tempo = self.tool.starting_key_and_tempo(HELLO_WORLD)
        self.assertIn(key, summary)
        self.assertIn(str(tempo), summary)

    def test_a_demo_summary_marks_only_the_features_the_demo_uses(self):
        features = self.tool.load_features()
        row = self.tool.summary_row(path=HELLO_WORLD, features=features)
        table = self.tool.feature_table(row)
        used = [heading for (heading, _), cell in zip(self.tool.FEATURE_COLUMNS, row[len(self.tool.LEFT_HEADINGS) + len(self.tool.NUMBER_HEADINGS):]) if cell == self.tool.USED]
        if used:
            self.assertEqual(table[0].strip(self.tool.EDGE).split(self.tool.EDGE), [self.tool.MARKDOWN_CELL.format(cell=heading) for heading in used])
        else:
            self.assertEqual(table, [self.tool.NO_FEATURES])

    def test_a_genre_names_its_page(self):
        self.assertEqual(self.tool.genre_page(HIP_HOP), HIP_HOP_PAGE)
        self.assertEqual(self.tool.genre_page(CHILDRENS), CHILDRENS_PAGE)


class TestFeatureLinks(unittest.TestCase):
    """Each checkmark links to the page that explains its feature, and the Tutorial Demos page says what each demo is the first to use."""

    def setUp(self):
        self.tool = load_script()
        self.features = self.tool.load_features()

    def test_every_link_names_a_feature_a_page_that_exists_and_a_heading_of_that_page(self):
        known = {name for name, _ in self.features.FEATURES}
        for name, link in self.tool.FEATURE_LINKS.items():
            self.assertIn(name, known)
            page, _, anchor = link.partition(self.tool.LINK_ANCHOR)
            path = (self.tool.DEMO_PAGES / page).resolve()
            self.assertTrue(path.is_file(), link)
            if anchor:
                headings = [as_anchor(line) for line in path.read_text(encoding=self.tool.FILE_ENCODING).splitlines() if line.startswith(HEADING_MARK)]
                self.assertIn(anchor, headings, link)

    def test_every_feature_a_column_marks_has_a_link(self):
        for _, names in self.tool.FEATURE_COLUMNS:
            for name in names:
                self.assertIn(name, self.tool.FEATURE_LINKS)

    def test_a_checkmark_links_to_the_first_feature_of_its_column_the_set_uses_and_is_plain_when_what_is_used_is_not_known(self):
        heading, names = next((heading, names) for heading, names in self.tool.FEATURE_COLUMNS if len(names) > 1)
        last = names[-1]
        self.assertEqual(self.tool.used_mark(names=names, used={last}), self.tool.USED_LINK.format(mark=self.tool.USED, link=self.tool.FEATURE_LINKS[last]))
        self.assertEqual(self.tool.used_mark(names=names, used=set(names)), self.tool.USED_LINK.format(mark=self.tool.USED, link=self.tool.FEATURE_LINKS[names[0]]))
        self.assertEqual(self.tool.used_mark(names=names, used=None), self.tool.USED)

    def test_a_learning_demo_introduces_only_what_no_demo_before_it_used_and_the_page_shows_a_linked_table_after_it(self):
        paths = [str(path) for path in sorted(pathlib.Path(LEARNING_FOLDER).glob(self.tool.STAR + self.tool.SET_SUFFIX))][:DEMOS_TRIED]
        rows = self.tool.rows_for(paths=paths, features=self.features)
        new = self.tool.new_features(paths=paths, rows=rows)
        seen = []
        for path, row in zip(paths, rows):
            used = self.tool.columns_used(row)
            self.assertEqual(new[pathlib.Path(path).name], [heading for heading in used if heading not in seen])
            seen += used
        first = pathlib.Path(paths[0]).name
        self.assertTrue(new[first])
        section = self.tool.with_new_features(section=A_SECTION, cells=rows[0], used=self.features.features_used(paths[0]), new=new[first])
        self.assertTrue(section.startswith(A_SECTION))
        self.assertIn(self.tool.NEW_FEATURES_TITLE, section)
        self.assertIn(self.tool.USED_LINK.format(mark=self.tool.USED, link=self.tool.FEATURE_LINKS[CHORDS_COLUMN]), section)
        self.assertEqual(self.tool.with_new_features(section=A_SECTION, cells=rows[0], used=None, new=[]), A_SECTION)


def as_anchor(heading):
    """Return the anchor a Markdown heading gets: its words in lower case, joined with dashes, without its marks."""
    words = ''.join(letter for letter in heading.lstrip(HEADING_MARK).strip().lower() if letter.isalnum() or letter in ANCHOR_KEPT)
    return words.replace(' ', ANCHOR_JOIN)
