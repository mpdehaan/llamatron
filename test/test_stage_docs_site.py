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

"""Tests internal_tools/stage_docs_site.py, which stages the guide and its chapters for the documentation website."""

import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'internal_tools'))

import stage_docs_site  # noqa: E402

GUIDE_TEXT = """# A guide

## Start Here

| Page | What it covers |
| --- | --- |
| [Concepts](docs/CONCEPTS.md) | The ideas. |
| [Demo Songs](docs/DEMOS.md) | Every demo, with [a link again](docs/CONCEPTS.md). |
| [Arpeggiator](docs/generators/ARPEGGIATOR.md) | One in a subfolder. |

## Objects

| Object | Page |
| --- | --- |
| Patterns | [Patterns](docs/PATTERNS.md) |
| Arrange | [Arrange](docs/ARRANGE.md), with [Tracks](docs/TRACKS.md) |
"""
CHAPTER_TEXT = "See [the guide](../GUIDE.md) and [Scenes](SCENES.md)."
SHOWN_CHAPTER_TEXT = "See [the guide](index.md) and [Scenes](SCENES.md)."
DEEPER_TEXT = "See [the guide](../../GUIDE.md) and [Patterns](../PATTERNS.md)."
SHOWN_DEEPER_TEXT = "See [the guide](../index.md) and [Patterns](../PATTERNS.md)."
GROUP = 'Objects'
INNER_GROUP = 'Melody'
GROUPED_TEXT = """## Generators

| What | Page |
| --- | --- |
| The overview | [Generators](docs/GENERATORS.md) |

### Melody

| What | Page |
| --- | --- |
| Chords one note at a time | [Arpeggiator](docs/generators/ARPEGGIATOR.md) |
"""
# A group whose subheadings are pages: one over the page of its name alone, one over the page of its name and others.
BASICS_TEXT = """## Intro

### Why llamatron

| Page | What |
| --- | --- |
| [Why llamatron](docs/WHY_LLAMATRON.md) | Why |

### Installing

| Page | What |
| --- | --- |
| [Installing](docs/INSTALLING.md) | Installing |
| [FluidSynth](docs/FLUIDSYNTH.md) | FluidSynth |
"""
LEFT_OVER = 'LEFT_OVER.md'
LEFT_OVER_FOLDER = 'old'


class TestStagedPages(unittest.TestCase):

    def test_the_guide_links_its_chapters_beside_it(self):
        shown = stage_docs_site.site_guide(GUIDE_TEXT)
        self.assertIn('[Patterns](PATTERNS.md)', shown)
        self.assertNotIn('](docs/', shown)

    def test_a_chapter_links_the_guide_as_the_front_page_and_keeps_its_other_links(self):
        self.assertEqual(stage_docs_site.site_chapter(text=CHAPTER_TEXT), SHOWN_CHAPTER_TEXT)
        self.assertEqual(stage_docs_site.site_chapter(text=DEEPER_TEXT, depth=1), SHOWN_DEEPER_TEXT)


class TestSidebar(unittest.TestCase):

    def entries(self):
        return stage_docs_site.sidebar(GUIDE_TEXT)

    def test_the_front_page_comes_first_and_a_table_not_grouped_lists_pages_of_their_own(self):
        entries = self.entries()
        self.assertEqual(entries[0][stage_docs_site.LINK], stage_docs_site.FRONT_PAGE_LINK)
        self.assertEqual([entry.get(stage_docs_site.LINK) for entry in entries[1:4]], ['/CONCEPTS', '/DEMOS', '/generators/ARPEGGIATOR'])

    def test_a_grouped_heading_makes_a_group_that_opens_and_closes_each_chapter_once(self):
        group = self.entries()[-1]
        self.assertEqual(group[stage_docs_site.TEXT], GROUP)
        self.assertIs(group[stage_docs_site.COLLAPSED], False)
        self.assertEqual([item[stage_docs_site.LINK] for item in group[stage_docs_site.ITEMS]], ['/PATTERNS', '/ARRANGE', '/TRACKS'])

    def test_a_group_opens_the_page_of_its_name_and_a_subheading_makes_a_group_within(self):
        text = GROUPED_TEXT
        entries = stage_docs_site.sidebar(text)
        group = entries[1]
        self.assertEqual(group[stage_docs_site.LINK], '/GENERATORS')
        inner = group[stage_docs_site.ITEMS][0]
        self.assertEqual(inner[stage_docs_site.TEXT], INNER_GROUP)
        self.assertEqual([item[stage_docs_site.LINK] for item in inner[stage_docs_site.ITEMS]], ['/generators/ARPEGGIATOR'])

    def test_a_subheading_over_its_own_page_alone_is_the_page_and_over_more_opens_its_page(self):
        group = stage_docs_site.sidebar(BASICS_TEXT)[1]
        alone, installing = group[stage_docs_site.ITEMS]
        self.assertEqual(alone, {stage_docs_site.TEXT: 'Why llamatron', stage_docs_site.LINK: '/WHY_LLAMATRON'})
        self.assertEqual(installing[stage_docs_site.LINK], '/INSTALLING')
        self.assertEqual([item[stage_docs_site.LINK] for item in installing[stage_docs_site.ITEMS]], ['/FLUIDSYNTH'])

    def test_the_real_guide_lists_every_chapter_in_docs_and_its_subfolders(self):
        entries = stage_docs_site.sidebar(stage_docs_site.GUIDE.read_text(encoding=stage_docs_site.ENCODING))
        self.assertEqual(listed_links(entries[1:]), {stage_docs_site.CHAPTER_PAGE_LINK.format(name=path.relative_to(stage_docs_site.DOCS).with_suffix('').as_posix()) for path in stage_docs_site.chapter_paths()})


def listed_links(entries):
    """Return every page a sidebar lists: its pages, its groups' own pages and their pages, at any depth."""
    links = set()
    for entry in entries:
        if stage_docs_site.LINK in entry:
            links.add(entry[stage_docs_site.LINK])
        links |= listed_links(entry.get(stage_docs_site.ITEMS, []))
    return links


class TestStaging(unittest.TestCase):

    def test_staging_writes_the_front_page_every_chapter_the_screenshots_and_the_sidebar_afresh(self):
        with tempfile.TemporaryDirectory() as folder:
            out = pathlib.Path(folder)
            (out / LEFT_OVER).write_text(CHAPTER_TEXT, encoding=stage_docs_site.ENCODING)
            (out / LEFT_OVER_FOLDER).mkdir()
            count = stage_docs_site.stage(out=out)
            chapters = stage_docs_site.chapter_paths()
            self.assertEqual(count, len(chapters) + 1)
            self.assertFalse((out / LEFT_OVER).exists())
            self.assertFalse((out / LEFT_OVER_FOLDER).exists())
            self.assertTrue((out / stage_docs_site.INDEX).is_file())
            for chapter in chapters:
                shown = (out / chapter.relative_to(stage_docs_site.DOCS)).read_text(encoding=stage_docs_site.ENCODING)
                self.assertNotIn('GUIDE.md)', shown)
            self.assertTrue(any((out / stage_docs_site.SCREENSHOTS).iterdir()))
            groups = json.loads((out / stage_docs_site.SIDEBAR).read_text(encoding=stage_docs_site.ENCODING))
            self.assertEqual(groups, stage_docs_site.sidebar(stage_docs_site.GUIDE.read_text(encoding=stage_docs_site.ENCODING)))


if __name__ == '__main__':
    unittest.main()
