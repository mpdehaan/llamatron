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
"""The Grooves page, the groove editor, and the Groove field on the Song, Scene and Track pages."""

from llamatron.tui.text import sorted_names
from ui_testing import DRUMS, KEY_SHOWN, LEAD, UITest, key_of
from llamatron.composition.defaults import DEFAULT_GROOVE_CELL_LENGTH
from llamatron.composition.file_format import GrooveSetting
from llamatron.composition.groove import FACTORY_GROOVE_NAMES, FactoryGroove, GROOVE_CELL_LENGTH_CHOICES, GROOVE_CELLS, STRAIGHT
from llamatron.composition.limits import MAX_GROOVE_AMOUNT, MAX_GROOVE_CELLS
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.dialogs.message_dialog import MessageDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.groove_editor import GrooveEditor
from llamatron.tui.screens.grooves_page import GroovesPage
from llamatron.strings.labels import MSG_GROOVE_LABEL, MSG_NAME_LABEL
from llamatron.strings.legends import MSG_LEGEND_WHAT, What, KeyName
from llamatron.strings.marks import (
    MSG_FACTORY_GROOVE_SHOWN, MSG_GROOVE_NAME_SHOWN, MSG_GROOVE_OFF_SHOWN, MSG_OWN_GROOVE_SHOWN, MSG_SCENE_OR_SONG_GROOVE_SHOWN,
    MSG_SONG_GROOVE_SHOWN,
)
from llamatron.strings.messages import MSG_COPIED_TO, MSG_FACTORY_GROOVE_NOTE, MSG_USE_SONG_TRACK
from llamatron.strings.names import MSG_NEW_GROOVE_NAME
from llamatron.tui import keybindings
from llamatron.tui.key_table import first_key
from rendering import render_song

GROOVE_1 = MSG_NEW_GROOVE_NAME.format(number=1)
GROOVE_2 = MSG_NEW_GROOVE_NAME.format(number=2)
SHUFFLE = 'shuffle'
# A copy counts up from the number a name ends in, so a copy of the factory groove swing 58 is swing 59.
SWING_58_COPY = 'swing 59'
THE_SONG = 'untitled'
FIRST_SCENE = 0
TWELVE = 12
TYPED_TOO_BIG = '1234'


class TestGroovesPage(UITest):
    """The list of grooves: the factory ones, which can only be looked at and copied, then the set's own."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.GROOVES)
        self.assertIsInstance(self.app.screen, GroovesPage)

    def grooves(self):
        return self.document.song().get_groove_names()

    async def test_the_factory_grooves_are_listed_first_and_marked(self):
        self.assertEqual(self.grooves(), FACTORY_GROOVE_NAMES)
        text = self.text()
        for name in FACTORY_GROOVE_NAMES:
            self.assertIn(name, text)
        self.assertIn(MSG_FACTORY_GROOVE_SHOWN, text)
        self.assertNotIn(MSG_OWN_GROOVE_SHOWN, text)
        # The song chooses none, so none has one use and the rest have none.
        self.assertEqual([row[1][-1] for row in self.app.screen.rows()], [1] + [0] * (len(FACTORY_GROOVE_NAMES) - 1))

    async def test_a_factory_groove_cannot_be_renamed_moved_or_deleted(self):
        shown = [name for item in self.app.screen.key_table() for name in item.keys]
        self.assertNotIn(first_key(keybindings.GroovesPage.RENAME), shown)
        self.assertNotIn(Key.BACKSPACE, shown)
        self.assertNotIn(first_key(keybindings.GroovesPage.MOVE), shown)
        self.assertIn(first_key(keybindings.GroovesPage.COPY), shown)
        await self.press(keybindings.GroovesPage.RENAME, Key.BACKSPACE, keybindings.GroovesPage.MOVE)
        self.assertIsInstance(self.app.screen, GroovesPage)
        self.assertEqual(self.grooves(), FACTORY_GROOVE_NAMES)

    async def test_enter_looks_at_a_factory_groove_without_editing_it(self):
        await self.press(Key.DOWN, Key.DOWN, Key.ENTER)
        self.assertIsInstance(self.app.screen, GrooveEditor)
        self.assertIn(MSG_FACTORY_GROOVE_NOTE.strip(), self.text())
        self.assertIn(FactoryGroove.SWING_58, self.crumbs_line())
        await self.press(Key.RIGHT, '9', keybindings.GrooveEditor.MORE, keybindings.GrooveEditor.REMOVE_CELL, keybindings.GrooveEditor.CELL_LENGTH, keybindings.GrooveEditor.RENAME)
        self.assertIsInstance(self.app.screen, GrooveEditor)
        self.assertEqual(self.document.song().get_groove(FactoryGroove.SWING_58).get_cells()[1], 16)
        self.assertEqual(len(self.document.song().get_groove(FactoryGroove.SWING_58).get_cells()), GROOVE_CELLS)
        self.assertFalse(self.document.is_dirty())

    async def test_copying_a_factory_groove_makes_one_of_your_own(self):
        await self.press(Key.DOWN, Key.DOWN, keybindings.GroovesPage.COPY)
        self.assertEqual(self.grooves(), [*FACTORY_GROOVE_NAMES, SWING_58_COPY])
        self.assertIn(MSG_COPIED_TO.format(name=SWING_58_COPY), self.text())
        self.assertEqual(self.document.song().get_groove(SWING_58_COPY).get_cells(), self.document.song().get_groove(FactoryGroove.SWING_58).get_cells())
        self.assertIn(MSG_OWN_GROOVE_SHOWN, self.text())
        await self.press(Key.ENTER, Key.RIGHT, '9')
        self.assertEqual(self.document.song().get_groove(SWING_58_COPY).get_cells()[1], 9)

    async def test_up_and_down_nudge_a_cell_like_plus_and_minus(self):
        await self.press(keybindings.GroovesPage.ADD)
        self.assertIsInstance(self.app.screen, GrooveEditor)
        await self.press(Key.UP, Key.UP, Key.RIGHT, Key.DOWN, key_of(binding=keybindings.GrooveEditor.LESS, key=Key.MINUS))
        self.assertEqual(self.document.song().get_groove(GROOVE_1).get_cells()[:2], [2, -2])

    async def test_a_adds_a_numbered_straight_groove_and_opens_it(self):
        await self.press(keybindings.GroovesPage.ADD)
        self.assertIsInstance(self.app.screen, GrooveEditor)
        self.assertEqual(self.grooves(), [*FACTORY_GROOVE_NAMES, GROOVE_1])
        self.assertEqual(self.document.song().get_groove(GROOVE_1).get_cells(), [STRAIGHT] * GROOVE_CELLS)
        self.assertEqual(self.document.song().get_groove(GROOVE_1).get_cell_length_text(), DEFAULT_GROOVE_CELL_LENGTH)
        await self.press(Key.ESCAPE, keybindings.GroovesPage.ADD)
        self.assertEqual(self.grooves(), [*FACTORY_GROOVE_NAMES, GROOVE_1, GROOVE_2])

    async def test_your_own_grooves_can_be_renamed_moved_and_deleted(self):
        await self.press(keybindings.GroovesPage.ADD, Key.ESCAPE, keybindings.GroovesPage.ADD, Key.ESCAPE, keybindings.GroovesPage.RENAME)
        self.app.screen.value = SHUFFLE
        await self.press(Key.ENTER)
        self.assertEqual(self.grooves(), [*FACTORY_GROOVE_NAMES, GROOVE_1, SHUFFLE])
        await self.press(keybindings.GroovesPage.MOVE, Key.UP, Key.ENTER)
        self.assertEqual(self.grooves(), [*FACTORY_GROOVE_NAMES, SHUFFLE, GROOVE_1])
        await self.press(keybindings.GroovesPage.MOVE, Key.UP, Key.ENTER)
        self.assertEqual(self.grooves(), [*FACTORY_GROOVE_NAMES, SHUFFLE, GROOVE_1])
        await self.press(Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertEqual(self.grooves(), [*FACTORY_GROOVE_NAMES, GROOVE_1])

    async def test_a_groove_cannot_take_a_factory_name(self):
        await self.press(keybindings.GroovesPage.ADD, Key.ESCAPE, keybindings.GroovesPage.RENAME)
        self.app.screen.value = FactoryGroove.PUSH
        await self.press(Key.ENTER)
        self.assertEqual(self.grooves(), [*FACTORY_GROOVE_NAMES, GROOVE_1])

    async def test_a_groove_in_use_cannot_be_deleted(self):
        await self.press(keybindings.GroovesPage.ADD, Key.ESCAPE)
        self.document.set_track_groove(name=DRUMS, choice=GROOVE_1)
        await self.press(Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(MSG_USE_SONG_TRACK.format(song=THE_SONG, track=DRUMS), self.text())
        await self.press(Key.ENTER)
        self.assertEqual(self.grooves(), [*FACTORY_GROOVE_NAMES, GROOVE_1])
        render_song(self.document.song())


class TestGrooveEditor(UITest):
    """Editing one of your own grooves cell by cell."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.GROOVES, keybindings.GroovesPage.ADD)
        self.assertIsInstance(self.app.screen, GrooveEditor)

    def groove(self):
        return self.document.song().get_groove(GROOVE_1)

    async def test_the_brackets_change_an_amount_and_the_legend_names_up_and_down_alone(self):
        await self.press(Key.RIGHT, keybindings.GrooveEditor.MORE, keybindings.GrooveEditor.MORE, keybindings.GrooveEditor.LESS)
        self.assertEqual(self.groove().get_cells()[1], 1)
        self.assertIn(KEY_SHOWN.format(label=KeyName.LEFT_BRACKET) + MSG_LEGEND_WHAT.format(what=What.LESS), self.text())
        self.assertIn(KEY_SHOWN.format(label=KeyName.RIGHT_BRACKET) + MSG_LEGEND_WHAT.format(what=What.MORE), self.text())

    async def test_digits_type_an_amount_and_plus_and_minus_change_it(self):
        await self.press(Key.RIGHT, '1', '6')
        self.assertEqual(self.groove().get_cells()[1], 16)
        await self.press(key_of(binding=keybindings.GrooveEditor.MORE, key=Key.PLUS), key_of(binding=keybindings.GrooveEditor.MORE, key=Key.PLUS))
        self.assertEqual(self.groove().get_cells()[1], 18)
        await self.press(Key.LEFT, key_of(binding=keybindings.GrooveEditor.LESS, key=Key.MINUS))
        self.assertEqual(self.groove().get_cells()[0], -1)
        # Typing into a negative cell keeps the minus sign.
        await self.press('1', '2')
        self.assertEqual(self.groove().get_cells()[0], -TWELVE)
        # A digit that would take the number out of range starts a new number, as in the pattern editor.
        await self.press(*TYPED_TOO_BIG)
        self.assertEqual(self.groove().get_cells()[0], -34)
        self.assertEqual(self.groove().get_cells()[1], 18)

    async def test_the_name_is_shown_and_n_renames_it_everywhere(self):
        self.assertIn(MSG_GROOVE_NAME_SHOWN.format(label=MSG_NAME_LABEL, name=GROOVE_1).strip(), self.text())
        await self.press(Key.ESCAPE)
        self.document.set_track_groove(name=DRUMS, choice=GROOVE_1)
        await self.press(Key.ENTER, keybindings.GrooveEditor.RENAME)
        self.app.screen.value = SHUFFLE
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, GrooveEditor)
        self.assertIn(SHUFFLE, self.document.song().get_groove_names())
        self.assertNotIn(GROOVE_1, self.document.song().get_groove_names())
        self.assertEqual(self.track(DRUMS).get_groove_choice(), SHUFFLE)
        self.assertIn(MSG_GROOVE_NAME_SHOWN.format(label=MSG_NAME_LABEL, name=SHUFFLE).strip(), self.text())
        self.assertIn(SHUFFLE, self.crumbs_line())
        await self.press(Key.RIGHT, '7')
        self.assertEqual(self.document.song().get_groove(SHUFFLE).get_cells()[1], 7)

    async def test_amounts_stop_at_the_limits(self):
        await self.press(*[keybindings.GrooveEditor.MORE] * (MAX_GROOVE_AMOUNT + 5))
        self.assertEqual(self.groove().get_cells()[0], MAX_GROOVE_AMOUNT)
        await self.press(*[keybindings.GrooveEditor.LESS] * (2 * MAX_GROOVE_AMOUNT + 5))
        self.assertEqual(self.groove().get_cells()[0], -MAX_GROOVE_AMOUNT)

    async def test_cells_can_be_inserted_and_removed_within_the_limits(self):
        await self.press(Key.RIGHT, '7', keybindings.GrooveEditor.INSERT_CELL)
        self.assertEqual(self.groove().get_cells()[:3], [0, 0, 7])
        await self.press(keybindings.GrooveEditor.REMOVE_CELL, keybindings.GrooveEditor.REMOVE_CELL)
        self.assertEqual(self.groove().get_cells()[:2], [0, 0])
        self.assertEqual(len(self.groove().get_cells()), GROOVE_CELLS - 1)
        await self.press(*[keybindings.GrooveEditor.INSERT_CELL] * MAX_GROOVE_CELLS)
        self.assertEqual(len(self.groove().get_cells()), MAX_GROOVE_CELLS)
        await self.press(*[keybindings.GrooveEditor.REMOVE_CELL] * (MAX_GROOVE_CELLS + 2))
        self.assertEqual(len(self.groove().get_cells()), 1)

    async def test_s_steps_the_cell_length_round_the_choices(self):
        self.assertEqual(self.groove().get_cell_length_text(), DEFAULT_GROOVE_CELL_LENGTH)
        seen = []
        for _ in GROOVE_CELL_LENGTH_CHOICES:
            await self.press(keybindings.GrooveEditor.CELL_LENGTH)
            seen.append(self.groove().get_cell_length_text())
            self.assertIn(self.groove().get_cell_length_text(), self.text())
        self.assertEqual(sorted(seen), sorted(GROOVE_CELL_LENGTH_CHOICES))
        self.assertEqual(self.groove().get_cell_length_text(), DEFAULT_GROOVE_CELL_LENGTH)
        self.assertNotIn(GrooveSetting.CELL_LENGTH, self.groove().to_data())


class TestGrooveChoices(UITest):
    """The Groove field on the Song, Scene and Track pages."""

    async def test_the_song_page_steps_and_picks_the_songs_groove(self):
        await self.press(keybindings.MainPage.SONGS, Key.ENTER)
        await self.select_field(MSG_GROOVE_LABEL)
        self.assertEqual(self.document.song().get_groove_name(), FactoryGroove.NONE)
        # The arrows step through the names as the picker sorts them.
        names = sorted_names(FACTORY_GROOVE_NAMES)
        await self.press(Key.RIGHT, Key.RIGHT)
        self.assertEqual(self.document.song().get_groove_name(), names[names.index(FactoryGroove.NONE) + 2])
        await self.press(Key.LEFT, Key.LEFT, Key.LEFT)
        self.assertEqual(self.document.song().get_groove_name(), names[names.index(FactoryGroove.NONE) - 1])
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, names)
        await self.pick(FactoryGroove.PUSH)
        self.assertEqual(self.document.song().get_groove_name(), FactoryGroove.PUSH)
        self.assertIn(FactoryGroove.PUSH, self.text())
        render_song(self.document.song())

    async def test_the_scene_page_takes_the_songs_groove_or_chooses_off_or_a_name(self):
        await self.press(keybindings.MainPage.ARRANGE, Key.ENTER)
        await self.select_field(MSG_GROOVE_LABEL)
        self.assertIn(MSG_SONG_GROOVE_SHOWN.format(groove=FactoryGroove.NONE), self.text())
        await self.press(Key.RIGHT)
        self.assertIs(self.document.song().get_scenes()[FIRST_SCENE].get_groove_choice(), False)
        self.assertIn(MSG_GROOVE_OFF_SHOWN, self.text())
        # The arrows step through the names in the picker's order, sorted, after the two choices that aren't names.
        await self.press(Key.RIGHT, Key.RIGHT)
        self.assertEqual(self.document.song().get_scenes()[FIRST_SCENE].get_groove_choice(), sorted_names(FACTORY_GROOVE_NAMES)[1])
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.document.song().get_scenes()[FIRST_SCENE].get_groove_choice())
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        await self.pick(FactoryGroove.SWING_66)
        self.assertEqual(self.document.song().get_scenes()[FIRST_SCENE].get_groove_choice(), FactoryGroove.SWING_66)
        render_song(self.document.song())

    async def test_the_track_editor_takes_the_scene_or_song_groove_or_chooses(self):
        await self.press(keybindings.MainPage.ARRANGE, Key.UP, Key.ENTER)
        await self.select_field(MSG_GROOVE_LABEL)
        self.assertIn(MSG_SCENE_OR_SONG_GROOVE_SHOWN, self.text())
        await self.press(Key.RIGHT)
        self.assertIs(self.track(LEAD).get_groove_choice(), False)
        await self.press(Key.LEFT, Key.LEFT)
        self.assertIsNone(self.track(LEAD).get_groove_choice())
        await self.press(Key.ENTER)
        await self.pick(FactoryGroove.PUSH)
        self.assertEqual(self.track(LEAD).get_groove_choice(), FactoryGroove.PUSH)
        self.assertIn(FactoryGroove.PUSH, self.text())
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.track(LEAD).get_groove_choice())
        render_song(self.document.song())
