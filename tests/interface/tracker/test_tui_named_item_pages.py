# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The pages that show one named thing all keep its name, follow its rename and notice when it is gone the same way (interface/tracker/screens/shared/shows_named_item.py).

The same checks run on each of them: the pattern, chain, groove, arpeggiator, AutoRatchet and
offsets editors, the Scale page and the track editor. The key that renames from each page is
tested with the page, so these checks call the page's rename and answer its prompt.
"""

import inspect
import unittest

from llamatron.engine.generators import arp as arp_plugin
from llamatron.engine.generators.arp.model import ArpSetting
from llamatron.interface.tracker import drawing
from llamatron.interface.tracker.dialogs.prompt_dialog import PromptDialog
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.generators.arp_editor import ArpEditor
from llamatron.interface.tracker.screens.generators.chain_editor import ChainEditor
from llamatron.interface.tracker.screens.generators.offsets_editor import OffsetsEditor
from llamatron.interface.tracker.screens.pattern.pattern_editor import PatternEditor
from llamatron.interface.tracker.screens.shared.shows_named_item import ShowsNamedItem
from llamatron.user_strings import errors, marks
from tests.support import ui_testing
from tests.support.ui_testing import leaf_pages, UITest

RENAMED = 'renamed'
SOME_OFFSETS = [0, 2]
THE_PAGE_DOES_NOT_RENAME = 'the offsets editor shows an arpeggiator, which is renamed from the arpeggiator editor'


class NamedItemChecks:
    """What every page of one named thing does, checked on the page a test class names.

    A test class gives PAGE and the name of the thing the page opens on as FIRST.
    """

    __slots__ = ()

    PAGE = None
    FIRST = None
    RENAMES = True

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.prepare()
        self.app.screen.show_page(self.make_page())
        await self.pilot.pause()
        self.assertIsInstance(self.app.screen, self.PAGE)
        self.page = self.app.screen

    def prepare(self):
        """Give the set what the page needs before the page opens."""

    def make_page(self):
        """Return the page, open on the thing a test class names, as most pages are made."""
        return self.PAGE(holder=self.app.screen.holder, name=self.FIRST)

    def header(self):
        return self.crumbs_line()

    def crumbs_of(self, name):
        """Return the page's crumbs for a name, as the header joins them."""
        return marks.MSG_CRUMB_SEPARATOR.join([*self.PAGE.CRUMBS_BEFORE, self.PAGE.ITEM_CRUMB.format(name=name), *self.PAGE.CRUMBS_AFTER])

    def assert_crumbs_name(self, name):
        """Check that the page's crumbs are its own with the name among them, and that the header shows the name, however much of the rest fits."""
        self.assertEqual(marks.MSG_CRUMB_SEPARATOR.join(self.page.crumb_trail()), self.crumbs_of(name))
        self.assertIn(name, self.header())

    async def another(self):
        """Add a second thing to the page's section, a copy of the first, and return its name."""
        new = self.document.copy_named(section=self.PAGE.SECTION, name=self.FIRST)
        self.document.record_edit()
        return new

    async def rename_to(self, name):
        self.page.rename()
        await self.pilot.pause()
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.assertIn(self.PAGE.RENAME_PROMPT, self.text())
        self.app.screen.value = name
        await self.press(Key.ENTER)

    async def test_the_header_names_the_thing_among_the_pages_crumbs(self):
        self.assertEqual(self.page.item, self.FIRST)
        self.assert_crumbs_name(self.FIRST)
        self.assertTrue(self.page.still_exists())

    async def test_renaming_changes_the_set_and_the_header(self):
        if not self.RENAMES:
            self.skipTest(THE_PAGE_DOES_NOT_RENAME)
        await self.rename_to(RENAMED)
        self.assertIs(self.app.screen, self.page)
        self.assertEqual(self.page.item, RENAMED)
        self.assertIn(RENAMED, self.document.names_of(self.PAGE.SECTION))
        self.assertNotIn(self.FIRST, self.document.names_of(self.PAGE.SECTION))
        self.assert_crumbs_name(RENAMED)

    async def test_a_name_in_use_and_an_empty_name_are_each_refused_in_their_own_words(self):
        if not self.RENAMES:
            self.skipTest(THE_PAGE_DOES_NOT_RENAME)
        other = await self.another()
        before = self.document.names_of(self.PAGE.SECTION)
        await self.rename_to(other)
        self.assertIn(errors.ERR_NAME_IN_USE.format(name=other), self.text())
        await self.rename_to(drawing.NOTHING)
        self.assertIn(errors.ERR_EMPTY_NAME, self.text())
        self.assertEqual(self.document.names_of(self.PAGE.SECTION), before)
        self.assertEqual(self.page.item, self.FIRST)

    async def test_the_page_follows_a_rename_made_elsewhere_and_ignores_another_things(self):
        other = await self.another()
        self.page.follow_renames({self.PAGE.SECTION: {other: RENAMED}})
        self.assertEqual(self.page.item, self.FIRST)
        self.document.rename_named(section=self.PAGE.SECTION, old=self.FIRST, new=RENAMED)
        self.page.follow_renames({self.PAGE.SECTION: {self.FIRST: RENAMED}})
        self.assertEqual(self.page.item, RENAMED)
        self.assertTrue(self.page.still_exists())
        await self.press(Key.DOWN)
        self.assert_crumbs_name(RENAMED)

    async def test_the_thing_is_gone_once_it_is_deleted(self):
        await self.another()
        self.document.delete_named(section=self.PAGE.SECTION, name=self.FIRST)
        self.assertFalse(self.page.still_exists())


class TestPatternEditorShowsItsPattern(NamedItemChecks, UITest):

    PAGE = PatternEditor
    FIRST = ui_testing.TUNE

    async def another(self):
        """Return a second pattern. The first is played by a clip, so the checks that delete the first empty the arrangement."""
        self.empty_the_arrangement()
        return await super().another()


class TestChainEditorShowsItsChain(NamedItemChecks, UITest):

    PAGE = ChainEditor
    FIRST = ui_testing.NAMED


class TestArpEditorShowsItsArp(NamedItemChecks, UITest):

    PAGE = ArpEditor
    FIRST = ui_testing.UP_ARP


class TestOffsetsEditorShowsItsArp(NamedItemChecks, UITest):

    PAGE = OffsetsEditor
    FIRST = ui_testing.UP_ARP
    RENAMES = False

    def prepare(self):
        self.document.change_set(self.document.generator(section=arp_plugin.SECTION, name=ui_testing.UP_ARP).set_setting, name=ArpSetting.OFFSETS, value=SOME_OFFSETS)

    async def test_the_arp_without_its_offsets_is_nothing_to_edit(self):
        self.document.change_set(self.document.generator(section=arp_plugin.SECTION, name=ui_testing.UP_ARP).set_setting, name=ArpSetting.OFFSETS, value=None)
        self.assertFalse(self.page.still_exists())


# The pages of one named thing that carry the full checks: a list, a settings editor and a generator's, standing for every such
# page, since the rule below holds that every one shows, follows renames and renames by the one shared way; and the offsets
# editor, which is the one that renames nothing.
# What a page that serves many sections is given as it opens.
SECTION_GIVEN = 'section'

CHECKED = [TestPatternEditorShowsItsPattern, TestChainEditorShowsItsChain, TestArpEditorShowsItsArp, TestOffsetsEditorShowsItsArp]


class TestEveryPageOfOneNamedThingIsChecked(unittest.TestCase):

    def test_every_such_page_names_its_section_and_its_crumbs(self):
        # A page drawn from a generator plugin's view, which serves every such plugin, is given its section as it opens.
        for page in pages_of_one_named_thing():
            if page.SECTION is None:
                self.assertIn(SECTION_GIVEN, inspect.signature(page.__init__).parameters, page.__name__)
            self.assertTrue(page.CRUMBS_BEFORE, page.__name__)

    def test_no_page_keeps_a_way_of_its_own(self):
        for page in pages_of_one_named_thing():
            for method in (ShowsNamedItem.show_item, ShowsNamedItem.follow_renames, ShowsNamedItem.rename):
                self.assertIs(getattr(page, method.__name__), method, page.__name__)

    def test_the_checks_run_on_such_pages(self):
        self.assertTrue(all(checks.PAGE in pages_of_one_named_thing() for checks in CHECKED))


def pages_of_one_named_thing():
    """Return every page that shows one named thing."""
    return [page for page in leaf_pages() if issubclass(page, ShowsNamedItem)]


if __name__ == '__main__':
    unittest.main()
