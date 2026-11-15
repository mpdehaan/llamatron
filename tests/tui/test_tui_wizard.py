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
"""The song wizard: its tree and its fields, the keys between them, what Create adds to the set, closing, and undo."""

from llamatron.composition.file_format import Section
from llamatron.macro_composer.wizard_choices import MINOR, genre_names, genre_title
from llamatron.strings.errors import ERR_WIZARD_CHOOSE_GENRE, ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE
from llamatron.strings.labels import MSG_GENRE_LABEL, MSG_NAME_LABEL, MSG_SCALE_LABEL, MSG_TEMPO_LABEL, MSG_WIZARD_BARS_LABEL, MSG_WIZARD_CREATE_BRANCH, MSG_WIZARD_FORM_BRANCH, MSG_WIZARD_FORM_LABEL, MSG_WIZARD_GENRE_BRANCH, MSG_WIZARD_KEY_LABEL, MSG_WIZARD_SCALE_TYPE_NAMES, MSG_WIZARD_SUBGENRE_LABEL
from llamatron.strings.marks import MSG_WIZARD_BRANCH_CLOSED, MSG_WIZARD_BRANCH_OPEN, MSG_WIZARD_CHOOSE, MSG_WIZARD_EDITED_BRANCH, MSG_WIZARD_NEEDS_GENRE
from llamatron.strings.messages import MSG_UNDONE, MSG_RESTORED, MSG_WIZARD_ALREADY_OPEN, MSG_WIZARD_CLOSE_QUESTION, MSG_WIZARD_CREATED, MSG_WIZARD_CHOOSE_FIRST, MSG_WIZARD_NOTHING_TO_UNDO
from llamatron.strings.names import MSG_DEFAULT_SONG_NAME, MSG_NEW_SONG_WORD
from llamatron.composition.naming import new_name
from llamatron.tui import keybindings
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.arrange.arrange_page import ArrangePage
from llamatron.tui.screens.set.main_page import MainPage
from llamatron.tui.screens.set.songs_page import SongsPage
from llamatron.tui.screens.wizard.wizard_page import WizardPage
from tests.support.ui_testing import UITest, fixed_text, key_of

# The tree's branches by their places from the top, while none is open.
GENRE_PLACE = 0
FORM_PLACE = 1
CREATE_PLACE = 2
# A name the test gives the song.
A_SONG_NAME = 'anthem'


class WizardTest(UITest):
    """Opens the wizard from the main screen, and has the steps the tests share."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.Page.WIZARD)

    def wizard(self):
        return self.app.screen

    def choices(self):
        return self.wizard().choices()

    async def go_to_branch(self, place):
        """Move the tree's cursor to a branch by its place from the top."""
        await self.press(*[Key.UP] * len(self.wizard().rows()), *[Key.DOWN] * place)

    async def choose_genre_and_subgenre(self):
        """Choose the first genre and its first subgenre, each with ] (inc) from nothing chosen, and go back to the tree."""
        await self.go_to_branch(GENRE_PLACE)
        await self.press(keybindings.WizardPage.INTO_FIELDS, key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET), Key.DOWN, key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET), keybindings.WizardPage.TO_TREE)

    async def create(self):
        await self.go_to_branch(CREATE_PLACE)
        await self.press(keybindings.WizardPage.INTO_FIELDS, Key.ENTER)


class TestWizardPage(WizardTest):

    async def test_f9_opens_the_wizard_from_any_page_with_the_cursor_in_the_tree_on_genre(self):
        self.assertIsInstance(self.wizard(), WizardPage)
        self.assertFalse(self.wizard().in_fields)
        self.assertEqual(self.wizard().branch().name(), MSG_WIZARD_GENRE_BRANCH)
        await self.press(Key.ESCAPE, keybindings.MainPage.SONGS, keybindings.Page.WIZARD)
        self.assertIsInstance(self.wizard(), WizardPage)
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, SongsPage)

    async def test_f9_in_the_wizard_says_the_wizard_is_open(self):
        await self.press(keybindings.Page.WIZARD)
        self.assertIsInstance(self.wizard(), WizardPage)
        self.assertEqual(len(self.app.pages()), 2)
        self.assertIn(MSG_WIZARD_ALREADY_OPEN, self.text())

    async def test_the_tree_lists_genre_form_and_create_and_the_fields_of_the_branch_under_the_cursor_show(self):
        text = self.text()
        for name in (MSG_WIZARD_GENRE_BRANCH, MSG_WIZARD_FORM_BRANCH, MSG_WIZARD_CREATE_BRANCH, MSG_GENRE_LABEL, MSG_WIZARD_SUBGENRE_LABEL, MSG_WIZARD_CHOOSE, MSG_NAME_LABEL):
            self.assertIn(name, text)
        self.assertIn(MSG_WIZARD_NEEDS_GENRE, text)
        await self.go_to_branch(FORM_PLACE)
        self.assertIn(MSG_WIZARD_CHOOSE_FIRST, self.text())
        self.assertNotIn(MSG_WIZARD_SUBGENRE_LABEL, self.text())

    async def test_the_new_song_is_named_as_the_tracker_names_a_new_thing(self):
        self.assertEqual(self.wizard().song_name(), new_name(word=MSG_NEW_SONG_WORD, taken=[MSG_DEFAULT_SONG_NAME]))
        self.assertIn(self.wizard().song_name(), self.text())

    async def test_the_cursor_stops_at_both_ends_of_the_tree(self):
        await self.press(Key.UP)
        self.assertEqual(self.wizard().tree_place, GENRE_PLACE)
        await self.press(*[Key.DOWN] * 5)
        self.assertEqual(self.wizard().tree_place, CREATE_PLACE)

    async def test_enter_and_tab_move_into_the_fields_and_esc_and_tab_move_back(self):
        for into, back in ((Key.ENTER, Key.ESCAPE), (Key.TAB, Key.TAB)):
            await self.press(into)
            self.assertTrue(self.wizard().in_fields)
            self.assertIn(MSG_WIZARD_EDITED_BRANCH, self.text())
            await self.press(back)
            self.assertIsInstance(self.wizard(), WizardPage)
            self.assertFalse(self.wizard().in_fields)
            self.assertNotIn(MSG_WIZARD_EDITED_BRANCH, self.text())

    async def test_the_subgenre_refuses_until_a_genre_is_chosen(self):
        await self.press(keybindings.WizardPage.INTO_FIELDS, Key.DOWN, Key.ENTER)
        self.assertIn(ERR_WIZARD_CHOOSE_GENRE, self.text())
        self.assertIsNone(self.choices().get_subgenre())

    async def test_a_genre_is_picked_from_a_list_of_every_genre_by_title(self):
        await self.press(keybindings.WizardPage.INTO_FIELDS, Key.ENTER)
        for genre in genre_names():
            self.assertIn(genre_title(genre), self.text())
        await self.press(Key.DOWN, Key.ENTER)
        self.assertEqual(self.choices().get_genre(), genre_names()[1])
        self.assertIn(genre_title(genre_names()[1]), self.text())

    async def test_choosing_a_subgenre_fills_in_the_key_the_scale_and_the_tempo_which_can_be_changed(self):
        await self.choose_genre_and_subgenre()
        choices = self.choices()
        self.assertEqual(choices.get_genre(), genre_names()[0])
        self.assertEqual(choices.get_subgenre(), choices.subgenres()[0])
        text = self.text()
        for label in (MSG_WIZARD_KEY_LABEL, MSG_SCALE_LABEL, MSG_TEMPO_LABEL):
            self.assertIn(label, text)
        lowest, highest = choices.tempo_range()
        self.assertIn(str(lowest), text)
        self.assertIn(str(highest), text)
        tempo = choices.get_tempo()
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_TEMPO_LABEL)
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(choices.get_tempo(), tempo + 1)
        await self.select_field(MSG_SCALE_LABEL)
        await self.press(Key.ENTER, Key.DOWN, Key.ENTER)
        self.assertEqual(choices.get_scale_type(), MINOR)
        self.assertIn(MSG_WIZARD_SCALE_TYPE_NAMES[MINOR], self.text())

    async def test_choosing_another_genre_leaves_the_subgenre_to_be_chosen_again(self):
        await self.choose_genre_and_subgenre()
        await self.press(keybindings.WizardPage.INTO_FIELDS, key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.choices().get_genre(), genre_names()[1])
        self.assertIsNone(self.choices().get_subgenre())
        self.assertIn(MSG_WIZARD_CHOOSE, self.text())

    async def test_the_song_is_named_on_the_genre_branch_and_a_name_in_use_is_refused(self):
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_NAME_LABEL)
        await self.press(Key.ENTER, *[Key.BACKSPACE] * len(self.wizard().song_name()))
        await self.type(A_SONG_NAME)
        await self.press(Key.ENTER)
        self.assertEqual(self.wizard().song_name(), A_SONG_NAME)
        await self.press(Key.ENTER, *[Key.BACKSPACE] * len(A_SONG_NAME))
        await self.type(MSG_DEFAULT_SONG_NAME)
        await self.press(Key.ENTER)
        self.assertEqual(self.wizard().song_name(), A_SONG_NAME)

    async def test_the_form_branch_picks_a_form_lists_its_sections_and_opens_to_a_branch_for_each(self):
        await self.choose_genre_and_subgenre()
        await self.go_to_branch(FORM_PLACE)
        choices = self.choices()
        sections = choices.form_sections()
        text = self.text()
        self.assertIn(MSG_WIZARD_FORM_LABEL, text)
        self.assertIn(MSG_WIZARD_BRANCH_CLOSED, text)
        for name in sections:
            self.assertIn(name, text)
        self.assertEqual(len(self.wizard().rows()), CREATE_PLACE + 1)
        await self.press(Key.RIGHT)
        self.assertIn(MSG_WIZARD_BRANCH_OPEN, self.text())
        self.assertEqual(len(self.wizard().rows()), CREATE_PLACE + 1 + len(sections))
        await self.press(Key.DOWN)
        self.assertEqual(self.wizard().branch().name(), sections[0])
        self.assertIn(MSG_WIZARD_BARS_LABEL, self.text())
        # A section is only read, so ENTER has nothing to move into, and Left goes back to the Form branch, where Left closes it.
        await self.press(Key.ENTER)
        self.assertFalse(self.wizard().in_fields)
        await self.press(Key.DOWN, Key.LEFT)
        self.assertEqual(self.wizard().branch().name(), MSG_WIZARD_FORM_BRANCH)
        await self.press(Key.LEFT)
        self.assertEqual(len(self.wizard().rows()), CREATE_PLACE + 1)

    async def test_another_form_changes_the_sections(self):
        await self.choose_genre_and_subgenre()
        await self.go_to_branch(FORM_PLACE)
        forms = self.choices().forms()
        self.assertGreater(len(forms), 1)
        self.assertEqual(self.choices().get_form(), forms[0])
        await self.press(keybindings.WizardPage.INTO_FIELDS, key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.choices().get_form(), forms[1])

    async def test_create_refuses_until_a_genre_and_a_subgenre_are_chosen(self):
        before = self.document.setlist().to_data()
        await self.go_to_branch(CREATE_PLACE)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        self.assertFalse(self.wizard().in_fields)
        self.assertIn(ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE, self.text())
        self.assertEqual(self.document.setlist().to_data(), before)

    async def test_create_adds_the_song_with_all_it_uses_makes_it_current_and_shows_arrange(self):
        patterns = self.document.setlist().get_pattern_names()
        await self.choose_genre_and_subgenre()
        name = self.wizard().song_name()
        kept = self.choices().to_data()
        await self.create()
        self.assertIsInstance(self.app.screen, ArrangePage)
        self.assertEqual([type(page) for page in self.app.pages()], [MainPage, ArrangePage])
        self.assertEqual(self.document.current_song_name(), name)
        self.assertEqual(self.document.song_names(), [MSG_DEFAULT_SONG_NAME, name])
        self.assertIn(MSG_WIZARD_CREATED.format(name=name), self.text())
        song = self.document.song()
        self.assertTrue(song.get_scenes())
        self.assertGreater(len(self.document.setlist().get_pattern_names()), len(patterns))
        # The song keeps what the wizard was told, with the seed drawn for it.
        self.assertEqual({field: value for field, value in song.get_wizard_choices().items() if field in kept}, kept)
        self.assertTrue(self.document.is_dirty())

    async def test_a_second_song_of_the_same_choices_gets_a_name_of_its_own_and_touches_nothing_of_the_first(self):
        await self.choose_genre_and_subgenre()
        await self.create()
        first = self.document.current_song_name()
        first_data = self.document.setlist().get_item(section=Section.SONGS, name=first).to_data()
        await self.press(keybindings.Page.WIZARD)
        await self.choose_genre_and_subgenre()
        second = self.wizard().song_name()
        self.assertNotEqual(first, second)
        await self.create()
        self.assertEqual(self.document.song_names(), [MSG_DEFAULT_SONG_NAME, first, second])
        self.assertEqual(self.document.setlist().get_item(section=Section.SONGS, name=first).to_data(), first_data)

    async def test_esc_in_the_tree_closes_at_once_with_nothing_chosen(self):
        await self.press(keybindings.WizardPage.INTO_FIELDS, keybindings.WizardPage.TO_TREE, Key.ESCAPE)
        self.assertIsInstance(self.app.screen, MainPage)

    async def test_esc_in_the_tree_asks_once_something_is_chosen_and_no_keeps_the_wizard(self):
        await self.choose_genre_and_subgenre()
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn(MSG_WIZARD_CLOSE_QUESTION, self.text())
        await self.press(keybindings.ConfirmDialog.NO)
        self.assertIsInstance(self.app.screen, WizardPage)
        self.assertEqual(self.choices().get_genre(), genre_names()[0])
        await self.press(Key.ESCAPE, keybindings.ConfirmDialog.YES)
        self.assertIsInstance(self.app.screen, MainPage)

    async def test_the_wizard_fits_an_80_by_24_console_with_a_long_form_open(self):
        await self.choose_genre_and_subgenre()
        await self.go_to_branch(FORM_PLACE)
        await self.press(Key.RIGHT, *[Key.DOWN] * 30)
        self.assertEqual(self.wizard().branch().name(), MSG_WIZARD_CREATE_BRANCH)
        self.assertIn(MSG_WIZARD_CREATE_BRANCH, self.text())


class TestWizardPageUndo(WizardTest):
    """Undo and the wizard, the user's design: nothing to undo while it is open, and Create is one step."""

    async def test_undo_and_redo_do_nothing_in_the_wizard_and_say_why(self):
        await self.choose_genre_and_subgenre()
        chosen = self.choices().to_data()
        for key in (keybindings.Page.UNDO, keybindings.Page.REDO):
            await self.press(key)
            self.assertIsInstance(self.app.screen, WizardPage)
            self.assertIn(MSG_WIZARD_NOTHING_TO_UNDO, self.text())
            self.assertEqual(self.choices().to_data(), chosen)

    async def test_create_is_one_step_which_undo_takes_away_whole_and_redo_brings_back(self):
        before = self.document.setlist().to_data()
        await self.choose_genre_and_subgenre()
        name = self.wizard().song_name()
        await self.create()
        after = self.document.setlist().to_data()
        self.assertNotEqual(before, after)
        await self.press(keybindings.Page.UNDO)
        self.assertEqual(self.document.setlist().to_data(), before)
        self.assertEqual(self.document.current_song_name(), MSG_DEFAULT_SONG_NAME)
        self.assertIsInstance(self.app.screen, ArrangePage)
        self.assertIn(fixed_text(MSG_UNDONE), self.text())
        await self.press(keybindings.Page.REDO)
        self.assertEqual(self.document.setlist().to_data(), after)
        self.assertEqual(self.document.current_song_name(), name)
        self.assertIn(fixed_text(MSG_RESTORED), self.text())
