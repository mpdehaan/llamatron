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

from llamatron.composition.file_format import GeneratorKind, Section, SectionKind
from llamatron.composition.generator_settings import DEFAULT_EARLY_NOTES, DEFAULT_LINE_BARS, LINES_IN_BARS, PhrasingSetting
from llamatron.generators.phrasing import EVEN_LINES, LONG_BREATH, LONG_THEN_SHORT, MEDIUM_BREATH, MOST_EARLY, NO_BREATH
from llamatron.strings.labels import (
    MSG_BY_SECTION_COLUMN, MSG_BY_SECTION_HEADING, MSG_PHRASING_BREATH_LABEL, MSG_PHRASING_EARLY_LABEL, MSG_PHRASING_LABEL, MSG_PHRASING_LINE_LABEL,
    MSG_PHRASING_LINE_LENGTHS_LABEL, MSG_PHRASING_LINE_NAMES,
)
from llamatron.strings.marks import MSG_SAME_AS_ABOVE, MSG_SECTION_SET
from llamatron.tui import keybindings
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.generators.phrasing_editor import PhrasingEditor
from tests.support.ui_testing import BREATHES, UITest

# The table's cells, counted from the left.
BREATH_CELL = 0
LINE_LENGTHS_CELL = 1
EARLY_CELL = 2
LONGEST_LINE = LINES_IN_BARS[-1]


class TestPhrasingAdded(UITest):

    async def test_a_new_one_is_found_under_articulation_and_starts_with_its_usual_values(self):
        name = await self.add_generator(Section.PHRASINGS)
        settings = self.document.song().get_generator_settings(kind=GeneratorKind.PHRASING, name=name)
        self.assertEqual(settings.to_data(), {})
        self.assertIsInstance(self.app.screen, PhrasingEditor)
        self.assertIn(MSG_PHRASING_LABEL.upper(), self.text().upper())


class TestPhrasingEditor(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_generator(section=Section.PHRASINGS)
        self.assertIsInstance(self.app.screen, PhrasingEditor)

    def phrasing(self):
        return self.document.song().get_generator_settings(kind=GeneratorKind.PHRASING, name=BREATHES)

    async def to_row_of(self, section):
        """Open the By Section table and put the cursor on a kind of section's row."""
        await self.select_field(section)

    async def test_the_line_is_stepped_through_its_lengths_and_stops_at_each_end(self):
        await self.select_field(MSG_PHRASING_LINE_LABEL)
        self.assertEqual(self.phrasing().get_line_bars(), DEFAULT_LINE_BARS)
        await self.press(*[keybindings.PhrasingEditor.MORE] * len(LINES_IN_BARS))
        self.assertEqual(self.phrasing().get_line_bars(), LONGEST_LINE)
        self.assertIn(MSG_PHRASING_LINE_NAMES[LONGEST_LINE], self.text())
        await self.press(*[keybindings.PhrasingEditor.LESS] * len(LINES_IN_BARS))
        self.assertEqual(self.phrasing().get_line_bars(), LINES_IN_BARS[0])

    async def test_the_breath_and_the_line_lengths_are_chosen_and_the_early_notes_stepped(self):
        await self.select_field(MSG_PHRASING_BREATH_LABEL)
        await self.press(keybindings.PhrasingEditor.MORE)
        self.assertEqual(self.phrasing().get_own(PhrasingSetting.BREATH), LONG_BREATH)
        await self.select_field(MSG_PHRASING_LINE_LENGTHS_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        await self.pick(EVEN_LINES)
        self.assertEqual(self.phrasing().get_own(PhrasingSetting.LINE_LENGTHS), EVEN_LINES)
        await self.select_field(MSG_PHRASING_EARLY_LABEL)
        await self.press(*[keybindings.PhrasingEditor.MORE] * MOST_EARLY)
        self.assertEqual(self.phrasing().get_own(PhrasingSetting.EARLY_NOTES), MOST_EARLY)

    async def test_a_value_put_back_to_what_a_phrasing_starts_with_is_left_out_of_the_file(self):
        await self.select_field(MSG_PHRASING_BREATH_LABEL)
        await self.press(keybindings.PhrasingEditor.MORE)
        self.assertEqual(self.phrasing().to_data(), {PhrasingSetting.BREATH: LONG_BREATH})
        await self.press(keybindings.PhrasingEditor.LESS)
        self.assertEqual(self.phrasing().get_own(PhrasingSetting.BREATH), MEDIUM_BREATH)
        self.assertEqual(self.phrasing().to_data(), {})

    async def test_the_table_is_closed_until_opened_and_then_names_its_columns_and_every_kind_of_section(self):
        self.assertNotIn(MSG_BY_SECTION_COLUMN, self.text())
        await self.to_row_of(SectionKind.VERSE)
        shown = self.text()
        for text in (MSG_BY_SECTION_COLUMN, MSG_PHRASING_BREATH_LABEL.upper(), MSG_PHRASING_LINE_LENGTHS_LABEL.upper(), MSG_PHRASING_EARLY_LABEL.upper(), SectionKind.VERSE, MSG_SAME_AS_ABOVE):
            self.assertIn(text, shown)

    async def test_a_sections_cell_is_chosen_from_a_list_with_same_first_and_cleared_with_bksp(self):
        await self.to_row_of(SectionKind.CHORUS)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options[0], MSG_SAME_AS_ABOVE)
        await self.pick(NO_BREATH)
        self.assertEqual(self.phrasing().get_section_own(section=SectionKind.CHORUS, name=PhrasingSetting.BREATH), NO_BREATH)
        self.assertIsNone(self.phrasing().get_section_own(section=SectionKind.VERSE, name=PhrasingSetting.BREATH))
        await self.press(keybindings.PhrasingEditor.CLEAR)
        self.assertEqual(self.phrasing().to_data(), {})

    async def test_right_moves_along_a_sections_cells_to_the_line_lengths_and_the_early_notes(self):
        await self.to_row_of(SectionKind.BRIDGE)
        await self.press(Key.RIGHT, Key.ENTER)
        await self.pick(EVEN_LINES)
        await self.press(Key.RIGHT, Key.ENTER)
        await self.pick(str(MOST_EARLY))
        own = {PhrasingSetting.LINE_LENGTHS: EVEN_LINES, PhrasingSetting.EARLY_NOTES: MOST_EARLY}
        self.assertEqual(self.phrasing().to_data(), {PhrasingSetting.BY_SECTION: {SectionKind.BRIDGE: own}})
        self.assertEqual(self.phrasing().get_for(section=SectionKind.BRIDGE, name=PhrasingSetting.LINE_LENGTHS), EVEN_LINES)
        self.assertEqual(self.phrasing().get_for(section=SectionKind.VERSE, name=PhrasingSetting.LINE_LENGTHS), LONG_THEN_SHORT)
        self.assertEqual(self.phrasing().get_for(section=SectionKind.VERSE, name=PhrasingSetting.EARLY_NOTES), DEFAULT_EARLY_NOTES)

    async def test_the_closed_heading_says_set_once_a_section_has_a_value_of_its_own(self):
        self.assertNotIn(MSG_BY_SECTION_HEADING + ' ' * 3 + MSG_SECTION_SET, self.text())
        self.document.set_phrasing_section_own(name=BREATHES, section=SectionKind.CHORUS, setting=PhrasingSetting.BREATH, value=NO_BREATH)
        self.app.screen.draw()
        self.assertIn(MSG_SECTION_SET, self.text())

    async def test_the_column_headings_change_nothing(self):
        await self.to_row_of(MSG_BY_SECTION_COLUMN)
        before = self.document.setlist().to_data()
        await self.press(Key.ENTER, Key.RIGHT, keybindings.PhrasingEditor.CLEAR)
        self.assertIsInstance(self.app.screen, PhrasingEditor)
        self.assertEqual(self.document.setlist().to_data(), before)
