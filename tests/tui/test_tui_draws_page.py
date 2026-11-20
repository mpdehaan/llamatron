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

"""The Draws page: each draw a section whose settings change the song's draw, and a strip whose slots are stepped, typed and made blank."""

from unittest import mock

from llamatron.composition import defaults, limits
from llamatron.composition.file_format import DrawDirection, DrawName, DrawSetting
from llamatron.strings import labels as labels_text, marks
from llamatron.tui import drawing, keybindings, keys
from llamatron.tui.drawing import Box
from llamatron.tui.keys import Key
from llamatron.tui.screens.set.draws_page import DrawsPage
from llamatron.tui.transport import Transport
from tests.support.ui_testing import key_of, UITest

TYPED = '7'
LOWER_MAX = '3'
# More than the widest number a prompt here opens with, -99, so that clearing it leaves nothing.
PROMPT_ROOM = 4


class TestDrawsPage(UITest):

    async def open_draws(self):
        await self.press(keybindings.MainPage.DRAWS)
        self.assertIsInstance(self.app.screen, DrawsPage)

    async def type_over(self, text):
        """Open the prompt of the field under the cursor, clear what it opens with and type text."""
        await self.press(Key.ENTER)
        await self.press(*[Key.BACKSPACE] * PROMPT_ROOM)
        await self.type(text)
        await self.press(Key.ENTER)

    def draw(self, *, name=DrawName.AD):
        return self.document.song().get_draw(name)

    async def test_the_main_screen_opens_it_and_every_draw_is_a_section_closed_at_first(self):
        await self.open_draws()
        for name in (DrawName.AD, DrawName.BD, DrawName.CD, DrawName.DD):
            self.assertIn(name, self.text())
        self.assertNotIn(labels_text.MSG_DRAW_STRIP_SLOT_ROW, self.text())

    async def test_an_open_draw_shows_its_settings_and_its_strip_boxed_with_its_slots_numbered(self):
        await self.open_draws()
        await self.select_field(labels_text.MSG_DRAW_STRIP_LABEL)
        shown = self.text()
        for label in (labels_text.MSG_DRAW_DIRECTION_LABEL, labels_text.MSG_DRAW_SLOTS_LABEL, labels_text.MSG_DRAW_VALUE_MIN_LABEL, labels_text.MSG_DRAW_VALUE_MAX_LABEL, labels_text.MSG_DRAW_CONDITIONS_REDRAW_LABEL):
            self.assertIn(label, shown)
        self.assertIn(labels_text.MSG_DRAW_STRIP_SLOT_ROW, shown)
        self.assertIn(Box.TOP_LEFT, shown)
        self.assertIn(str(defaults.DEFAULT_DRAW_SLOT_COUNT), shown)

    async def test_the_direction_steps_through_every_direction_and_serial(self):
        await self.open_draws()
        await self.select_field(labels_text.MSG_DRAW_DIRECTION_LABEL)
        await self.press(Key.ENTER)
        await self.type(DrawDirection.SERIAL)
        await self.press(Key.ENTER)
        self.assertEqual(self.draw().get_direction(), DrawDirection.SERIAL)

    async def test_a_slot_is_stepped_from_zero_moved_along_typed_and_made_blank(self):
        await self.open_draws()
        await self.select_field(labels_text.MSG_DRAW_STRIP_LABEL)
        await self.press(keybindings.DrawsPage.SLOT_MORE)
        self.assertEqual(self.draw().get_slots()[0], 1)
        await self.press(Key.RIGHT)
        await self.press(keybindings.DrawsPage.SLOT_LESS)
        self.assertEqual(self.draw().get_slots()[1], -1)
        await self.press(Key.RIGHT, Key.ENTER)
        await self.type(TYPED)
        await self.press(Key.ENTER)
        self.assertEqual(self.draw().get_slots()[2], int(TYPED))
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.draw().get_slots()[2])

    async def test_a_digit_on_the_strip_puts_its_number_in_the_slot_kept_within_the_range(self):
        await self.open_draws()
        await self.select_field(labels_text.MSG_DRAW_VALUE_MAX_LABEL)
        await self.type_over(LOWER_MAX)
        await self.select_field(labels_text.MSG_DRAW_STRIP_LABEL)
        await self.press(keys.DIGITS[int(LOWER_MAX) - 1])
        self.assertEqual(self.draw().get_slots()[0], int(LOWER_MAX) - 1)
        await self.press(keys.DIGITS[int(LOWER_MAX) - 1])
        # A second digit puts its own number in, rather than making a number of two digits.
        self.assertEqual(self.draw().get_slots()[0], int(LOWER_MAX) - 1)
        await self.press(Key.RIGHT, keys.DIGITS[int(TYPED)])
        self.assertEqual(self.draw().get_slots()[1], int(LOWER_MAX))

    async def test_a_digit_off_the_strip_changes_no_slot(self):
        await self.open_draws()
        await self.select_field(labels_text.MSG_DRAW_DIRECTION_LABEL)
        await self.press(keys.DIGITS[int(TYPED)])
        self.assertEqual(self.draw().get_slots(), [None] * defaults.DEFAULT_DRAW_SLOT_COUNT)

    async def test_more_slots_lengthen_the_strip_and_a_lower_value_max_brings_every_slot_down_to_it(self):
        await self.open_draws()
        await self.select_field(labels_text.MSG_DRAW_STRIP_LABEL)
        await self.press(Key.ENTER)
        await self.type(TYPED)
        await self.press(Key.ENTER)
        await self.select_field(labels_text.MSG_DRAW_SLOTS_LABEL)
        await self.press(key_of(binding=keybindings.DrawsPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.draw().slot_count(), defaults.DEFAULT_DRAW_SLOT_COUNT + 1)
        await self.select_field(labels_text.MSG_DRAW_VALUE_MAX_LABEL)
        await self.type_over(LOWER_MAX)
        self.assertEqual(self.draw().get_slots()[0], int(LOWER_MAX))
        self.assertEqual(self.draw().get_value_max(), int(LOWER_MAX))

    async def test_conditions_redraw_switches_on_and_off(self):
        await self.open_draws()
        await self.select_field(labels_text.MSG_DRAW_CONDITIONS_REDRAW_LABEL)
        await self.press(keybindings.DrawsPage.TOGGLE)
        self.assertTrue(self.draw().redraws_in_conditions())
        self.assertEqual(self.draw().to_data()[DrawSetting.CONDITIONS_REDRAW], True)

    async def test_a_value_min_above_the_value_max_is_refused(self):
        await self.open_draws()
        await self.select_field(labels_text.MSG_DRAW_VALUE_MAX_LABEL)
        await self.type_over(str(limits.MIN_DRAW_VALUE))
        await self.select_field(labels_text.MSG_DRAW_VALUE_MIN_LABEL)
        await self.press(key_of(binding=keybindings.DrawsPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.draw().get_value_min(), limits.MIN_DRAW_VALUE)

    async def test_while_a_song_plays_a_draws_heading_says_the_slot_it_last_took_a_value_from(self):
        with mock.patch.object(Transport, Transport.draw_places.__name__, return_value={DrawName.BD: 2}):
            await self.open_draws()
            self.assertIn(marks.MSG_DRAW_HEADING_LIT.format(mark=drawing.NOTHING, place=3), self.text())
