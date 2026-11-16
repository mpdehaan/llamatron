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
from llamatron.macro_composer.arranger import BARS, WITHOUT
from llamatron.macro_composer.breaks import LEAST_CUT, MOST_CUT, break_names
from llamatron.macro_composer.melody import DEFAULT_GAUGES, GAUGE_MOVES, HIGHEST_GAUGE, SMART
from llamatron.macro_composer.wizard_choices import USUAL_PIECE_NOTE, FEWEST_FILLS, MOST_FILLS, ONE_GUITARIST_COUNT, TWO_GUITARISTS, ACOUSTIC, BAND_SOUNDS, FILLS_TRAITS, PROGRESSION_TRAITS, MOST_BUSY, USUAL_BUSY, MINOR, SEED, genre_names, genre_title
from llamatron.strings.errors import ERR_WIZARD_LAST_PIECE, ERR_WIZARD_LAST_PLAYER, ERR_WIZARD_LAST_SECTION, ERR_WIZARD_SECTION_NEEDS_PLAYER, ERR_WIZARD_CHOOSE_GENRE, ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE
from llamatron.strings.labels import MSG_GM_SOUNDS, MSG_WIZARD_KIT_DRUMS, MSG_GM_FAMILIES, MSG_WIZARD_BREAK_CUT_LABEL, MSG_WIZARD_BREAK_LABEL, MSG_WIZARD_GAUGE_ENDS, MSG_WIZARD_GAUGE_LABELS, MSG_WIZARD_NO_BREAK, MSG_WIZARD_ANY_PROGRESSION, MSG_WIZARD_DRUM_FILLS_LABEL, MSG_WIZARD_FILLS_COME, MSG_WIZARD_QUIET_NOTES_LABEL, MSG_WIZARD_KIT_PIECE, MSG_WIZARD_GUITARISTS_LABEL, MSG_WIZARD_MORE_SOUNDS, MSG_WIZARD_SOUND_LABEL, MSG_WIZARD_SOUNDS_LABEL, MSG_WIZARD_FILLS_LABEL, MSG_WIZARD_MELODY_LABEL, MSG_WIZARD_PLAYING_BRANCH, MSG_WIZARD_PROGRESSION_LABEL, MSG_WIZARD_THEMES_BRANCH, MSG_WIZARD_USUAL_MELODY, MSG_WIZARD_ADD_SECTION_TITLE, MSG_WIZARD_INSERT_SECTION_TITLE, MSG_WIZARD_SUGGESTED_FORM_BUTTON, MSG_WIZARD_KIND_LABEL, MSG_WIZARD_BAND_BRANCH, MSG_WIZARD_BUSY_LABEL, MSG_WIZARD_PLAYS_LABEL, MSG_GENRE_LABEL, MSG_NAME_LABEL, MSG_SCALE_LABEL, MSG_TEMPO_LABEL, MSG_WIZARD_BARS_LABEL, MSG_WIZARD_CREATE_BRANCH, MSG_WIZARD_FORM_BRANCH, MSG_WIZARD_FORM_LABEL, MSG_WIZARD_GENRE_BRANCH, MSG_WIZARD_KEY_LABEL, MSG_WIZARD_LENGTH_LABEL, MSG_WIZARD_METER_LABEL, MSG_WIZARD_SCALE_TYPE_NAMES, MSG_WIZARD_START_NAMES, MSG_WIZARD_START_TITLE, MSG_WIZARD_SUBGENRE_LABEL, MSG_WIZARD_CREATE_BUTTON, MSG_WIZARD_START_CANCEL
from llamatron.strings.legends import What
from llamatron.strings.marks import MSG_SOUND_NOTE_ROW, MSG_TOGGLE_ON, MSG_WIZARD_KIT_DRUM_SHOWN, MSG_WIZARD_OWN_DRUM_SHOWN, MSG_WIZARD_SOUND_ON_NOTE, MSG_WIZARD_MELODY_GAUGE_SHOWN, MSG_WIZARD_BAND_SOUND_SHOWN, MSG_WIZARD_FROM_BAND, MSG_WIZARD_CARRIED, MSG_WIZARD_SECTION_NUMBERED, MSG_WIZARD_SUGGESTED_FORM, MSG_WIZARD_OWN_FORM, MSG_WIZARD_GAUGE_EMPTY, MSG_WIZARD_GAUGE_FULL, MSG_WIZARD_BRANCH_CLOSED, MSG_WIZARD_BRANCH_OPEN, MSG_WIZARD_CHOOSE, MSG_WIZARD_EDITED_BRANCH, MSG_WIZARD_NEEDS_GENRE
from llamatron.strings.messages import MSG_WIZARD_NOTHING_TO_CHOOSE, MSG_WIZARD_MOVING, MSG_WIZARD_REPLACE_SECTIONS_QUESTION, MSG_WIZARD_SECTIONS_HINT, MSG_UNDONE, MSG_RESTORED, MSG_WIZARD_ALREADY_OPEN, MSG_WIZARD_CLOSE_QUESTION, MSG_WIZARD_CREATED, MSG_WIZARD_CHOOSE_FIRST, MSG_WIZARD_REPLACED, MSG_WIZARD_NOTHING_TO_UNDO
from llamatron.strings.names import MSG_DEFAULT_SONG_NAME, MSG_NEW_SONG_WORD
from llamatron.composition.naming import new_name
from llamatron.tui import keybindings
from llamatron.tui.app import LlamatronApp
from llamatron.tui.document import Document
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.composition.limits import GM_FAMILY_SIZE, MAX_GM_SOUND, MIN_GM_SOUND
from llamatron.tui.note_names import note_shown, note_typed
from llamatron.tui.dialogs.sound_dialog import SoundDialog
from llamatron.tui.keys import Key
from llamatron.tui.text import clock
from llamatron.tui.screens.arrange.arrange_page import ArrangePage
from llamatron.tui.screens.set.main_page import MainPage
from llamatron.tui.screens.set.songs_page import SongsPage
from llamatron.tui.screens.wizard.starts import NEW_FROM_LAST, NEW_FROM_SCRATCH, REPLACE_FROM_LAST, REPLACE_FROM_SCRATCH, STARTS
from llamatron.tui.screens.wizard.wizard_page import WizardPage
from tests.support.ui_testing import UITest, back_key, fixed_text, forward_key, key_of

# The tree's branches by their places from the top, while none is open.
GENRE_PLACE = 0
FORM_PLACE = 3
CREATE_PLACE = 5
# A name the test gives the song.
A_SONG_NAME = 'anthem'
A_NOTE_TYPED = 'f#2'
A_GENRE_WITH_RHYTHMS = 'rock'


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

    async def go_to_named_branch(self, name):
        """Move the tree's cursor to a top branch by its name, wherever the Start branch has put it."""
        await self.go_to_branch([branch.name() for _, branch in self.wizard().rows()].index(name))

    async def choose_genre_and_subgenre(self):
        """Choose the first genre and its first subgenre, each with ] (inc) from nothing chosen, and go back to the tree."""
        await self.go_to_named_branch(MSG_WIZARD_GENRE_BRANCH)
        more = key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET)
        await self.press(keybindings.WizardPage.INTO_FIELDS, more, Key.DOWN, more, keybindings.WizardPage.TO_TREE)

    async def create(self):
        """Press the Create button, the last row of the Create branch."""
        await self.go_to_named_branch(MSG_WIZARD_CREATE_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_CREATE_BUTTON)
        await self.press(Key.ENTER)

    async def start_with(self, start):
        """Choose one of the four ways to start in the dialog that F5 opens on a song the wizard made, which then opens the wizard."""
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        await self.press(*[Key.DOWN] * STARTS.index(start), Key.ENTER)

    async def make_a_song_and_open_the_wizard_on_it(self):
        """Make a song with the wizard, which becomes current, and press F5 again, which asks how to start; return the song's name."""
        await self.choose_genre_and_subgenre()
        await self.create()
        await self.press(keybindings.Page.WIZARD)
        return self.document.current_song_name()

    def song_data(self, name):
        return self.document.setlist().get_item(section=Section.SONGS, name=name).to_data()


class TestWizardPage(WizardTest):

    async def test_f5_opens_the_wizard_from_any_page_with_the_cursor_in_the_tree_on_genre(self):
        self.assertIsInstance(self.wizard(), WizardPage)
        self.assertFalse(self.wizard().in_fields)
        self.assertEqual(self.wizard().branch().name(), MSG_WIZARD_GENRE_BRANCH)
        await self.press(Key.ESCAPE, keybindings.MainPage.SONGS, keybindings.Page.WIZARD)
        self.assertIsInstance(self.wizard(), WizardPage)
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, SongsPage)

    async def test_f5_in_the_wizard_says_the_wizard_is_open(self):
        await self.press(keybindings.Page.WIZARD)
        self.assertIsInstance(self.wizard(), WizardPage)
        self.assertEqual(len(self.app.pages()), 2)
        self.assertIn(MSG_WIZARD_ALREADY_OPEN, self.text())

    async def test_the_tree_lists_genre_form_and_create_and_the_fields_of_the_branch_under_the_cursor_show(self):
        text = self.text()
        for name in (MSG_WIZARD_GENRE_BRANCH, MSG_WIZARD_FORM_BRANCH, MSG_WIZARD_CREATE_BRANCH, MSG_GENRE_LABEL, MSG_WIZARD_SUBGENRE_LABEL, MSG_WIZARD_CHOOSE, MSG_NAME_LABEL):
            self.assertIn(name, text)
        self.assertIn(MSG_WIZARD_NEEDS_GENRE, text)
        await self.go_to_named_branch(MSG_WIZARD_FORM_BRANCH)
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

    async def test_the_meter_is_shown_and_stepping_the_length_chooses_a_longer_or_a_shorter_form(self):
        await self.choose_genre_and_subgenre()
        choices = self.choices()
        self.assertIn(choices.meter(), self.text())
        self.assertIn(clock(choices.form_seconds()), self.text())
        forms = choices.forms_by_length()
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_LENGTH_LABEL)
        back = key_of(binding=keybindings.WizardPage.LESS, key=Key.LEFT_BRACKET)
        await self.press(*[back] * len(forms))
        self.assertEqual(choices.get_form(), forms[0])
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(choices.get_form(), forms[1])
        self.assertIn(clock(choices.form_seconds()), self.text())
        # The meter is the subgenre's, so its field does nothing.
        await self.select_field(MSG_WIZARD_METER_LABEL)
        before = choices.to_data()
        await self.press(Key.ENTER, back)
        self.assertEqual(choices.to_data(), before)

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
        await self.go_to_named_branch(MSG_WIZARD_FORM_BRANCH)
        choices = self.choices()
        sections = choices.form_sections()
        text = self.text()
        self.assertIn(MSG_WIZARD_FORM_LABEL, text)
        # The Form branch starts open, so that the sections show themselves.
        self.assertIn(MSG_WIZARD_BRANCH_OPEN, text)
        self.assertIn(MSG_WIZARD_SECTIONS_HINT, text)
        for name in sections:
            self.assertIn(name, text)
        self.assertEqual(len(self.wizard().rows()), CREATE_PLACE + 1 + len(choices.roles_in()) + len(sections))
        await self.press(Key.DOWN)
        self.assertEqual(self.wizard().branch().name(), sections[0])
        self.assertIn(MSG_WIZARD_BARS_LABEL, self.text())
        # ENTER moves into a section's settings and ESC back; Left goes back to the Form branch, where Left closes it.
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        self.assertTrue(self.wizard().in_fields)
        await self.press(Key.ESCAPE, Key.DOWN, Key.LEFT)
        self.assertEqual(self.wizard().branch().name(), MSG_WIZARD_FORM_BRANCH)
        await self.press(Key.LEFT)
        self.assertEqual(len(self.wizard().rows()), CREATE_PLACE + 1 + len(choices.roles_in()))
        self.assertIn(MSG_WIZARD_BRANCH_CLOSED, self.text())
        await self.press(Key.RIGHT)
        self.assertEqual(len(self.wizard().rows()), CREATE_PLACE + 1 + len(choices.roles_in()) + len(sections))

    async def test_a_suggested_form_is_picked_from_a_dialog_that_says_each_forms_sections_and_length(self):
        await self.choose_genre_and_subgenre()
        await self.go_to_named_branch(MSG_WIZARD_FORM_BRANCH)
        choices = self.choices()
        forms = choices.forms()
        self.assertGreater(len(forms), 1)
        self.assertEqual(choices.get_form(), forms[0])
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_SUGGESTED_FORM_BUTTON)
        # No key steps the form, which only the dialog changes.
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET), Key.RIGHT, Key.DOWN)
        self.assertEqual(choices.get_form(), forms[0])
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        for form in forms:
            self.assertIn(MSG_WIZARD_SUGGESTED_FORM.format(form=form, count=choices.form_section_count(form), length=clock(choices.form_seconds(form=form))), self.text())
        await self.press(Key.ESCAPE)
        self.assertEqual(choices.get_form(), forms[0])
        await self.press(Key.ENTER, Key.DOWN, Key.ENTER)
        self.assertEqual(choices.get_form(), forms[1])

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

    async def test_create_turns_real_time_on_so_that_the_song_can_be_played_and_undo_turns_it_off_again(self):
        self.assertFalse(self.document.setlist().is_real_time())
        await self.choose_genre_and_subgenre()
        await self.create()
        self.assertTrue(self.document.setlist().is_real_time())
        await self.press(keybindings.Page.UNDO)
        self.assertFalse(self.document.setlist().is_real_time())

    async def test_a_second_song_of_the_same_choices_gets_a_name_of_its_own_and_touches_nothing_of_the_first(self):
        await self.choose_genre_and_subgenre()
        await self.create()
        first = self.document.current_song_name()
        first_data = self.document.setlist().get_item(section=Section.SONGS, name=first).to_data()
        await self.press(keybindings.Page.WIZARD)
        await self.start_with(NEW_FROM_SCRATCH)
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
        await self.go_to_named_branch(MSG_WIZARD_FORM_BRANCH)
        await self.press(Key.RIGHT, *[Key.DOWN] * 30)
        self.assertEqual(self.wizard().branch().name(), MSG_WIZARD_CREATE_BRANCH)
        self.assertIn(MSG_WIZARD_CREATE_BRANCH, self.text())


class TestWizardBand(WizardTest):
    """The Band branch: a toggle for each player, and a branch for each player who is in."""

    async def open_the_band(self):
        await self.choose_genre_and_subgenre()
        await self.go_to_named_branch(MSG_WIZARD_BAND_BRANCH)

    async def test_the_band_waits_for_a_genre_and_a_subgenre(self):
        await self.go_to_named_branch(MSG_WIZARD_BAND_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        self.assertFalse(self.wizard().in_fields)
        self.assertIn(ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE, self.text())

    async def test_the_band_lists_every_player_and_opens_to_a_branch_for_each_who_is_in(self):
        await self.open_the_band()
        choices = self.choices()
        self.assertEqual([field.label for field in self.wizard().fields()], [MSG_WIZARD_SOUNDS_LABEL, *(choices.role_title(role) for role in choices.roles() if choices.role_can_play(role))])
        # The Band starts open: Left closes it and Right opens it to a branch for each player who is in.
        rows = len(self.wizard().rows())
        await self.press(Key.LEFT)
        self.assertEqual(len(self.wizard().rows()), rows - len(choices.roles_in()))
        await self.press(Key.RIGHT)
        self.assertEqual(len(self.wizard().rows()), rows)
        await self.press(Key.DOWN)
        self.assertEqual(self.wizard().branch().name(), choices.role_title(choices.roles_in()[0]))

    async def test_a_toggle_leaves_a_player_out_and_puts_the_player_back_and_the_last_player_stays(self):
        await self.open_the_band()
        choices = self.choices()
        players = choices.roles_in()
        await self.press(Key.RIGHT, keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(choices.role_title(players[0]))
        await self.press(Key.SPACE)
        self.assertEqual(choices.roles_in(), players[1:])
        self.assertNotIn(choices.role_title(players[0]), [branch.name() for _, branch in self.wizard().rows()])
        await self.press(Key.ENTER)
        self.assertEqual(choices.roles_in(), players)
        for player in players[:-1]:
            await self.select_field(choices.role_title(player))
            await self.press(Key.SPACE)
        await self.select_field(choices.role_title(players[-1]))
        await self.press(Key.SPACE)
        self.assertEqual(choices.roles_in(), players[-1:])
        self.assertIn(ERR_WIZARD_LAST_PLAYER, self.text())

    async def test_a_players_branch_chooses_how_the_player_plays_and_how_busy_shown_as_a_gauge(self):
        await self.open_the_band()
        choices = self.choices()
        player = next(role for role in choices.roles_in() if choices.has_busy(role) and len(choices.role_traits(role)) == 1)
        trait = choices.role_traits(player)[0]
        ways = choices.ways(role=player, trait=trait)
        await self.press(Key.RIGHT, *[Key.DOWN] * (choices.roles_in().index(player) + 1))
        self.assertEqual(self.wizard().branch().name(), choices.role_title(player))
        text = self.text()
        self.assertIn(MSG_WIZARD_BUSY_LABEL, text)
        self.assertIn(MSG_WIZARD_GAUGE_FULL * USUAL_BUSY + MSG_WIZARD_GAUGE_EMPTY * (MOST_BUSY - USUAL_BUSY), text)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_PLAYS_LABEL)
        await self.press(Key.ENTER)
        for way in ways:
            self.assertIn(way, self.text())
        await self.press(Key.ESCAPE)
        more = key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET)
        await self.select_field(MSG_WIZARD_BUSY_LABEL)
        await self.press(*[more] * MOST_BUSY)
        self.assertEqual(choices.get_busy(player), MOST_BUSY)
        self.assertIn(MSG_WIZARD_GAUGE_FULL * MOST_BUSY, self.text())

    async def test_the_song_made_has_the_band_chosen(self):
        await self.open_the_band()
        choices = self.choices()
        out = choices.roles_in()[0]
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(choices.role_title(out))
        await self.press(Key.SPACE, keybindings.WizardPage.TO_TREE)
        await self.create()
        self.assertNotIn(out, self.document.song().get_track_names())
        self.assertEqual(self.document.song().get_wizard_choices()[WITHOUT], [out])


class TestWizardSounds(WizardTest):
    """The band's Sounds, which every player follows, and a player's own Sound, which overrides it."""

    async def open_a_player(self):
        """Choose a genre and a subgenre, open the Band and put the tree's cursor on the first player whose sound can be chosen."""
        await self.choose_genre_and_subgenre()
        await self.go_to_named_branch(MSG_WIZARD_BAND_BRANCH)
        choices = self.choices()
        role = [role for role in choices.roles_in() if choices.has_sound(role)][0]
        await self.press(Key.RIGHT, *[Key.DOWN] * (choices.roles_in().index(role) + 1))
        return role

    async def test_the_bands_sounds_are_stepped_and_a_player_shows_the_bands_sound_as_the_bands(self):
        role = await self.open_a_player()
        choices = self.choices()
        self.assertIn(MSG_WIZARD_BAND_SOUND_SHOWN.format(sound=choices.sound_name(choices.get_sound(role))), self.text())
        await self.go_to_named_branch(MSG_WIZARD_BAND_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_SOUNDS_LABEL)
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET), keybindings.WizardPage.TO_TREE)
        self.assertEqual(choices.get_band_sounds(), BAND_SOUNDS[1])
        self.assertEqual(BAND_SOUNDS[1], ACOUSTIC)

    async def test_a_players_sound_is_picked_from_the_genres_and_goes_back_to_the_bands(self):
        role = await self.open_a_player()
        choices = self.choices()
        own = choices.genre_sounds(role)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_SOUND_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertIn(MSG_WIZARD_FROM_BAND.format(sound=choices.sound_name(choices.band_sound(role))), self.text())
        self.assertIn(MSG_WIZARD_MORE_SOUNDS, self.text())
        await self.press(*[Key.UP] * (len(own) + 2), *[Key.DOWN] * len(own), Key.ENTER)
        self.assertTrue(choices.has_own_sound(role))
        self.assertEqual(choices.get_sound(role), own[-1])
        self.assertNotIn(MSG_WIZARD_BAND_SOUND_SHOWN.format(sound=choices.sound_name(own[-1])), self.text())
        await self.press(Key.ENTER, *[Key.UP] * (len(own) + 2), Key.ENTER)
        self.assertFalse(choices.has_own_sound(role))

    async def test_more_sounds_opens_every_general_midi_sound_by_family_and_the_song_made_plays_the_one_picked(self):
        role = await self.open_a_player()
        choices = self.choices()
        own = choices.genre_sounds(role)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_SOUND_LABEL)
        await self.press(Key.ENTER, *[Key.DOWN] * (len(own) + 2), Key.ENTER)
        dialog = self.app.screen
        self.assertIsInstance(dialog, SoundDialog)
        # Every family of General MIDI is offered, the last ones too, and a sound of the last can be taken.
        self.assertEqual([name for name, _ in dialog.groups], MSG_GM_FAMILIES)
        await self.press(*[Key.DOWN] * len(MSG_GM_FAMILIES), Key.ENTER, *[Key.DOWN] * GM_FAMILY_SIZE, Key.ENTER)
        picked = choices.get_sound(role)
        self.assertEqual(picked, MAX_GM_SOUND)
        self.assertTrue(choices.has_own_sound(role))
        await self.press(keybindings.WizardPage.TO_TREE)
        await self.create()
        setlist = self.document.setlist()
        instrument = setlist.get_instrument(self.document.song().get_track(role).get_instrument_name())
        self.assertEqual(instrument.get_gm_sound(), picked)


class TestWizardGuitarists(WizardTest):
    """The Band's Guitarists field: two guitarists, or one who is one player on the screen."""

    async def choose(self, *, offers):
        """Choose the first genre that offers one guitarist, or the first that does not, and go to the Band."""
        for genre in genre_names():
            choices = self.choices()
            choices.set_genre(genre)
            choices.set_subgenre(choices.subgenres()[0])
            if choices.offers_one_guitarist() == offers:
                break
        await self.go_to_named_branch(MSG_WIZARD_BAND_BRANCH)
        await self.press(Key.DOWN, Key.UP)

    async def test_one_guitarist_is_chosen_on_the_band_and_the_two_players_show_as_one(self):
        await self.choose(offers=True)
        choices = self.choices()
        await self.press(Key.RIGHT)
        rows = len(self.wizard().rows())
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_GUITARISTS_LABEL)
        # The count is shown as a number, and [ (dec) steps from 2 to 1.
        self.assertEqual(str(self.wizard().field().value()), str(TWO_GUITARISTS))
        await self.press(key_of(binding=keybindings.WizardPage.LESS, key=Key.LEFT_BRACKET), keybindings.WizardPage.TO_TREE)
        self.assertEqual(choices.get_guitarists(), ONE_GUITARIST_COUNT)
        self.assertEqual(len(self.wizard().rows()), rows - 1)
        self.assertEqual([field.label for field in self.wizard().fields()][2:], [choices.role_title(role) for role in choices.roles_shown() if choices.role_can_play(role)])
        await self.create()
        self.assertIsInstance(self.app.screen, ArrangePage)

    async def test_a_genre_with_no_guitar_solo_shows_no_guitarists_field(self):
        await self.choose(offers=False)
        self.assertNotIn(MSG_WIZARD_GUITARISTS_LABEL, self.text())


class TestWizardKit(WizardTest):
    """The drums' branch: a toggle for each piece of the kit."""

    async def open_the_drums(self):
        """Choose a genre and a subgenre, open the Band and put the tree's cursor on the drums, the last player."""
        await self.choose_genre_and_subgenre()
        await self.go_to_named_branch(MSG_WIZARD_BAND_BRANCH)
        choices = self.choices()
        await self.press(Key.RIGHT, *[Key.DOWN] * len([role for role in choices.roles_in() if role in choices.roles_shown()]))
        self.assertFalse(choices.has_sound(choices.roles_in()[-1]))

    async def test_a_piece_is_switched_off_and_on_and_the_last_piece_stays(self):
        await self.open_the_drums()
        choices = self.choices()
        pieces = choices.pieces()
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_KIT_PIECE.format(piece=pieces[0]))
        await self.press(Key.SPACE)
        self.assertFalse(choices.piece_is_on(pieces[0]))
        await self.press(Key.SPACE)
        self.assertTrue(choices.piece_is_on(pieces[0]))
        for piece in pieces:
            await self.select_field(MSG_WIZARD_KIT_PIECE.format(piece=piece))
            await self.press(Key.SPACE)
        self.assertTrue(choices.piece_is_on(pieces[-1]))
        self.assertIn(ERR_WIZARD_LAST_PIECE, self.text())

    async def test_a_break_is_chosen_on_the_drums_branch_and_takes_the_place_of_the_drums_other_ways(self):
        await self.open_the_drums()
        choices = self.choices()
        drums = choices.roles_in()[-1]
        self.assertEqual(choices.breaks(), break_names())
        before = choices.role_traits(drums)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_BREAK_LABEL)
        self.assertEqual(self.wizard().field().value(), MSG_WIZARD_NO_BREAK)
        self.assertNotIn(MSG_WIZARD_BREAK_CUT_LABEL, self.text())
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertIsNotNone(choices.get_break())
        self.assertIn(choices.get_break(), self.text())
        self.assertLess(len(choices.role_traits(drums)), len(before))
        # How far the break is cut up shows under a break chosen: a gauge that is empty for the break as written.
        await self.select_field(MSG_WIZARD_BREAK_CUT_LABEL)
        self.assertNotIn(MSG_WIZARD_GAUGE_FULL, self.wizard().field().value())
        await self.press(*[key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET)] * MOST_CUT)
        self.assertEqual(choices.get_break_cut(), MOST_CUT)
        self.assertNotIn(MSG_WIZARD_GAUGE_EMPTY, self.wizard().field().value())
        await self.press(*[key_of(binding=keybindings.WizardPage.LESS, key=Key.LEFT_BRACKET)] * MOST_CUT)
        self.assertEqual(choices.get_break_cut(), LEAST_CUT)

    async def test_a_piece_is_a_row_of_two_cells_and_left_and_right_move_between_them(self):
        await self.open_the_drums()
        choices = self.choices()
        piece = choices.pieces()[0]
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_KIT_PIECE.format(piece=piece))
        wizard = self.wizard()
        self.assertEqual([cell.value() for cell in wizard.field().cells], [MSG_TOGGLE_ON, MSG_WIZARD_OWN_DRUM_SHOWN.format(piece=piece)])
        # The row is come to at its first cell, where Space switches the piece off and on, and Left stays.
        await self.press(Key.LEFT)
        self.assertEqual(wizard.cell, 0)
        await self.press(Key.SPACE)
        self.assertFalse(choices.piece_is_on(piece))
        await self.press(Key.SPACE)
        self.assertTrue(choices.piece_is_on(piece))
        # Right moves to the sound, steps nothing, and stays at the last cell; Left moves back.
        await self.press(Key.RIGHT, Key.RIGHT)
        self.assertEqual(wizard.cell, 1)
        self.assertEqual(wizard.cell_field().enter_what, What.CHOOSE)
        self.assertTrue(choices.piece_is_on(piece))
        await self.press(Key.LEFT)
        self.assertEqual(wizard.cell, 0)
        # Another row is come to at its first cell again.
        await self.press(Key.RIGHT, Key.DOWN)
        self.assertEqual(wizard.cell, 0)

    async def test_a_piece_takes_another_drum_or_a_general_midi_sound_on_the_note_of_the_pickers_note_row(self):
        await self.open_the_drums()
        choices = self.choices()
        piece = choices.pieces()[0]
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_KIT_PIECE.format(piece=piece))
        wizard = self.wizard()
        # The picker opens from the sound's cell on the piece's own drum, above the kit's other drums and General MIDI's families.
        await self.press(Key.RIGHT, Key.ENTER)
        dialog = self.app.screen
        self.assertIsInstance(dialog, SoundDialog)
        self.assertEqual([name for name, _ in dialog.groups], [MSG_WIZARD_KIT_DRUMS, *MSG_GM_FAMILIES])
        self.assertNotIn(piece, [drum for _, drum in dialog.groups[0][1]])
        self.assertIn(MSG_SOUND_NOTE_ROW.format(note=note_shown(USUAL_PIECE_NOTE)), self.text())
        await self.press(Key.DOWN, Key.ENTER, Key.ENTER)
        drum = choices.piece_sound(piece)
        self.assertIn(drum, choices.kit_drums())
        self.assertEqual(wizard.cell_field().value(), MSG_WIZARD_KIT_DRUM_SHOWN.format(drum=drum))
        # A General MIDI sound plays the note of the picker's Note row, stepped there, and the cell shows both.
        await self.press(Key.ENTER, *[Key.DOWN] * (len(MSG_GM_FAMILIES) + 1), key_of(binding=keybindings.SoundDialog.NOTE_LESS, key=Key.LEFT_BRACKET))
        await self.press(*[Key.UP] * len(MSG_GM_FAMILIES), Key.ENTER, Key.ENTER)
        self.assertEqual((choices.piece_sound(piece), choices.piece_note(piece)), (MIN_GM_SOUND, USUAL_PIECE_NOTE - 1))
        self.assertEqual(wizard.cell_field().value(), MSG_WIZARD_SOUND_ON_NOTE.format(sound=MSG_GM_SOUNDS[0], note=note_shown(USUAL_PIECE_NOTE - 1)))
        # A note typed on the Note row and taken there keeps the sound and changes the note.
        await self.press(Key.ENTER, *[Key.DOWN] * (len(MSG_GM_FAMILIES) + 2))
        await self.type(A_NOTE_TYPED)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, SoundDialog)
        await self.press(Key.ENTER)
        self.assertEqual((choices.piece_sound(piece), choices.piece_note(piece)), (MIN_GM_SOUND, note_typed(A_NOTE_TYPED)))
        # Bksp on the sound's cell gives the piece its own drum back, and is offered only while the piece has another sound.
        await self.press(keybindings.WizardPage.CLEAR)
        self.assertIsNone(choices.piece_sound(piece))
        self.assertIsNone(wizard.cell_field().clear)

    async def test_how_often_fills_come_is_a_gauge_that_is_empty_at_never(self):
        await self.open_the_drums()
        choices = self.choices()
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_DRUM_FILLS_LABEL)
        await self.press(*[key_of(binding=keybindings.WizardPage.LESS, key=Key.LEFT_BRACKET)] * MOST_FILLS)
        self.assertEqual(choices.get_fills(), FEWEST_FILLS)
        shown = self.wizard().field().value()
        self.assertIn(MSG_WIZARD_FILLS_COME[0], shown)
        self.assertNotIn(MSG_WIZARD_GAUGE_FULL, shown)
        await self.press(*[key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET)] * MOST_FILLS)
        self.assertEqual(choices.get_fills(), MOST_FILLS)
        shown = self.wizard().field().value()
        self.assertIn(MSG_WIZARD_FILLS_COME[-1], shown)
        self.assertNotIn(MSG_WIZARD_GAUGE_EMPTY, shown)

    async def test_quiet_notes_show_only_for_a_groove_that_has_them_and_are_switched_off(self):
        await self.open_the_drums()
        choices = self.choices()
        drums = choices.roles_in()[-1]
        with_them = [(trait, way) for trait in choices.role_traits(drums) for way in choices.ways(role=drums, trait=trait) if self.has_quiet_notes_with(trait=trait, way=way)]
        without = [(trait, way) for trait in choices.role_traits(drums) for way in choices.ways(role=drums, trait=trait) if not self.has_quiet_notes_with(trait=trait, way=way)]
        if without:
            choices.set_way(trait=without[0][0], value=without[0][1])
        if not choices.has_quiet_notes():
            await self.press(Key.UP, Key.DOWN)
            self.assertNotIn(MSG_WIZARD_QUIET_NOTES_LABEL, self.text())
        choices.set_way(trait=with_them[0][0], value=with_them[0][1])
        await self.press(Key.UP, Key.DOWN, keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_QUIET_NOTES_LABEL)
        await self.press(Key.SPACE)
        self.assertFalse(choices.plays_quiet_notes())
        # The toggle stays while the quiet notes are off, so that they can be switched on again.
        self.assertIn(MSG_WIZARD_QUIET_NOTES_LABEL, self.text())

    def has_quiet_notes_with(self, *, trait, way):
        choices = self.choices().__class__.from_data(self.choices().to_data())
        choices.set_way(trait=trait, value=way)
        return choices.has_quiet_notes()

    async def test_the_song_made_has_no_track_for_a_piece_switched_off(self):
        await self.open_the_drums()
        piece = self.choices().pieces()[-1]
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_KIT_PIECE.format(piece=piece))
        await self.press(Key.SPACE, keybindings.WizardPage.TO_TREE)
        await self.create()
        self.assertNotIn(piece, self.document.song().get_track_names())


class TestWizardForm(WizardTest):
    """The Form branch: the sections as branches, added, copied, removed and moved with a list's keys, and each section's settings."""

    async def open_the_form(self):
        """Choose a genre and a subgenre, open the Form branch and put the tree's cursor on its first section."""
        await self.choose_genre_and_subgenre()
        await self.go_to_named_branch(MSG_WIZARD_FORM_BRANCH)
        await self.press(Key.RIGHT, Key.DOWN)

    def sections(self):
        return self.choices().form_sections()

    async def test_down_from_the_form_reaches_each_section_in_order(self):
        await self.choose_genre_and_subgenre()
        await self.go_to_named_branch(MSG_WIZARD_FORM_BRANCH)
        # A kind the form has several of is numbered, and one it has once is not.
        labels = self.choices().section_labels()
        kinds = self.sections()
        repeated = [kind for kind in kinds if kinds.count(kind) > 1][0]
        self.assertEqual([label for label in labels if label.startswith(repeated)][:2], [MSG_WIZARD_SECTION_NUMBERED.format(kind=repeated, number=number) for number in (1, 2)])
        self.assertIn(kinds[0], labels)
        for name in labels:
            await self.press(Key.DOWN)
            self.assertEqual(self.wizard().branch().name(), name)

    async def test_insert_on_a_section_asks_the_kind_and_puts_the_new_section_before_it_under_the_cursor(self):
        await self.open_the_form()
        await self.press(Key.DOWN)
        before = self.sections()
        kinds = self.choices().section_kinds()
        await self.press(keybindings.WizardPage.INSERT)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertIn(MSG_WIZARD_INSERT_SECTION_TITLE, self.text())
        await self.press(*[Key.DOWN] * (len(kinds) - 1), Key.ENTER)
        self.assertEqual(self.sections(), [before[0], kinds[-1], *before[1:]])
        self.assertEqual(self.wizard().branch().name(), self.choices().section_labels()[1])
        self.assertTrue(self.choices().has_own_form())

    async def test_add_on_a_section_puts_the_new_section_at_the_end_and_leaves_the_cursor(self):
        await self.open_the_form()
        before = self.sections()
        await self.press(keybindings.WizardPage.ADD)
        self.assertIn(MSG_WIZARD_ADD_SECTION_TITLE, self.text())
        await self.press(Key.ENTER)
        self.assertEqual(self.sections(), [*before, self.choices().section_kinds()[0]])
        self.assertEqual(self.wizard().branch().name(), self.choices().section_labels()[0])

    async def test_add_on_the_form_puts_the_new_section_at_the_end_and_esc_adds_nothing(self):
        await self.choose_genre_and_subgenre()
        await self.go_to_named_branch(MSG_WIZARD_FORM_BRANCH)
        before = self.sections()
        await self.press(keybindings.WizardPage.ADD, Key.ESCAPE)
        self.assertEqual(self.sections(), before)
        await self.press(keybindings.WizardPage.ADD, Key.ENTER)
        self.assertEqual(self.sections(), [*before, self.choices().section_kinds()[0]])
        # The form opens to show what was added.
        self.assertGreater(len(self.wizard().rows()), len(before))

    async def test_copy_puts_a_copy_after_the_section_and_delete_removes_one_until_the_last(self):
        await self.open_the_form()
        before = self.sections()
        await self.press(keybindings.WizardPage.COPY)
        self.assertEqual(self.sections(), [before[0], *before])
        await self.press(keybindings.WizardPage.DELETE)
        self.assertEqual(self.sections(), before)
        await self.press(*[keybindings.WizardPage.DELETE] * len(before))
        self.assertEqual(len(self.sections()), 1)
        self.assertIn(ERR_WIZARD_LAST_SECTION, self.text())

    async def test_move_picks_a_section_up_carries_it_and_drops_it_and_only_those_keys_work_meanwhile(self):
        await self.open_the_form()
        before = self.sections()
        await self.press(keybindings.WizardPage.MOVE)
        self.assertIn(MSG_WIZARD_CARRIED.format(name=before[0]), self.text())
        self.assertIn(MSG_WIZARD_MOVING.format(name=before[0]), self.text())
        await self.press(forward_key(keybindings.WizardPage.CARRY), keybindings.WizardPage.COPY)
        self.assertEqual(self.sections(), [before[1], before[0], *before[2:]])
        self.assertEqual(self.wizard().branch().name(), before[0])
        # A carried section stops at the top of the form.
        await self.press(*[back_key(keybindings.WizardPage.CARRY)] * 3)
        self.assertEqual(self.sections(), before)
        await self.press(keybindings.WizardPage.DROP)
        self.assertFalse(self.wizard().moving)
        self.assertNotIn(MSG_WIZARD_CARRIED.format(name=before[0]), self.text())
        self.assertIsInstance(self.app.screen, WizardPage)

    async def test_a_sections_kind_and_bars_are_chosen_and_a_changed_section_gets_a_name_of_its_own(self):
        await self.open_the_form()
        await self.press(Key.DOWN)
        place = 1
        before = self.sections()
        offered = self.choices().bars_offered(place)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_BARS_LABEL)
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.choices().section_bars(place), offered[offered.index(self.choices()._usual(place)[BARS]) + 1])
        self.assertNotEqual(self.sections()[place], before[place])
        kinds = self.choices().section_kinds()
        await self.select_field(MSG_WIZARD_KIND_LABEL)
        await self.press(Key.ENTER, *[Key.UP] * len(kinds), Key.ENTER)
        self.assertEqual(self.choices().section_kind(place), kinds[0])

    async def test_a_player_sits_a_section_out_and_the_sections_last_player_stays(self):
        await self.open_the_form()
        place = 0
        players = self.choices().section_plays(place)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        for player in players:
            await self.select_field(self.choices().role_title(player))
            await self.press(Key.SPACE)
        self.assertEqual(len(self.choices().section_plays(place)), 1)
        self.assertIn(ERR_WIZARD_SECTION_NEEDS_PLAYER, self.text())

    async def test_a_form_of_the_songs_own_says_so_and_holds_the_length_until_a_suggested_form_is_chosen_again(self):
        await self.open_the_form()
        suggested = self.sections()
        await self.press(keybindings.WizardPage.COPY)
        await self.go_to_named_branch(MSG_WIZARD_FORM_BRANCH)
        self.assertIn(MSG_WIZARD_OWN_FORM, self.text())
        await self.go_to_named_branch(MSG_WIZARD_GENRE_BRANCH)
        self.assertIn(MSG_WIZARD_OWN_FORM, self.text())
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_LENGTH_LABEL)
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET), keybindings.WizardPage.TO_TREE)
        self.assertTrue(self.choices().has_own_form())
        # The button asks before a suggested form replaces the sections changed, and NO keeps them.
        await self.go_to_named_branch(MSG_WIZARD_FORM_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_SUGGESTED_FORM_BUTTON)
        await self.press(Key.ENTER)
        self.assertIn(MSG_WIZARD_REPLACE_SECTIONS_QUESTION, self.text())
        await self.press(keybindings.ConfirmDialog.NO)
        self.assertTrue(self.choices().has_own_form())
        await self.press(Key.ENTER, keybindings.ConfirmDialog.YES, Key.ENTER)
        self.assertFalse(self.choices().has_own_form())
        self.assertEqual(self.sections(), suggested)

    async def test_create_makes_the_songs_own_form_and_the_wizard_opens_on_it_again_from_the_last_settings(self):
        await self.open_the_form()
        await self.press(keybindings.WizardPage.COPY, keybindings.WizardPage.COPY)
        sections = self.sections()
        await self.create()
        self.assertIsInstance(self.app.screen, ArrangePage)
        self.assertEqual(len(self.document.song().get_scenes()), len(sections))
        await self.press(keybindings.Page.WIZARD)
        await self.start_with(NEW_FROM_LAST)
        self.assertEqual(self.sections(), sections)
        self.assertTrue(self.choices().has_own_form())


class TestWizardThemesAndPlaying(WizardTest):
    """The Themes branch, the song's Progression and Melody, and the Playing branch, its Feel and Fills."""

    async def choose(self, *, genre):
        """Choose a genre by its name and its first subgenre through the choices, and draw the page again."""
        choices = self.choices()
        choices.set_genre(genre)
        choices.set_subgenre(choices.subgenres()[0])
        await self.press(Key.DOWN, Key.UP)

    def a_genre_with(self, traits):
        """A genre that has one of some song traits with several ways."""
        for genre in genre_names():
            choices = self.choices().__class__()
            choices.set_genre(genre)
            choices.set_subgenre(choices.subgenres()[0])
            trait = choices.song_trait(traits)
            if trait is not None and len(choices.song_ways(trait)) > 1:
                return genre
        raise AssertionError(traits)

    async def step(self, label):
        """Move into the fields, onto a field by its label, and press ] (inc)."""
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(label)
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET), keybindings.WizardPage.TO_TREE)

    async def test_both_branches_wait_for_a_genre_and_a_subgenre(self):
        for name in (MSG_WIZARD_THEMES_BRANCH, MSG_WIZARD_PLAYING_BRANCH):
            await self.go_to_named_branch(name)
            await self.press(keybindings.WizardPage.INTO_FIELDS)
            self.assertFalse(self.wizard().in_fields)
            self.assertIn(ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE, self.text())

    async def test_the_progression_is_chosen_on_the_themes_branch(self):
        await self.choose(genre=self.a_genre_with(PROGRESSION_TRAITS))
        choices = self.choices()
        trait = choices.song_trait(PROGRESSION_TRAITS)
        ways = choices.song_ways(trait)
        choices.set_way(trait=trait, value=ways[0])
        await self.go_to_named_branch(MSG_WIZARD_THEMES_BRANCH)
        self.assertIn(ways[0], self.text())
        await self.step(MSG_WIZARD_PROGRESSION_LABEL)
        self.assertEqual(choices.get_way(trait), ways[1])

    async def test_the_smart_melody_styles_gauges_show_under_the_melody_field_and_are_stepped(self):
        await self.choose(genre=A_GENRE_WITH_RHYTHMS)
        choices = self.choices()
        await self.go_to_named_branch(MSG_WIZARD_THEMES_BRANCH)
        for name in DEFAULT_GAUGES:
            self.assertNotIn(MSG_WIZARD_GAUGE_ENDS[name][1], self.text())
        choices.set_melody(SMART)
        await self.press(Key.DOWN, Key.UP)
        shown = self.text()
        for name in DEFAULT_GAUGES:
            self.assertIn(MSG_WIZARD_GAUGE_LABELS[name], shown)
            self.assertIn(MSG_WIZARD_MELODY_GAUGE_SHOWN.format(gauge=self.gauge_drawn(choices.get_gauge(name)), low=MSG_WIZARD_GAUGE_ENDS[name][0], high=MSG_WIZARD_GAUGE_ENDS[name][1]), shown)
        for name in DEFAULT_GAUGES:
            before = choices.get_gauge(name)
            await self.step(MSG_WIZARD_GAUGE_LABELS[name])
            self.assertEqual(choices.get_gauge(name), before + 1)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_GAUGE_LABELS[GAUGE_MOVES])
        await self.press(*[key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET)] * HIGHEST_GAUGE)
        self.assertEqual(choices.get_gauge(GAUGE_MOVES), HIGHEST_GAUGE)
        self.assertNotIn(MSG_WIZARD_GAUGE_EMPTY, self.wizard().field().value())

    def gauge_drawn(self, position):
        return MSG_WIZARD_GAUGE_FULL * position + MSG_WIZARD_GAUGE_EMPTY * (HIGHEST_GAUGE - position)

    async def test_the_progression_starts_on_any_and_is_left_to_chance_again_from_the_field(self):
        await self.choose(genre=self.a_genre_with(PROGRESSION_TRAITS))
        choices = self.choices()
        await self.go_to_named_branch(MSG_WIZARD_THEMES_BRANCH)
        self.assertTrue(choices.has_any_progression())
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_PROGRESSION_LABEL)
        self.assertEqual(self.wizard().field().value(), MSG_WIZARD_ANY_PROGRESSION)
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertFalse(choices.has_any_progression())
        self.assertEqual(choices.get_way(choices.progression_trait()), choices.song_ways(choices.progression_trait())[0])
        await self.press(key_of(binding=keybindings.WizardPage.LESS, key=Key.LEFT_BRACKET))
        self.assertTrue(choices.has_any_progression())

    async def test_the_melody_starts_on_usual_and_another_style_is_chosen_and_made(self):
        await self.choose(genre=self.a_genre_with(PROGRESSION_TRAITS))
        choices = self.choices()
        await self.go_to_named_branch(MSG_WIZARD_THEMES_BRANCH)
        self.assertIn(MSG_WIZARD_USUAL_MELODY, self.text())
        self.assertIsNone(choices.get_melody())
        await self.step(MSG_WIZARD_MELODY_LABEL)
        self.assertEqual(choices.get_melody(), choices.melody_styles()[0])
        await self.create()
        self.assertIsInstance(self.app.screen, ArrangePage)

    async def test_the_fills_are_chosen_on_the_playing_branch(self):
        for label, traits in ((MSG_WIZARD_FILLS_LABEL, FILLS_TRAITS),):
            await self.choose(genre=self.a_genre_with(traits))
            choices = self.choices()
            trait = choices.song_trait(traits)
            ways = choices.song_ways(trait)
            choices.set_way(trait=trait, value=ways[0])
            await self.go_to_named_branch(MSG_WIZARD_PLAYING_BRANCH)
            await self.step(label)
            self.assertEqual(choices.get_way(trait), ways[1])

    async def test_a_field_with_one_way_is_not_shown_and_a_branch_with_none_says_so(self):
        empty = [genre for genre in genre_names() if not self.fields_of(genre=genre, traits=(FILLS_TRAITS,))]
        self.assertTrue(empty)
        await self.choose(genre=empty[0])
        await self.go_to_named_branch(MSG_WIZARD_PLAYING_BRANCH)
        self.assertIn(MSG_WIZARD_NOTHING_TO_CHOOSE, self.text())
        self.assertNotIn(MSG_WIZARD_FILLS_LABEL, self.text())

    def fields_of(self, *, genre, traits):
        choices = self.choices().__class__()
        choices.set_genre(genre)
        choices.set_subgenre(choices.subgenres()[0])
        found = [choices.song_trait(group) for group in traits]
        return [trait for trait in found if trait is not None and len(choices.song_ways(trait)) > 1]


class TestWizardStart(WizardTest):
    """The four ways a run starts when the current song was made by the wizard, and replacing a song."""

    async def test_no_way_of_starting_is_asked_for_on_a_song_the_wizard_did_not_make(self):
        self.assertIsInstance(self.app.screen, WizardPage)
        self.assertIsNone(self.wizard().start())

    async def test_a_song_the_wizard_made_asks_how_to_start_in_a_dialog_and_esc_opens_no_wizard(self):
        await self.make_a_song_and_open_the_wizard_on_it()
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        text = self.text()
        self.assertIn(MSG_WIZARD_START_TITLE, text)
        for start in STARTS:
            self.assertIn(MSG_WIZARD_START_NAMES[start], text)
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, ArrangePage)

    async def test_the_last_row_of_the_dialog_is_cancel_which_opens_no_wizard(self):
        await self.make_a_song_and_open_the_wizard_on_it()
        self.assertIn(MSG_WIZARD_START_CANCEL, self.text())
        await self.press(*[Key.DOWN] * len(STARTS), Key.ENTER)
        self.assertIsInstance(self.app.screen, ArrangePage)

    async def test_the_wizard_closes_without_asking_until_something_is_changed_after_the_start(self):
        await self.make_a_song_and_open_the_wizard_on_it()
        await self.start_with(NEW_FROM_LAST)
        self.assertIsInstance(self.app.screen, WizardPage)
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, ArrangePage)

    async def test_a_new_song_from_the_last_settings_starts_with_the_songs_choices_and_a_name_of_its_own(self):
        first = await self.make_a_song_and_open_the_wizard_on_it()
        kept = self.document.song().get_wizard_choices()
        await self.start_with(NEW_FROM_LAST)
        self.assertEqual(self.wizard().start(), NEW_FROM_LAST)
        self.assertEqual(self.choices().to_data(), kept)
        self.assertNotEqual(self.wizard().song_name(), first)
        self.assertFalse(self.wizard().replaces())
        await self.create()
        self.assertEqual(len(self.document.song_names()), 3)
        # The settings are kept and the dice rolled again, as on every run.
        self.assertEqual({**self.document.song().get_wizard_choices(), SEED: None}, {**kept, SEED: None})

    async def test_a_new_song_from_scratch_starts_with_nothing_chosen(self):
        await self.make_a_song_and_open_the_wizard_on_it()
        await self.start_with(NEW_FROM_SCRATCH)
        self.assertEqual(self.choices().to_data(), {})
        await self.go_to_named_branch(MSG_WIZARD_CREATE_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        self.assertIn(ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE, self.text())

    async def test_replacing_from_the_last_settings_keeps_the_settings_rolls_the_dice_again_and_leaves_nothing_behind(self):
        first = await self.make_a_song_and_open_the_wizard_on_it()
        kept = self.document.song().get_wizard_choices()
        patterns = len(self.document.setlist().get_pattern_names())
        await self.start_with(REPLACE_FROM_LAST)
        self.assertIn(first, self.wizard().caption())
        await self.create()
        self.assertIsInstance(self.app.screen, ArrangePage)
        self.assertIn(MSG_WIZARD_REPLACED.format(name=first), self.text())
        self.assertEqual(self.document.song_names(), [MSG_DEFAULT_SONG_NAME, first])
        now = self.document.song().get_wizard_choices()
        self.assertNotEqual(now[SEED], kept[SEED])
        self.assertEqual({**now, SEED: None}, {**kept, SEED: None})
        self.assertEqual(len(self.document.setlist().get_pattern_names()), patterns)

    async def test_replacing_from_scratch_keeps_the_songs_name_and_place(self):
        first = await self.make_a_song_and_open_the_wizard_on_it()
        await self.press(Key.ESCAPE)
        # A third song after it, so that the replaced song's place is not the last.
        await self.press(keybindings.Page.WIZARD)
        await self.start_with(NEW_FROM_SCRATCH)
        await self.choose_genre_and_subgenre()
        await self.create()
        third = self.document.current_song_name()
        third_data = self.song_data(third)
        self.document.select_song(first)
        await self.press(keybindings.Page.WIZARD)
        await self.start_with(REPLACE_FROM_SCRATCH)
        await self.choose_genre_and_subgenre()
        # The name is only shown, since a replaced song keeps it.
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_NAME_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, WizardPage)
        await self.press(keybindings.WizardPage.TO_TREE)
        await self.create()
        self.assertEqual(self.document.song_names(), [MSG_DEFAULT_SONG_NAME, first, third])
        self.assertEqual(self.document.current_song_name(), first)
        self.assertEqual(self.song_data(third), third_data)

    async def test_one_undo_puts_a_replaced_song_back_with_its_hand_edits_and_one_redo_replaces_it_again(self):
        first = await self.make_a_song_and_open_the_wizard_on_it()
        await self.press(Key.ESCAPE)
        self.document.set_tempo(self.document.song().get_tempo() + 1)
        edited = self.document.setlist().to_data()
        await self.press(keybindings.Page.WIZARD)
        await self.start_with(REPLACE_FROM_SCRATCH)
        await self.choose_genre_and_subgenre()
        await self.create()
        replaced = self.document.setlist().to_data()
        self.assertNotEqual(replaced, edited)
        await self.press(keybindings.Page.UNDO)
        self.assertEqual(self.document.setlist().to_data(), edited)
        self.assertEqual(self.document.current_song_name(), first)
        await self.press(keybindings.Page.REDO)
        self.assertEqual(self.document.setlist().to_data(), replaced)


class TestWizardFillsAnUntouchedSong(WizardTest):
    """On a song nothing was done to, as a new set's, Create fills the song in place of adding one beside it."""

    def make_app(self):
        self.document = Document()
        return LlamatronApp(document=self.document)

    async def test_a_new_sets_song_is_filled_under_the_wizards_name_and_its_starter_pattern_goes(self):
        before = self.document.setlist().to_data()
        starter = self.document.setlist().get_pattern_names()
        await self.choose_genre_and_subgenre()
        name = self.wizard().song_name()
        await self.create()
        self.assertEqual(self.document.song_names(), [name])
        self.assertEqual(self.document.current_song_name(), name)
        self.assertIn(MSG_WIZARD_CREATED.format(name=name), self.text())
        for pattern in starter:
            self.assertFalse(self.document.setlist().has_pattern(pattern))
        await self.press(keybindings.Page.UNDO)
        self.assertEqual(self.document.setlist().to_data(), before)
        self.assertEqual(self.document.song_names(), [MSG_DEFAULT_SONG_NAME])

    async def test_a_song_that_was_changed_is_kept_and_the_new_song_added_beside_it(self):
        self.document.set_tempo(self.document.song().get_tempo() + 1)
        await self.choose_genre_and_subgenre()
        name = self.wizard().song_name()
        await self.create()
        self.assertEqual(self.document.song_names(), [MSG_DEFAULT_SONG_NAME, name])


class TestWizardPageUndo(WizardTest):
    """Undo and the wizard: nothing to undo while it is open, and Create is one step."""

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
