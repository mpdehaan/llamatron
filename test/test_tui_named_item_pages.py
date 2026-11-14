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
"""The pages that show one named thing all keep its name, follow its rename and notice when it is gone the same way (tui/screens/shows_named_item.py).

The same checks run on each of them: the pattern, chain, groove, arpeggiator, AutoRatchet and
offsets editors, the Scale page and the track editor. The key that renames from each page is
tested with the page, so these checks call the page's rename and answer its prompt.
"""

import unittest

from ui_testing import TRADE, CLIPS, LAZY, PUSH, SLIDES, CLAVE, FOLK, POP, SMOOTH, CLIPPED, FADE, THIN, SWAY, LEAD, NAMED, ROLLS, TUNE, UITest, UP_ARP, leaf_pages
from llamatron.composition.file_format import Section
from llamatron.composition.generator_settings import ArpSetting
from llamatron.composition.groove import FactoryGroove
from llamatron.composition.setlist import DEFAULT_SCALE
from llamatron.strings.errors import ERR_EMPTY_NAME, ERR_NAME_IN_USE
from llamatron.strings.marks import MSG_CRUMB_SEPARATOR
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.drawing import NOTHING
from llamatron.tui.keys import Key
from llamatron.tui.screens.arp_editor import ArpEditor
from llamatron.tui.screens.auto_ratchet_editor import AutoRatchetEditor
from llamatron.tui.screens.drift_editor import DriftEditor
from llamatron.tui.screens.density_editor import DensityEditor
from llamatron.tui.screens.progression_editor import ProgressionEditor
from llamatron.tui.screens.chords_editor import ChordsEditor
from llamatron.tui.screens.voice_leading_editor import VoiceLeadingEditor
from llamatron.tui.screens.hocket_editor import HocketEditor
from llamatron.tui.screens.strum_editor import StrumEditor
from llamatron.tui.screens.euclid_editor import EuclidEditor
from llamatron.tui.screens.glide_editor import GlideEditor
from llamatron.tui.screens.shorten_editor import ShortenEditor
from llamatron.tui.screens.shorten_steps_editor import ShortenStepsEditor
from llamatron.tui.screens.rush_editor import RushEditor
from llamatron.tui.screens.rush_steps_editor import RushStepsEditor
from llamatron.tui.screens.drag_editor import DragEditor
from llamatron.tui.screens.drag_steps_editor import DragStepsEditor
from llamatron.tui.screens.glide_steps_editor import GlideStepsEditor
from llamatron.tui.screens.swell_editor import SwellEditor
from llamatron.tui.screens.articulate_editor import ArticulateEditor
from llamatron.tui.screens.chain_editor import ChainEditor
from llamatron.tui.screens.groove_editor import GrooveEditor
from llamatron.tui.screens.instrument_editor import InstrumentEditor
from llamatron.tui.screens.offsets_editor import OffsetsEditor
from llamatron.tui.screens.pattern_editor import PatternEditor
from llamatron.tui.screens.scale_page import ScalePage
from llamatron.tui.screens.shows_named_item import ShowsNamedItem
from llamatron.tui.screens.track_editor import TrackEditor

RENAMED = 'renamed'
A_GROOVE = 'shuffle'
A_INSTRUMENT = 'synth'
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
        return MSG_CRUMB_SEPARATOR.join([*self.PAGE.CRUMBS_BEFORE, self.PAGE.ITEM_CRUMB.format(name=name), *self.PAGE.CRUMBS_AFTER])

    def assert_crumbs_name(self, name):
        """Check that the page's crumbs are its own with the name among them, and that the header shows the name, however much of the rest fits."""
        self.assertEqual(MSG_CRUMB_SEPARATOR.join(self.page.crumb_trail()), self.crumbs_of(name))
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
        self.assertIn(ERR_NAME_IN_USE.format(name=other), self.text())
        await self.rename_to(NOTHING)
        self.assertIn(ERR_EMPTY_NAME, self.text())
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
    FIRST = TUNE

    async def another(self):
        """Return a second pattern. The first is played by a clip, so the checks that delete the first empty the arrangement."""
        self.empty_the_arrangement()
        return await super().another()


class TestChainEditorShowsItsChain(NamedItemChecks, UITest):

    PAGE = ChainEditor
    FIRST = NAMED


class TestInstrumentEditorShowsItsInstrument(NamedItemChecks, UITest):

    PAGE = InstrumentEditor
    FIRST = A_INSTRUMENT

    def prepare(self):
        self.document.add_instrument(A_INSTRUMENT)


class TestGrooveEditorShowsItsGroove(NamedItemChecks, UITest):

    PAGE = GrooveEditor
    FIRST = A_GROOVE

    def prepare(self):
        self.document.add_groove(A_GROOVE)

    async def test_a_factory_groove_is_always_there(self):
        self.page.show_item(FactoryGroove.SWING_58)
        self.assertTrue(self.page.still_exists())

    async def test_a_factory_grooves_name_is_in_use(self):
        await self.rename_to(FactoryGroove.SWING_58)
        self.assertIn(ERR_NAME_IN_USE.format(name=FactoryGroove.SWING_58), self.text())
        self.assertEqual(self.page.item, A_GROOVE)


class TestArpEditorShowsItsArp(NamedItemChecks, UITest):

    PAGE = ArpEditor
    FIRST = UP_ARP


class TestAutoRatchetEditorShowsItsAutoRatchet(NamedItemChecks, UITest):

    PAGE = AutoRatchetEditor
    FIRST = ROLLS


class TestDriftEditorShowsItsDrift(NamedItemChecks, UITest):

    PAGE = DriftEditor
    FIRST = SWAY


class TestProgressionEditorShowsItsProgression(NamedItemChecks, UITest):

    PAGE = ProgressionEditor
    FIRST = POP


class TestChordsEditorShowsItsProgression(NamedItemChecks, UITest):

    PAGE = ChordsEditor
    FIRST = POP
    RENAMES = False


class TestVoiceLeadingEditorShowsItsVoiceLeading(NamedItemChecks, UITest):

    PAGE = VoiceLeadingEditor
    FIRST = SMOOTH


class TestHocketEditorShowsItsHocket(NamedItemChecks, UITest):

    PAGE = HocketEditor
    FIRST = TRADE


class TestStrumEditorShowsItsStrum(NamedItemChecks, UITest):

    PAGE = StrumEditor
    FIRST = FOLK


class TestEuclidEditorShowsItsEuclid(NamedItemChecks, UITest):

    PAGE = EuclidEditor
    FIRST = CLAVE


class TestGlideEditorShowsItsGlide(NamedItemChecks, UITest):

    PAGE = GlideEditor
    FIRST = SLIDES


class TestGlideStepsEditorShowsItsGlide(NamedItemChecks, UITest):

    PAGE = GlideStepsEditor
    FIRST = SLIDES
    RENAMES = False


class TestShortenEditorShowsItsShorten(NamedItemChecks, UITest):

    PAGE = ShortenEditor
    FIRST = CLIPS


class TestShortenStepsEditorShowsItsShorten(NamedItemChecks, UITest):

    PAGE = ShortenStepsEditor
    FIRST = CLIPS
    RENAMES = False


class TestRushEditorShowsItsRush(NamedItemChecks, UITest):

    PAGE = RushEditor
    FIRST = PUSH


class TestRushStepsEditorShowsItsRush(NamedItemChecks, UITest):

    PAGE = RushStepsEditor
    FIRST = PUSH
    RENAMES = False


class TestDragEditorShowsItsDrag(NamedItemChecks, UITest):

    PAGE = DragEditor
    FIRST = LAZY


class TestDragStepsEditorShowsItsDrag(NamedItemChecks, UITest):

    PAGE = DragStepsEditor
    FIRST = LAZY
    RENAMES = False


class TestDensityEditorShowsItsDensity(NamedItemChecks, UITest):

    PAGE = DensityEditor
    FIRST = THIN


class TestSwellEditorShowsItsSwell(NamedItemChecks, UITest):

    PAGE = SwellEditor
    FIRST = FADE


class TestArticulateEditorShowsItsArticulate(NamedItemChecks, UITest):

    PAGE = ArticulateEditor
    FIRST = CLIPPED


class TestScalePageShowsItsScale(NamedItemChecks, UITest):

    PAGE = ScalePage
    FIRST = DEFAULT_SCALE


class TestTrackEditorShowsItsTrack(NamedItemChecks, UITest):

    PAGE = TrackEditor
    FIRST = LEAD


class TestOffsetsEditorShowsItsArp(NamedItemChecks, UITest):

    PAGE = OffsetsEditor
    FIRST = UP_ARP
    RENAMES = False

    def prepare(self):
        self.document.set_generator_setting(section=Section.ARPS, name=UP_ARP, setting=ArpSetting.OFFSETS, value=SOME_OFFSETS)

    async def test_the_arp_without_its_offsets_is_nothing_to_edit(self):
        self.document.set_generator_setting(section=Section.ARPS, name=UP_ARP, setting=ArpSetting.OFFSETS, value=None)
        self.assertFalse(self.page.still_exists())


# The test class of each page of one named thing, which the rule below reads.
CHECKED = [
    TestPatternEditorShowsItsPattern, TestChainEditorShowsItsChain, TestGrooveEditorShowsItsGroove, TestInstrumentEditorShowsItsInstrument, TestArpEditorShowsItsArp,
    TestAutoRatchetEditorShowsItsAutoRatchet, TestDriftEditorShowsItsDrift, TestProgressionEditorShowsItsProgression, TestChordsEditorShowsItsProgression, TestVoiceLeadingEditorShowsItsVoiceLeading, TestHocketEditorShowsItsHocket, TestStrumEditorShowsItsStrum, TestEuclidEditorShowsItsEuclid, TestGlideEditorShowsItsGlide, TestGlideStepsEditorShowsItsGlide, TestShortenEditorShowsItsShorten, TestShortenStepsEditorShowsItsShorten,
    TestRushEditorShowsItsRush, TestRushStepsEditorShowsItsRush, TestDragEditorShowsItsDrag, TestDragStepsEditorShowsItsDrag,
    TestDensityEditorShowsItsDensity, TestSwellEditorShowsItsSwell,
    TestArticulateEditorShowsItsArticulate, TestScalePageShowsItsScale, TestTrackEditorShowsItsTrack, TestOffsetsEditorShowsItsArp,
]


class TestEveryPageOfOneNamedThingIsChecked(unittest.TestCase):

    def test_every_such_page_has_the_checks(self):
        pages = [page for page in leaf_pages() if issubclass(page, ShowsNamedItem)]
        self.assertEqual(sorted(page.__name__ for page in pages), sorted(checks.PAGE.__name__ for checks in CHECKED))

    def test_every_such_page_names_its_section_and_its_crumbs(self):
        for checks in CHECKED:
            page = checks.PAGE
            self.assertIsNotNone(page.SECTION, page.__name__)
            self.assertTrue(page.CRUMBS_BEFORE, page.__name__)
            self.assertEqual(page.RENAME_PROMPT is not None, checks.RENAMES, page.__name__)

    def test_no_page_keeps_a_way_of_its_own(self):
        for checks in CHECKED:
            for method in (ShowsNamedItem.show_item, ShowsNamedItem.follow_renames, ShowsNamedItem.rename):
                self.assertIs(getattr(checks.PAGE, method.__name__), method, checks.PAGE.__name__)


if __name__ == '__main__':
    unittest.main()
