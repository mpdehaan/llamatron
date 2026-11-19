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
"""The tracker's Phrasing pages: a new one, the editor's fields, and the By Section table of what each kind of section does of its own."""

from llamatron.composition.file_format import GeneratorKind, Section
from llamatron.composition import generator_settings
from llamatron.composition.generator_settings import PhrasingSetting
from llamatron.generators.phrasing import BIG_RISE, BREATHS, DEEP_BREATH, FLOWING_NOTES, JOINS, QUICK_BREATH, RISES
from llamatron.strings import labels
from llamatron.tui import keybindings
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.generators.phrasing_editor import PhrasingEditor
from tests.support.ui_testing import BREATHES, UITest

LONGEST_LINE = generator_settings.LINES_IN_BARS[-1]


class TestPhrasingAdded(UITest):

    async def test_a_new_one_is_found_under_articulation_and_starts_with_its_usual_values(self):
        name = await self.add_generator(Section.PHRASINGS)
        settings = self.document.song().get_generator_settings(kind=GeneratorKind.PHRASING, name=name)
        self.assertEqual(settings.to_data(), {})
        self.assertIsInstance(self.app.screen, PhrasingEditor)
        self.assertIn(labels.MSG_PHRASING_LABEL.upper(), self.text().upper())


class TestPhrasingEditor(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_generator(section=Section.PHRASINGS)
        self.assertIsInstance(self.app.screen, PhrasingEditor)

    def phrasing(self):
        return self.document.song().get_generator_settings(kind=GeneratorKind.PHRASING, name=BREATHES)

    async def test_the_page_shows_its_four_fields_each_with_its_value_in_words(self):
        shown = self.text()
        for label in (labels.MSG_PHRASING_LINE_LABEL, labels.MSG_PHRASING_BREATH_LABEL, labels.MSG_PHRASING_RISE_LABEL, labels.MSG_PHRASING_NOTES_LABEL):
            self.assertIn(label, shown)
        self.assertIn(labels.MSG_PHRASING_LINE_NAMES[generator_settings.DEFAULT_LINE_BARS], shown)
        self.assertIn(QUICK_BREATH, shown)

    async def test_the_line_is_stepped_through_its_lengths_and_stops_at_each_end(self):
        await self.select_field(labels.MSG_PHRASING_LINE_LABEL)
        self.assertEqual(self.phrasing().get_own(PhrasingSetting.LINE_BARS), generator_settings.DEFAULT_LINE_BARS)
        await self.press(*[keybindings.PhrasingEditor.MORE] * len(generator_settings.LINES_IN_BARS))
        self.assertEqual(self.phrasing().get_own(PhrasingSetting.LINE_BARS), LONGEST_LINE)
        self.assertIn(labels.MSG_PHRASING_LINE_NAMES[LONGEST_LINE], self.text())
        await self.press(*[keybindings.PhrasingEditor.LESS] * len(generator_settings.LINES_IN_BARS))
        self.assertEqual(self.phrasing().get_own(PhrasingSetting.LINE_BARS), generator_settings.LINES_IN_BARS[0])

    async def test_the_breath_is_stepped_and_the_rise_and_the_notes_are_chosen_from_their_lists(self):
        await self.select_field(labels.MSG_PHRASING_BREATH_LABEL)
        await self.press(keybindings.PhrasingEditor.MORE)
        self.assertEqual(self.phrasing().get_own(PhrasingSetting.BREATH), DEEP_BREATH)
        await self.select_field(labels.MSG_PHRASING_RISE_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(list(self.app.screen.options), list(RISES))
        await self.pick(BIG_RISE)
        self.assertEqual(self.phrasing().get_own(PhrasingSetting.RISE_AND_FALL), BIG_RISE)
        await self.select_field(labels.MSG_PHRASING_NOTES_LABEL)
        await self.press(Key.ENTER)
        self.assertEqual(list(self.app.screen.options), list(JOINS))
        await self.pick(FLOWING_NOTES)
        self.assertEqual(self.phrasing().get_own(PhrasingSetting.NOTES), FLOWING_NOTES)

    async def test_the_breaths_list_holds_its_three_words(self):
        await self.select_field(labels.MSG_PHRASING_BREATH_LABEL)
        await self.press(Key.ENTER)
        self.assertEqual(list(self.app.screen.options), list(BREATHS))

    async def test_a_value_put_back_to_what_a_phrasing_starts_with_is_left_out_of_the_file(self):
        await self.select_field(labels.MSG_PHRASING_BREATH_LABEL)
        await self.press(keybindings.PhrasingEditor.MORE)
        self.assertEqual(self.phrasing().to_data(), {PhrasingSetting.BREATH: DEEP_BREATH})
        await self.press(keybindings.PhrasingEditor.LESS)
        self.assertEqual(self.phrasing().get_own(PhrasingSetting.BREATH), QUICK_BREATH)
        self.assertEqual(self.phrasing().to_data(), {})
