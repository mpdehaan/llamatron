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
from llamatron.macro_composer.melody import LENGTHS, LOUDNESS, DEFAULT_GAUGES, EVOLVING, GAUGE_MOVES, HIGHEST_GAUGE, LEAPS, MOVE, SERIAL, SMART
from llamatron.macro_composer.wizard_choices import PLAYER_ROWS, PLAYER_ROWS_KEPT, MAJOR, WizardChoices, USUAL_PIECE_NOTE, FEWEST_FILLS, MOST_FILLS, ONE_GUITARIST_COUNT, TWO_GUITARISTS, ACOUSTIC, BAND_SOUNDS, FILLS_TRAITS, PROGRESSION_TRAITS, MOST_BUSY, USUAL_BUSY, MINOR, SEED, genre_names, genre_title
from llamatron.composition import limits
from llamatron.strings import errors, labels as labels_text, legends, macro_composer as composer_text, marks, messages, names
from llamatron.composition.naming import new_name
from llamatron.support.version import VERSION
from llamatron.tui import keybindings, themes
from llamatron.tui.app import LlamatronApp
from llamatron.tui.document import Document
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.dialogs.dialog import DIALOG_MARGIN
from llamatron.tui.drawing import LINE_BREAK
from llamatron.tui.dialogs.row_dialog import CELL_WIDTH, RowDialog
from llamatron.tui.note_names import note_shown, note_typed
from llamatron.tui.dialogs.sound_dialog import SoundDialog
from llamatron.tui.keys import Key
from llamatron.tui.text import clock
from llamatron.tui.screens.arrange.arrange_page import ArrangePage
from llamatron.tui.screens.set.main_page import MainPage
from llamatron.tui.screens.set.songs_page import SongsPage
from llamatron.tui.screens.wizard.hooks_branch import picture_of
from llamatron.tui.screens.wizard.starts import NEW_FROM_LAST, NEW_FROM_SCRATCH, REPLACE_FROM_LAST, REPLACE_FROM_SCRATCH, STARTS
from llamatron.tui.screens.wizard.wizard_page import WizardPage
from tests.support.ui_testing import UITest, back_key, first_key, fixed_text, forward_key, key_of

# The tree's branches by their places from the top, while none is open.
GENRE_PLACE = 0
# The branches under Composition, which the tree shows from the start, and the places of the branches after them.
COMPOSITION_BRANCHES = 4
# The panel under Composition with the longest name, which the Composition panel's lines are as wide as.
WIDEST_COMPOSITION_BRANCH = labels_text.MSG_WIZARD_TUNES_BRANCH
FORM_PLACE = 3 + COMPOSITION_BRANCHES
# The tree's top panels and the Subgenre panel under Genre come before Create.
CREATE_PLACE = 5 + COMPOSITION_BRANCHES
# A name the test gives the song.
A_SONG_NAME = 'anthem'
A_NOTE_TYPED = 'f#2'
A_GENRE_WITH_RHYTHMS = 'rock'
A_GENRE_WITH_NO_HOOK = 'blues'
# A row made for the Row dialog's tests, its range, how short and long it may be, and the row put back; and a row either side of zero.
A_ROWS_TITLE = 'A row'
A_ROW = [1, 2, 3]
A_USUAL_ROW = [2, 2]
A_ROWS_LOWEST = 1
A_ROWS_HIGHEST = 4
A_ROWS_FEWEST = 1
A_ROWS_MOST = 16
A_SIGNED_ROW = [-2, 0, 3]
CONSOLE_WIDTH = 80
# A hook of one bar made for the test, a note of it, and the widths of a panel with room for wide steps and without.
A_HOOKS_STEPS = 8
A_PITCH = 60
A_WIDE_PANEL = 60
A_NARROW_PANEL = 20
# A progression of rock with a borrowed chord, as written, and its verse spelled in two keys.
A_PROGRESSION = 'borrowed flat seven'
A_ROOT = 'C'
ITS_NUMERALS = 'I ♭VII IV I'
A_VERSE = 'verse'
A_HELD_KIND = 'ending'
ITS_VERSE_CHORDS = 'C  Bb  F  C'
# A progression of plain degrees, whose chords take the scale's own qualities.
A_PLAIN_PROGRESSION = 'three chord'
ITS_NUMERALS_IN_MINOR = 'i iv i v'
ITS_VERSE_CHORDS_IN_MINOR = 'Cm  Fm  Cm  Gm'


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
        """Choose the first genre and its first subgenre, each with ] (inc) from nothing chosen on its panel, and go back to the tree."""
        more = key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET)
        await self.go_to_named_branch(labels_text.MSG_WIZARD_GENRE_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS, more, keybindings.WizardPage.TO_TREE)
        # The subgenre is chosen on its own panel, and the cursor goes back to Genre, where the tests go on from.
        await self.go_to_named_branch(labels_text.MSG_WIZARD_SUBGENRE_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS, more, keybindings.WizardPage.TO_TREE)
        await self.go_to_named_branch(labels_text.MSG_WIZARD_GENRE_BRANCH)

    async def create(self):
        """Press the Create button, the last row of the Create branch."""
        await self.go_to_named_branch(labels_text.MSG_WIZARD_CREATE_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_CREATE_BUTTON)
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
        self.assertEqual(self.wizard().branch().name(), labels_text.MSG_WIZARD_GENRE_BRANCH)
        await self.press(Key.ESCAPE, keybindings.ConfirmDialog.YES, keybindings.MainPage.SONGS, keybindings.Page.WIZARD)
        self.assertIsInstance(self.wizard(), WizardPage)
        await self.press(Key.ESCAPE, keybindings.ConfirmDialog.YES)
        self.assertIsInstance(self.app.screen, SongsPage)

    async def test_f5_in_the_wizard_says_the_wizard_is_open(self):
        await self.press(keybindings.Page.WIZARD)
        self.assertIsInstance(self.wizard(), WizardPage)
        self.assertEqual(len(self.app.pages()), 2)
        self.assertIn(messages.MSG_WIZARD_ALREADY_OPEN, self.text())

    async def test_the_tree_lists_genre_form_and_create_and_the_fields_of_the_branch_under_the_cursor_show(self):
        text = self.text()
        for name in (labels_text.MSG_WIZARD_GENRE_BRANCH, labels_text.MSG_WIZARD_FORM_BRANCH, labels_text.MSG_WIZARD_CREATE_BRANCH, labels_text.MSG_GENRE_LABEL, labels_text.MSG_WIZARD_SUBGENRE_BRANCH, marks.MSG_WIZARD_CHOOSE, labels_text.MSG_NAME_LABEL):
            self.assertIn(name, text)
        self.assertIn(marks.MSG_WIZARD_NEEDS_GENRE, text)
        await self.go_to_named_branch(labels_text.MSG_WIZARD_FORM_BRANCH)
        self.assertIn(messages.MSG_WIZARD_CHOOSE_FIRST, self.text())
        self.assertNotIn(labels_text.MSG_NAME_LABEL, self.text())

    async def test_the_new_song_is_named_as_the_tracker_names_a_new_thing(self):
        self.assertEqual(self.wizard().song_name(), new_name(word=names.MSG_NEW_SONG_WORD, taken=[names.MSG_DEFAULT_SONG_NAME]))
        self.assertIn(self.wizard().song_name(), self.text())

    async def test_the_cursor_stops_at_both_ends_of_the_tree(self):
        await self.press(Key.UP)
        self.assertEqual(self.wizard().tree_place, GENRE_PLACE)
        await self.press(*[Key.DOWN] * (CREATE_PLACE + 1))
        self.assertEqual(self.wizard().tree_place, len(self.wizard().rows()) - 1)
        self.assertEqual(self.wizard().branch().name(), labels_text.MSG_WIZARD_CREATE_BRANCH)

    async def test_the_part_under_the_cursor_is_drawn_in_the_wizards_colour_and_no_other_is(self):
        colour = themes.text_style(WizardPage.THEME)
        await self.press(Key.DOWN)
        lines = self.wizard().tree_lines()
        coloured = [place for place, line in enumerate(lines) if any(colour in str(span.style) for span in line.spans)]
        self.assertEqual(coloured, [self.wizard().tree_place])

    async def test_the_subgenre_is_a_top_part_of_the_tree_after_the_genre(self):
        names = [branch.name() for depth, branch in self.wizard().rows() if not depth]
        self.assertEqual(names[:2], [labels_text.MSG_WIZARD_GENRE_BRANCH, labels_text.MSG_WIZARD_SUBGENRE_BRANCH])

    async def test_a_locked_part_shows_nothing_under_it_and_right_and_enter_say_what_to_choose_first(self):
        wizard = self.wizard()
        self.assertTrue(all(not depth for depth, _ in wizard.rows()))
        await self.go_to_named_branch(labels_text.MSG_WIZARD_COMPOSITION_BRANCH)
        before = len(wizard.rows())
        await self.press(Key.RIGHT)
        self.assertEqual(len(wizard.rows()), before)
        self.assertIn(errors.ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE, self.text())
        await self.press(Key.DOWN, keybindings.WizardPage.INTO_FIELDS)
        self.assertFalse(wizard.in_fields)
        self.assertIn(errors.ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE, self.text())
        await self.go_to_named_branch(labels_text.MSG_WIZARD_SUBGENRE_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        self.assertFalse(wizard.in_fields)
        self.assertIn(errors.ERR_WIZARD_CHOOSE_GENRE, self.text())

    async def test_choosing_the_genre_and_the_subgenre_unlocks_every_part(self):
        await self.choose_genre_and_subgenre()
        wizard = self.wizard()
        self.assertTrue(all(branch.refusal() is None for _, branch in wizard.rows()))
        await self.go_to_named_branch(labels_text.MSG_WIZARD_FORM_BRANCH)
        await self.press(Key.RIGHT)
        self.assertTrue(any(depth for depth, _ in wizard.rows()))

    async def test_enter_and_tab_move_into_the_fields_and_esc_and_tab_move_back(self):
        for into, back in ((Key.ENTER, Key.ESCAPE), (Key.TAB, Key.TAB)):
            await self.press(into)
            self.assertTrue(self.wizard().in_fields)
            self.assertIn(marks.MSG_WIZARD_EDITED_BRANCH, self.text())
            await self.press(back)
            self.assertIsInstance(self.wizard(), WizardPage)
            self.assertFalse(self.wizard().in_fields)
            self.assertNotIn(marks.MSG_WIZARD_EDITED_BRANCH, self.text())

    async def test_the_subgenre_refuses_until_a_genre_is_chosen(self):
        await self.go_to_named_branch(labels_text.MSG_WIZARD_SUBGENRE_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        self.assertFalse(self.wizard().in_fields)
        self.assertIn(errors.ERR_WIZARD_CHOOSE_GENRE, self.text())
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
        for label in (labels_text.MSG_WIZARD_KEY_LABEL, labels_text.MSG_SCALE_LABEL):
            self.assertIn(label, self.text())
        # The tempo is the subgenre's, on the panel under Genre, with the subgenre's usual range after it.
        await self.go_to_named_branch(labels_text.MSG_WIZARD_SUBGENRE_BRANCH)
        text = self.text()
        self.assertIn(labels_text.MSG_TEMPO_LABEL, text)
        lowest, highest = choices.tempo_range()
        self.assertIn(str(lowest), text)
        self.assertIn(str(highest), text)
        tempo = choices.get_tempo()
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_TEMPO_LABEL)
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(choices.get_tempo(), tempo + 1)
        await self.press(keybindings.WizardPage.TO_TREE)
        await self.go_to_named_branch(labels_text.MSG_WIZARD_GENRE_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_SCALE_LABEL)
        await self.press(Key.ENTER, Key.DOWN, Key.ENTER)
        self.assertEqual(choices.get_scale_type(), MINOR)
        self.assertIn(labels_text.MSG_WIZARD_SCALE_TYPE_NAMES[MINOR], self.text())

    async def test_the_meter_is_shown_and_stepping_the_length_chooses_a_longer_or_a_shorter_form(self):
        await self.choose_genre_and_subgenre()
        choices = self.choices()
        self.assertIn(choices.meter(), self.text())
        self.assertIn(clock(choices.form_seconds()), self.text())
        forms = choices.forms_by_length()
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_LENGTH_LABEL)
        back = key_of(binding=keybindings.WizardPage.LESS, key=Key.LEFT_BRACKET)
        await self.press(*[back] * len(forms))
        self.assertEqual(choices.get_form(), forms[0])
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(choices.get_form(), forms[1])
        self.assertIn(clock(choices.form_seconds()), self.text())
        # The meter is the subgenre's, so its field does nothing.
        await self.select_field(labels_text.MSG_WIZARD_METER_LABEL)
        before = choices.to_data()
        await self.press(Key.ENTER, back)
        self.assertEqual(choices.to_data(), before)

    async def test_choosing_another_genre_leaves_the_subgenre_to_be_chosen_again(self):
        await self.choose_genre_and_subgenre()
        await self.press(keybindings.WizardPage.INTO_FIELDS, key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.choices().get_genre(), genre_names()[1])
        self.assertIsNone(self.choices().get_subgenre())
        await self.press(keybindings.WizardPage.TO_TREE)
        await self.go_to_named_branch(labels_text.MSG_WIZARD_SUBGENRE_BRANCH)
        self.assertIn(marks.MSG_WIZARD_CHOOSE, self.text())

    async def test_the_song_is_named_on_the_genre_branch_and_a_name_in_use_is_refused(self):
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_NAME_LABEL)
        await self.press(Key.ENTER, *[Key.BACKSPACE] * len(self.wizard().song_name()))
        await self.type(A_SONG_NAME)
        await self.press(Key.ENTER)
        self.assertEqual(self.wizard().song_name(), A_SONG_NAME)
        await self.press(Key.ENTER, *[Key.BACKSPACE] * len(A_SONG_NAME))
        await self.type(names.MSG_DEFAULT_SONG_NAME)
        await self.press(Key.ENTER)
        self.assertEqual(self.wizard().song_name(), A_SONG_NAME)

    async def test_the_form_branch_picks_a_form_lists_its_sections_and_opens_to_a_branch_for_each(self):
        await self.choose_genre_and_subgenre()
        await self.go_to_named_branch(labels_text.MSG_WIZARD_FORM_BRANCH)
        choices = self.choices()
        sections = choices.form_sections()
        text = self.text()
        self.assertIn(labels_text.MSG_WIZARD_FORM_LABEL, text)
        # The Form branch starts open, so that the sections show themselves.
        self.assertIn(marks.MSG_WIZARD_BRANCH_OPEN, text)
        self.assertIn(messages.MSG_WIZARD_SECTIONS_HINT, text)
        for name in sections:
            self.assertIn(name, text)
        self.assertEqual(len(self.wizard().rows()), CREATE_PLACE + 1 + len(choices.roles_in()) + len(sections))
        await self.press(Key.DOWN)
        self.assertEqual(self.wizard().branch().name(), sections[0])
        self.assertIn(labels_text.MSG_WIZARD_BARS_LABEL, self.text())
        # ENTER moves into a section's settings and ESC back; Left goes back to the Form branch, where Left closes it.
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        self.assertTrue(self.wizard().in_fields)
        await self.press(Key.ESCAPE, Key.DOWN, Key.LEFT)
        self.assertEqual(self.wizard().branch().name(), labels_text.MSG_WIZARD_FORM_BRANCH)
        await self.press(Key.LEFT)
        self.assertEqual(len(self.wizard().rows()), CREATE_PLACE + 1 + len(choices.roles_in()))
        self.assertIn(marks.MSG_WIZARD_BRANCH_CLOSED, self.text())
        await self.press(Key.RIGHT)
        self.assertEqual(len(self.wizard().rows()), CREATE_PLACE + 1 + len(choices.roles_in()) + len(sections))

    async def test_a_suggested_form_is_picked_from_a_dialog_that_says_each_forms_sections_and_length(self):
        await self.choose_genre_and_subgenre()
        await self.go_to_named_branch(labels_text.MSG_WIZARD_FORM_BRANCH)
        choices = self.choices()
        forms = choices.forms()
        self.assertGreater(len(forms), 1)
        self.assertEqual(choices.get_form(), forms[0])
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_SUGGESTED_FORM_BUTTON)
        # No key steps the form, which only the dialog changes.
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET), Key.RIGHT, Key.DOWN)
        self.assertEqual(choices.get_form(), forms[0])
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        for form in forms:
            self.assertIn(marks.MSG_WIZARD_SUGGESTED_FORM.format(form=form, count=choices.form_section_count(form), length=clock(choices.form_seconds(form=form))), self.text())
        await self.press(Key.ESCAPE)
        self.assertEqual(choices.get_form(), forms[0])
        await self.press(Key.ENTER, Key.DOWN, Key.ENTER)
        self.assertEqual(choices.get_form(), forms[1])

    async def test_create_refuses_until_a_genre_and_a_subgenre_are_chosen(self):
        before = self.document.setlist().to_data()
        await self.go_to_branch(CREATE_PLACE)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        self.assertFalse(self.wizard().in_fields)
        self.assertIn(errors.ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE, self.text())
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
        self.assertEqual(self.document.song_names(), [names.MSG_DEFAULT_SONG_NAME, name])
        self.assertIn(messages.MSG_WIZARD_CREATED.format(name=name), self.text())
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
        self.assertEqual(self.document.song_names(), [names.MSG_DEFAULT_SONG_NAME, first, second])
        self.assertEqual(self.document.setlist().get_item(section=Section.SONGS, name=first).to_data(), first_data)

    async def test_esc_in_the_tree_asks_even_with_nothing_chosen_and_enter_alone_keeps_the_wizard(self):
        await self.press(keybindings.WizardPage.INTO_FIELDS, keybindings.WizardPage.TO_TREE, Key.ESCAPE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn(messages.MSG_WIZARD_CLOSE_UNCHANGED_QUESTION, self.text())
        self.assertNotIn(messages.MSG_WIZARD_CLOSE_QUESTION, self.text())
        # No is selected, so ENTER keeps the wizard, and so does ESC.
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, WizardPage)
        await self.press(Key.ESCAPE, Key.ESCAPE)
        self.assertIsInstance(self.app.screen, WizardPage)
        await self.press(Key.ESCAPE, keybindings.ConfirmDialog.YES)
        self.assertIsInstance(self.app.screen, MainPage)

    async def test_esc_in_the_tree_asks_once_something_is_chosen_and_no_keeps_the_wizard(self):
        await self.choose_genre_and_subgenre()
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn(messages.MSG_WIZARD_CLOSE_QUESTION, self.text())
        await self.press(keybindings.ConfirmDialog.NO)
        self.assertIsInstance(self.app.screen, WizardPage)
        self.assertEqual(self.choices().get_genre(), genre_names()[0])
        await self.press(Key.ESCAPE, keybindings.ConfirmDialog.YES)
        self.assertIsInstance(self.app.screen, MainPage)

    async def test_the_wizard_fits_an_80_by_24_console_with_a_long_form_open(self):
        await self.choose_genre_and_subgenre()
        await self.go_to_named_branch(labels_text.MSG_WIZARD_FORM_BRANCH)
        await self.press(Key.RIGHT, *[Key.DOWN] * 30)
        self.assertEqual(self.wizard().branch().name(), labels_text.MSG_WIZARD_CREATE_BRANCH)
        self.assertIn(labels_text.MSG_WIZARD_CREATE_BRANCH, self.text())


class TestWizardBand(WizardTest):
    """The Band branch: a toggle for each player, and a branch for each player who is in."""

    async def open_the_band(self):
        await self.choose_genre_and_subgenre()
        await self.go_to_named_branch(labels_text.MSG_WIZARD_BAND_BRANCH)

    async def test_the_band_waits_for_a_genre_and_a_subgenre(self):
        await self.go_to_named_branch(labels_text.MSG_WIZARD_BAND_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        self.assertFalse(self.wizard().in_fields)
        self.assertIn(errors.ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE, self.text())

    async def test_the_band_lists_every_player_and_opens_to_a_branch_for_each_who_is_in(self):
        await self.open_the_band()
        choices = self.choices()
        self.assertTrue(choices.answerers())
        self.assertEqual([field.label for field in self.wizard().fields()],
                         [labels_text.MSG_WIZARD_SOUNDS_LABEL, labels_text.MSG_WIZARD_TUNE_LABEL, labels_text.MSG_WIZARD_ANSWERED_BY_LABEL, *(choices.role_title(role) for role in choices.roles() if choices.role_can_play(role))])
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
        self.assertIn(errors.ERR_WIZARD_LAST_PLAYER, self.text())

    async def test_a_players_own_gauges_show_under_busy_and_one_moved_makes_the_player_custom_until_busy_is_chosen_again(self):
        await self.choose_genre_and_subgenre()
        choices = self.choices()
        player = next(role for role in choices.roles_in() if choices.has_busy(role) and choices.player_gauges(role))
        await self.go_to_named_branch(choices.role_title(player))
        shown = self.text()
        for gauge in choices.player_gauges(player):
            self.assertIn(labels_text.MSG_WIZARD_PLAYER_GAUGE_LABELS[gauge], shown)
        self.assertNotIn(fixed_text(marks.MSG_WIZARD_BUSY_CUSTOM_SHOWN), shown)
        gauge = choices.player_gauges(player)[0]
        before = choices.get_player_gauge(role=player, gauge=gauge)
        more = key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_PLAYER_GAUGE_LABELS[gauge])
        await self.press(more)
        self.assertEqual(choices.get_player_gauge(role=player, gauge=gauge), before + 1)
        self.assertIsNone(choices.player_preset(player))
        self.assertIn(fixed_text(marks.MSG_WIZARD_BUSY_CUSTOM_SHOWN), self.text())
        await self.select_field(labels_text.MSG_WIZARD_BUSY_LABEL)
        await self.press(more)
        self.assertIsNotNone(choices.player_preset(player))
        self.assertNotIn(fixed_text(marks.MSG_WIZARD_BUSY_CUSTOM_SHOWN), self.text())

    async def test_a_players_branch_chooses_how_the_player_plays_and_how_busy_shown_as_a_gauge(self):
        await self.open_the_band()
        choices = self.choices()
        player = next(role for role in choices.roles_in() if choices.has_busy(role) and len(choices.role_traits(role)) == 1)
        trait = choices.role_traits(player)[0]
        ways = choices.ways(role=player, trait=trait)
        await self.press(Key.RIGHT, *[Key.DOWN] * (choices.roles_in().index(player) + 1))
        self.assertEqual(self.wizard().branch().name(), choices.role_title(player))
        text = self.text()
        self.assertIn(labels_text.MSG_WIZARD_BUSY_LABEL, text)
        self.assertIn(marks.MSG_WIZARD_GAUGE_FULL * USUAL_BUSY + marks.MSG_WIZARD_GAUGE_EMPTY * (MOST_BUSY - USUAL_BUSY), text)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_PLAYS_LABEL)
        await self.press(Key.ENTER)
        for way in ways:
            self.assertIn(way, self.text())
        await self.press(Key.ESCAPE)
        more = key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET)
        await self.select_field(labels_text.MSG_WIZARD_BUSY_LABEL)
        await self.press(*[more] * MOST_BUSY)
        self.assertEqual(choices.get_busy(player), MOST_BUSY)
        self.assertIn(marks.MSG_WIZARD_GAUGE_FULL * MOST_BUSY, self.text())
        # A field that a busier player brings above the gauge leaves the cursor on the gauge.
        self.assertEqual(self.wizard().label_under_cursor(), labels_text.MSG_WIZARD_BUSY_LABEL)

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
        await self.go_to_named_branch(labels_text.MSG_WIZARD_BAND_BRANCH)
        choices = self.choices()
        role = [role for role in choices.roles_in() if choices.has_sound(role)][0]
        await self.press(Key.RIGHT, *[Key.DOWN] * (choices.roles_in().index(role) + 1))
        return role

    async def test_the_bands_sounds_are_stepped_and_a_player_shows_the_bands_sound_as_the_bands(self):
        role = await self.open_a_player()
        choices = self.choices()
        self.assertIn(marks.MSG_WIZARD_BAND_SOUND_SHOWN.format(sound=choices.sound_name(choices.get_sound(role))), self.text())
        await self.go_to_named_branch(labels_text.MSG_WIZARD_BAND_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_SOUNDS_LABEL)
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET), keybindings.WizardPage.TO_TREE)
        self.assertEqual(choices.get_band_sounds(), BAND_SOUNDS[1])
        self.assertEqual(BAND_SOUNDS[1], ACOUSTIC)

    async def test_a_players_sound_is_picked_from_the_genres_and_goes_back_to_the_bands(self):
        role = await self.open_a_player()
        choices = self.choices()
        own = choices.genre_sounds(role)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_SOUND_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertIn(marks.MSG_WIZARD_FROM_BAND.format(sound=choices.sound_name(choices.band_sound(role))), self.text())
        self.assertIn(labels_text.MSG_WIZARD_MORE_SOUNDS, self.text())
        await self.press(*[Key.UP] * (len(own) + 2), *[Key.DOWN] * len(own), Key.ENTER)
        self.assertTrue(choices.has_own_sound(role))
        self.assertEqual(choices.get_sound(role), own[-1])
        self.assertNotIn(marks.MSG_WIZARD_BAND_SOUND_SHOWN.format(sound=choices.sound_name(own[-1])), self.text())
        await self.press(Key.ENTER, *[Key.UP] * (len(own) + 2), Key.ENTER)
        self.assertFalse(choices.has_own_sound(role))

    async def test_more_sounds_opens_every_general_midi_sound_by_family_and_the_song_made_plays_the_one_picked(self):
        role = await self.open_a_player()
        choices = self.choices()
        own = choices.genre_sounds(role)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_SOUND_LABEL)
        await self.press(Key.ENTER, *[Key.DOWN] * (len(own) + 2), Key.ENTER)
        dialog = self.app.screen
        self.assertIsInstance(dialog, SoundDialog)
        # Every family of General MIDI is offered, the last ones too, and a sound of the last can be taken.
        self.assertEqual([name for name, _ in dialog.groups], labels_text.MSG_GM_FAMILIES)
        await self.press(*[Key.DOWN] * len(labels_text.MSG_GM_FAMILIES), Key.ENTER, *[Key.DOWN] * limits.GM_FAMILY_SIZE, Key.ENTER)
        picked = choices.get_sound(role)
        self.assertEqual(picked, limits.MAX_GM_SOUND)
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
        await self.go_to_named_branch(labels_text.MSG_WIZARD_BAND_BRANCH)
        await self.press(Key.DOWN, Key.UP)

    async def test_one_guitarist_is_chosen_on_the_band_and_the_two_players_show_as_one(self):
        await self.choose(offers=True)
        choices = self.choices()
        await self.press(Key.RIGHT)
        rows = len(self.wizard().rows())
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_GUITARISTS_LABEL)
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
        self.assertNotIn(labels_text.MSG_WIZARD_GUITARISTS_LABEL, self.text())


class TestWizardKit(WizardTest):
    """The drums' branch: a toggle for each piece of the kit."""

    async def open_the_drums(self):
        """Choose a genre and a subgenre, open the Band and put the tree's cursor on the drums, the last player."""
        await self.choose_genre_and_subgenre()
        await self.go_to_named_branch(labels_text.MSG_WIZARD_BAND_BRANCH)
        choices = self.choices()
        await self.press(Key.RIGHT, *[Key.DOWN] * len([role for role in choices.roles_in() if role in choices.roles_shown()]))
        self.assertFalse(choices.has_sound(choices.roles_in()[-1]))

    async def test_a_piece_is_switched_off_and_on_and_the_last_piece_stays(self):
        await self.open_the_drums()
        choices = self.choices()
        pieces = choices.pieces()
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_KIT_PIECE.format(piece=pieces[0]))
        await self.press(Key.SPACE)
        self.assertFalse(choices.piece_is_on(pieces[0]))
        await self.press(Key.SPACE)
        self.assertTrue(choices.piece_is_on(pieces[0]))
        for piece in pieces:
            await self.select_field(labels_text.MSG_WIZARD_KIT_PIECE.format(piece=piece))
            await self.press(Key.SPACE)
        self.assertTrue(choices.piece_is_on(pieces[-1]))
        self.assertIn(errors.ERR_WIZARD_LAST_PIECE, self.text())

    async def test_a_break_is_chosen_on_the_drums_branch_and_takes_the_place_of_the_drums_other_ways(self):
        await self.open_the_drums()
        choices = self.choices()
        drums = choices.roles_in()[-1]
        self.assertEqual(choices.breaks(), break_names())
        before = choices.role_traits(drums)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_BREAK_LABEL)
        self.assertEqual(self.wizard().field().value(), labels_text.MSG_WIZARD_NO_BREAK)
        self.assertNotIn(labels_text.MSG_WIZARD_BREAK_CUT_LABEL, self.text())
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertIsNotNone(choices.get_break())
        self.assertIn(choices.get_break(), self.text())
        self.assertLess(len(choices.role_traits(drums)), len(before))
        # How far the break is cut up shows under a break chosen: a gauge that is empty for the break as written.
        await self.select_field(labels_text.MSG_WIZARD_BREAK_CUT_LABEL)
        self.assertNotIn(marks.MSG_WIZARD_GAUGE_FULL, self.wizard().field().value())
        await self.press(*[key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET)] * MOST_CUT)
        self.assertEqual(choices.get_break_cut(), MOST_CUT)
        self.assertNotIn(marks.MSG_WIZARD_GAUGE_EMPTY, self.wizard().field().value())
        await self.press(*[key_of(binding=keybindings.WizardPage.LESS, key=Key.LEFT_BRACKET)] * MOST_CUT)
        self.assertEqual(choices.get_break_cut(), LEAST_CUT)

    async def test_a_piece_is_a_row_of_two_cells_and_left_and_right_move_between_them(self):
        await self.open_the_drums()
        choices = self.choices()
        piece = choices.pieces()[0]
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_KIT_PIECE.format(piece=piece))
        wizard = self.wizard()
        self.assertEqual([cell.value() for cell in wizard.field().cells], [marks.MSG_TOGGLE_ON, marks.MSG_WIZARD_OWN_DRUM_SHOWN.format(piece=piece)])
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
        self.assertEqual(wizard.cell_field().enter_what, legends.What.CHOOSE)
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
        await self.select_field(labels_text.MSG_WIZARD_KIT_PIECE.format(piece=piece))
        wizard = self.wizard()
        # The picker opens from the sound's cell on the piece's own drum, above the kit's other drums and General MIDI's families.
        await self.press(Key.RIGHT, Key.ENTER)
        dialog = self.app.screen
        self.assertIsInstance(dialog, SoundDialog)
        self.assertEqual([name for name, _ in dialog.groups], [labels_text.MSG_WIZARD_KIT_DRUMS, *labels_text.MSG_GM_FAMILIES])
        self.assertNotIn(piece, [drum for _, drum in dialog.groups[0][1]])
        self.assertIn(marks.MSG_SOUND_NOTE_ROW.format(note=note_shown(USUAL_PIECE_NOTE)), self.text())
        await self.press(Key.DOWN, Key.ENTER, Key.ENTER)
        drum = choices.piece_sound(piece)
        self.assertIn(drum, choices.kit_drums())
        self.assertEqual(wizard.cell_field().value(), marks.MSG_WIZARD_KIT_DRUM_SHOWN.format(drum=drum))
        # A General MIDI sound plays the note of the picker's Note row, stepped there, and the cell shows both.
        await self.press(Key.ENTER, *[Key.DOWN] * (len(labels_text.MSG_GM_FAMILIES) + 1), key_of(binding=keybindings.SoundDialog.NOTE_LESS, key=Key.LEFT_BRACKET))
        await self.press(*[Key.UP] * len(labels_text.MSG_GM_FAMILIES), Key.ENTER, Key.ENTER)
        self.assertEqual((choices.piece_sound(piece), choices.piece_note(piece)), (limits.MIN_GM_SOUND, USUAL_PIECE_NOTE - 1))
        self.assertEqual(wizard.cell_field().value(), marks.MSG_WIZARD_SOUND_ON_NOTE.format(sound=labels_text.MSG_GM_SOUNDS[0], note=note_shown(USUAL_PIECE_NOTE - 1)))
        # A note typed on the Note row and taken there keeps the sound and changes the note.
        await self.press(Key.ENTER, *[Key.DOWN] * (len(labels_text.MSG_GM_FAMILIES) + 2))
        await self.type(A_NOTE_TYPED)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, SoundDialog)
        await self.press(Key.ENTER)
        self.assertEqual((choices.piece_sound(piece), choices.piece_note(piece)), (limits.MIN_GM_SOUND, note_typed(A_NOTE_TYPED)))
        # Bksp on the sound's cell gives the piece its own drum back, and is offered only while the piece has another sound.
        await self.press(keybindings.WizardPage.CLEAR)
        self.assertIsNone(choices.piece_sound(piece))
        self.assertIsNone(wizard.cell_field().clear)

    async def test_a_piece_given_a_kit_drum_again_drops_its_note_from_the_row_and_from_the_song(self):
        await self.open_the_drums()
        choices = self.choices()
        piece = choices.pieces()[0]
        choices.set_piece_sound(piece=piece, sound=limits.MIN_GM_SOUND)
        choices.set_piece_note(piece=piece, note=note_typed(A_NOTE_TYPED))
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_KIT_PIECE.format(piece=piece))
        await self.press(Key.RIGHT)
        self.assertIn(note_shown(note_typed(A_NOTE_TYPED)), self.wizard().cell_field().value())
        # A drum of the kit taken with a note on the Note row: the note is not used, and the row shows the drum alone.
        await self.press(Key.ENTER, *[Key.UP] * (len(labels_text.MSG_GM_FAMILIES) + 2), Key.DOWN, Key.ENTER, Key.ENTER)
        drum = choices.piece_sound(piece)
        self.assertIn(drum, choices.kit_drums())
        self.assertIsNone(choices.piece_note(piece))
        self.assertEqual(self.wizard().cell_field().value(), marks.MSG_WIZARD_KIT_DRUM_SHOWN.format(drum=drum))
        self.assertNotIn(composer_text.MSG_PIECE_INSTRUMENT.format(piece), choices.made_setlist(name=A_SONG_NAME, version=VERSION).to_data()[Section.INSTRUMENTS])
        # ENTER on the Note row then keeps the drum, and so does the piece's own drum.
        await self.press(Key.ENTER, *[Key.DOWN] * (len(labels_text.MSG_GM_FAMILIES) + 2), Key.ENTER)
        self.assertEqual((choices.piece_sound(piece), choices.piece_note(piece)), (drum, None))
        await self.press(Key.ENTER, *[Key.UP] * (len(labels_text.MSG_GM_FAMILIES) + 2), Key.ENTER)
        self.assertEqual((choices.piece_sound(piece), choices.piece_note(piece)), (None, None))
        self.assertEqual(self.wizard().cell_field().value(), marks.MSG_WIZARD_OWN_DRUM_SHOWN.format(piece=piece))

    async def test_how_often_fills_come_is_a_gauge_that_is_empty_at_never(self):
        await self.open_the_drums()
        choices = self.choices()
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_DRUM_FILLS_LABEL)
        await self.press(*[key_of(binding=keybindings.WizardPage.LESS, key=Key.LEFT_BRACKET)] * MOST_FILLS)
        self.assertEqual(choices.get_fills(), FEWEST_FILLS)
        shown = self.wizard().field().value()
        self.assertIn(labels_text.MSG_WIZARD_FILLS_COME[0], shown)
        self.assertNotIn(marks.MSG_WIZARD_GAUGE_FULL, shown)
        await self.press(*[key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET)] * MOST_FILLS)
        self.assertEqual(choices.get_fills(), MOST_FILLS)
        shown = self.wizard().field().value()
        self.assertIn(labels_text.MSG_WIZARD_FILLS_COME[-1], shown)
        self.assertNotIn(marks.MSG_WIZARD_GAUGE_EMPTY, shown)

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
            self.assertNotIn(labels_text.MSG_WIZARD_QUIET_NOTES_LABEL, self.text())
        choices.set_way(trait=with_them[0][0], value=with_them[0][1])
        await self.press(Key.UP, Key.DOWN, keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_QUIET_NOTES_LABEL)
        await self.press(Key.SPACE)
        self.assertFalse(choices.plays_quiet_notes())
        # The toggle stays while the quiet notes are off, so that they can be switched on again.
        self.assertIn(labels_text.MSG_WIZARD_QUIET_NOTES_LABEL, self.text())

    def has_quiet_notes_with(self, *, trait, way):
        choices = self.choices().__class__.from_data(self.choices().to_data())
        choices.set_way(trait=trait, value=way)
        return choices.has_quiet_notes()

    async def test_the_song_made_has_no_track_for_a_piece_switched_off(self):
        await self.open_the_drums()
        piece = self.choices().pieces()[-1]
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_KIT_PIECE.format(piece=piece))
        await self.press(Key.SPACE, keybindings.WizardPage.TO_TREE)
        await self.create()
        self.assertNotIn(piece, self.document.song().get_track_names())


class TestWizardForm(WizardTest):
    """The Form branch: the sections as branches, added, copied, removed and moved with a list's keys, and each section's settings."""

    async def open_the_form(self):
        """Choose a genre and a subgenre, open the Form branch and put the tree's cursor on its first section."""
        await self.choose_genre_and_subgenre()
        await self.go_to_named_branch(labels_text.MSG_WIZARD_FORM_BRANCH)
        await self.press(Key.RIGHT, Key.DOWN)

    def sections(self):
        return self.choices().form_sections()

    async def test_down_from_the_form_reaches_each_section_in_order(self):
        await self.choose_genre_and_subgenre()
        await self.go_to_named_branch(labels_text.MSG_WIZARD_FORM_BRANCH)
        # A kind the form has several of is numbered, and one it has once is not.
        labels = self.choices().section_labels()
        kinds = self.sections()
        repeated = [kind for kind in kinds if kinds.count(kind) > 1][0]
        self.assertEqual([label for label in labels if label.startswith(repeated)][:2], [marks.MSG_WIZARD_SECTION_NUMBERED.format(kind=repeated, number=number) for number in (1, 2)])
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
        self.assertIn(labels_text.MSG_WIZARD_INSERT_SECTION_TITLE, self.text())
        await self.press(*[Key.DOWN] * (len(kinds) - 1), Key.ENTER)
        self.assertEqual(self.sections(), [before[0], kinds[-1], *before[1:]])
        self.assertEqual(self.wizard().branch().name(), self.choices().section_labels()[1])
        self.assertTrue(self.choices().has_own_form())

    async def test_add_on_a_section_puts_the_new_section_at_the_end_and_leaves_the_cursor(self):
        await self.open_the_form()
        before = self.sections()
        await self.press(keybindings.WizardPage.ADD)
        self.assertIn(labels_text.MSG_WIZARD_ADD_SECTION_TITLE, self.text())
        await self.press(Key.ENTER)
        self.assertEqual(self.sections(), [*before, self.choices().section_kinds()[0]])
        self.assertEqual(self.wizard().branch().name(), self.choices().section_labels()[0])

    async def test_add_on_the_form_puts_the_new_section_at_the_end_and_esc_adds_nothing(self):
        await self.choose_genre_and_subgenre()
        await self.go_to_named_branch(labels_text.MSG_WIZARD_FORM_BRANCH)
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
        self.assertIn(errors.ERR_WIZARD_LAST_SECTION, self.text())

    async def test_move_picks_a_section_up_carries_it_and_drops_it_and_only_those_keys_work_meanwhile(self):
        await self.open_the_form()
        before = self.sections()
        await self.press(keybindings.WizardPage.MOVE)
        self.assertIn(marks.MSG_WIZARD_CARRIED.format(name=before[0]), self.text())
        self.assertIn(messages.MSG_WIZARD_MOVING.format(name=before[0]), self.text())
        await self.press(forward_key(keybindings.WizardPage.CARRY), keybindings.WizardPage.COPY)
        self.assertEqual(self.sections(), [before[1], before[0], *before[2:]])
        self.assertEqual(self.wizard().branch().name(), before[0])
        # A carried section stops at the top of the form.
        await self.press(*[back_key(keybindings.WizardPage.CARRY)] * 3)
        self.assertEqual(self.sections(), before)
        await self.press(keybindings.WizardPage.DROP)
        self.assertFalse(self.wizard().moving)
        self.assertNotIn(marks.MSG_WIZARD_CARRIED.format(name=before[0]), self.text())
        self.assertIsInstance(self.app.screen, WizardPage)

    async def test_a_sections_kind_and_bars_are_chosen_and_a_changed_section_gets_a_name_of_its_own(self):
        await self.open_the_form()
        await self.press(Key.DOWN)
        place = 1
        before = self.sections()
        offered = self.choices().bars_offered(place)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_BARS_LABEL)
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.choices().section_bars(place), offered[offered.index(self.choices()._usual(place)[BARS]) + 1])
        self.assertNotEqual(self.sections()[place], before[place])
        kinds = self.choices().section_kinds()
        await self.select_field(labels_text.MSG_WIZARD_KIND_LABEL)
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
        self.assertIn(errors.ERR_WIZARD_SECTION_NEEDS_PLAYER, self.text())

    async def test_a_form_of_the_songs_own_says_so_and_holds_the_length_until_a_suggested_form_is_chosen_again(self):
        await self.open_the_form()
        suggested = self.sections()
        await self.press(keybindings.WizardPage.COPY)
        await self.go_to_named_branch(labels_text.MSG_WIZARD_FORM_BRANCH)
        self.assertIn(marks.MSG_WIZARD_OWN_FORM, self.text())
        await self.go_to_named_branch(labels_text.MSG_WIZARD_GENRE_BRANCH)
        self.assertIn(marks.MSG_WIZARD_OWN_FORM, self.text())
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_LENGTH_LABEL)
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET), keybindings.WizardPage.TO_TREE)
        self.assertTrue(self.choices().has_own_form())
        # The button asks before a suggested form replaces the sections changed, and NO keeps them.
        await self.go_to_named_branch(labels_text.MSG_WIZARD_FORM_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_SUGGESTED_FORM_BUTTON)
        await self.press(Key.ENTER)
        self.assertIn(messages.MSG_WIZARD_REPLACE_SECTIONS_QUESTION, self.text())
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


class TestWizardInterplay(WizardTest):
    """Who answers the tune, on the Band branch; the answering player's Role and Fills busy; and each section's own role."""

    async def open_rock(self):
        choices = self.choices()
        choices.set_genre(A_GENRE_WITH_RHYTHMS)
        choices.set_subgenre(choices.subgenres()[0])
        await self.press(Key.DOWN, Key.UP)
        self.assertIsNotNone(choices.answered_by())

    async def test_the_band_shows_who_has_the_tune_and_nobody_can_be_made_to_answer(self):
        await self.open_rock()
        choices = self.choices()
        answering = choices.answered_by()
        await self.go_to_named_branch(labels_text.MSG_WIZARD_BAND_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_TUNE_LABEL)
        self.assertEqual(self.wizard().field().value(), choices.role_title(choices.tune_player()))
        await self.select_field(labels_text.MSG_WIZARD_ANSWERED_BY_LABEL)
        self.assertEqual(self.wizard().field().value(), choices.role_title(answering))
        await self.press(key_of(binding=keybindings.WizardPage.LESS, key=Key.LEFT_BRACKET))
        self.assertIsNone(choices.answered_by())
        self.assertEqual(self.wizard().field().value(), labels_text.MSG_WIZARD_NOBODY)
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(choices.answered_by(), answering)

    async def open_the_answering_player(self):
        await self.open_rock()
        choices = self.choices()
        await self.go_to_named_branch(labels_text.MSG_WIZARD_BAND_BRANCH)
        shown = [role for role in choices.roles_in() if role in choices.roles_shown()]
        await self.press(Key.RIGHT, *[Key.DOWN] * (shown.index(choices.answered_by()) + 1), keybindings.WizardPage.INTO_FIELDS)

    async def test_the_answering_player_has_a_role_by_section_or_one_for_every_section_and_fills_busy(self):
        await self.open_the_answering_player()
        choices = self.choices()
        await self.select_field(labels_text.MSG_WIZARD_ROLE_LABEL)
        self.assertEqual(self.wizard().field().value(), labels_text.MSG_WIZARD_BY_SECTION)
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(choices.get_role_plan(), choices.ways_beside()[0])
        await self.press(key_of(binding=keybindings.WizardPage.LESS, key=Key.LEFT_BRACKET))
        self.assertIsNone(choices.get_role_plan())
        await self.select_field(labels_text.MSG_WIZARD_FILLS_BUSY_LABEL)
        busy = choices.get_fills_busy()
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(choices.get_fills_busy(), busy + 1)
        self.assertIn(str(busy + 1), self.wizard().field().value())

    async def test_a_player_who_answers_nobody_has_neither_field(self):
        await self.open_the_answering_player()
        self.choices().set_answered_by(None)
        await self.press(keybindings.WizardPage.TO_TREE, keybindings.WizardPage.INTO_FIELDS)
        labels = [field.label for field in self.wizard().fields()]
        self.assertNotIn(labels_text.MSG_WIZARD_ROLE_LABEL, labels)
        self.assertNotIn(labels_text.MSG_WIZARD_FILLS_BUSY_LABEL, labels)

    async def test_a_section_shows_the_plans_role_takes_its_own_and_bksp_gives_it_back_to_the_plan(self):
        await self.open_rock()
        choices = self.choices()
        place = next(place for place in range(len(choices.section_labels())) if choices.section_has_role(place))
        label = labels_text.MSG_WIZARD_SECTION_ROLE_LABEL.format(player=choices.role_title(choices.answered_by()))
        planned = choices.section_role(place)
        await self.go_to_named_branch(labels_text.MSG_WIZARD_FORM_BRANCH)
        await self.press(Key.RIGHT, *[Key.DOWN] * (place + 1), keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(label)
        self.assertEqual(self.wizard().field().value(), marks.MSG_WIZARD_ROLE_FROM_PLAN.format(way=planned))
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertTrue(choices.section_role_is_own(place))
        self.assertEqual(choices.section_role(place), choices.ways_beside()[0])
        self.assertEqual(self.wizard().field().value(), choices.ways_beside()[0])
        await self.press(keybindings.WizardPage.CLEAR)
        self.assertFalse(choices.section_role_is_own(place))
        self.assertEqual(self.wizard().field().value(), marks.MSG_WIZARD_ROLE_FROM_PLAN.format(way=planned))
        # A section nobody has the tune in has no such field.
        without = next(place for place in range(len(choices.section_labels())) if not choices.section_has_role(place))
        await self.press(keybindings.WizardPage.TO_TREE)
        await self.go_to_named_branch(labels_text.MSG_WIZARD_FORM_BRANCH)
        await self.press(*[Key.DOWN] * (without + 1), keybindings.WizardPage.INTO_FIELDS)
        self.assertNotIn(label, [field.label for field in self.wizard().fields()])


class TestWizardPlayerRows(WizardTest):
    """A player's rows of numbers under the serial melody style: shown on the player's panel, opened in the Row dialog and kept."""

    async def serial(self):
        choices = self.choices()
        choices.set_genre(A_GENRE_WITH_RHYTHMS)
        choices.set_subgenre(choices.subgenres()[0])
        choices.set_melody(SERIAL)
        await self.press(Key.DOWN, Key.UP)
        role = next(role for role in choices.roles_in() if choices.player_rows(role))
        await self.go_to_named_branch(choices.role_title(role))
        return choices, role

    async def open_row(self, name):
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_ROW_LABELS[name])
        await self.press(Key.ENTER)

    def shown_row(self, *, choices, role, name):
        return marks.MSG_WIZARD_ROW_SEPARATOR.join(str(value) for value in choices.get_player_row(role=role, name=name))

    async def test_the_rows_show_on_the_players_panel_only_under_the_serial_style(self):
        choices, role = await self.serial()
        for name in PLAYER_ROWS:
            self.assertIn(marks.MSG_WIZARD_GENRE_ROW_SHOWN.format(row=self.shown_row(choices=choices, role=role, name=name)), self.text())
        choices.set_melody(None)
        await self.press(Key.DOWN, Key.UP)
        # By the fields' labels, since a row's label may be part of another field's.
        labels = [field.label for field in self.wizard().fields()]
        for name in PLAYER_ROWS:
            self.assertNotIn(labels_text.MSG_WIZARD_ROW_LABELS[name], labels)

    async def test_a_row_is_edited_in_the_row_dialog_and_kept_on_ok(self):
        choices, role = await self.serial()
        before = choices.get_player_row(role=role, name=LENGTHS)
        await self.open_row(LENGTHS)
        self.assertIsInstance(self.app.screen, RowDialog)
        self.assertIn(messages.MSG_WIZARD_ROW_TITLE.format(row=labels_text.MSG_WIZARD_ROW_LABELS[LENGTHS], player=choices.role_title(role)), self.text())
        await self.press(Key.RIGHT, keybindings.RowDialog.MORE, keybindings.RowDialog.DONE)
        after = [before[0], before[1] + 1, *before[2:]]
        self.assertEqual(choices.get_player_row(role=role, name=LENGTHS), after)
        self.assertTrue(choices.player_row_is_own(role=role, name=LENGTHS))
        shown = self.shown_row(choices=choices, role=role, name=LENGTHS)
        self.assertIn(shown, self.text())
        self.assertNotIn(marks.MSG_WIZARD_GENRE_ROW_SHOWN.format(row=shown), self.text())

    async def test_cancel_changes_nothing_and_the_usual_row_gives_the_row_back_to_the_genre(self):
        choices, role = await self.serial()
        usual = choices.get_player_row(role=role, name=LOUDNESS)
        await self.open_row(LOUDNESS)
        await self.press(keybindings.RowDialog.MORE, keybindings.RowDialog.CANCEL)
        self.assertEqual(choices.get_player_row(role=role, name=LOUDNESS), usual)
        await self.press(Key.ENTER, keybindings.RowDialog.MORE, keybindings.RowDialog.DONE)
        self.assertTrue(choices.player_row_is_own(role=role, name=LOUDNESS))
        await self.press(Key.ENTER, keybindings.RowDialog.USUAL, keybindings.RowDialog.DONE)
        self.assertFalse(choices.player_row_is_own(role=role, name=LOUDNESS))
        self.assertEqual(choices.get_player_row(role=role, name=LOUDNESS), usual)

    async def test_a_song_is_made_with_the_row(self):
        choices, role = await self.serial()
        await self.open_row(LENGTHS)
        await self.press(keybindings.RowDialog.MORE, keybindings.RowDialog.DONE, keybindings.WizardPage.TO_TREE)
        row = choices.get_player_row(role=role, name=LENGTHS)
        await self.create()
        self.assertEqual(self.document.song().get_wizard_choices()[PLAYER_ROWS_KEPT], {role: {LENGTHS: row}})


class TestRowDialog(UITest):
    """The Row dialog on its own: the cursor, the numbers held to the row's range, cells inserted and removed between the fewest and the most, and the bars."""

    async def open(self, *, values=A_ROW, lowest=A_ROWS_LOWEST, highest=A_ROWS_HIGHEST):
        self.answers = []
        self.app.push_screen(RowDialog(title=A_ROWS_TITLE, values=values, lowest=lowest, highest=highest, fewest=A_ROWS_FEWEST, most=A_ROWS_MOST, usual=A_USUAL_ROW), self.answers.append)
        await self.settle()
        return self.app.screen

    def drawn_by(self, dialog):
        """The dialog's own lines as text, apart from the page under the dialog."""
        return LINE_BREAK.join(line.plain for line in dialog.lines(CONSOLE_WIDTH - DIALOG_MARGIN))

    async def test_the_cursor_stops_at_both_ends_and_a_number_at_the_lowest_and_highest(self):
        dialog = await self.open()
        await self.press(Key.LEFT)
        self.assertEqual(dialog.place, 0)
        await self.press(*[Key.RIGHT] * (len(A_ROW) + 1))
        self.assertEqual(dialog.place, len(A_ROW) - 1)
        await self.press(*[keybindings.RowDialog.MORE] * (A_ROWS_HIGHEST - A_ROWS_LOWEST + 1))
        self.assertEqual(dialog.values[-1], A_ROWS_HIGHEST)
        await self.press(*[keybindings.RowDialog.LESS] * (A_ROWS_HIGHEST - A_ROWS_LOWEST + 1))
        self.assertEqual(dialog.values[-1], A_ROWS_LOWEST)

    async def test_cells_are_inserted_up_to_the_most_and_removed_down_to_the_fewest(self):
        dialog = await self.open()
        await self.press(keybindings.RowDialog.INSERT_CELL)
        self.assertEqual(dialog.values, [A_ROW[0], *A_ROW])
        self.assertEqual(dialog.place, 1)
        await self.press(*[keybindings.RowDialog.INSERT_CELL] * A_ROWS_MOST)
        self.assertEqual(len(dialog.values), A_ROWS_MOST)
        self.assertNotIn(first_key(keybindings.RowDialog.INSERT_CELL), [key for item in dialog.keys() for key in item.keys])
        await self.press(*[keybindings.RowDialog.REMOVE_CELL] * A_ROWS_MOST)
        self.assertEqual(len(dialog.values), A_ROWS_FEWEST)
        self.assertEqual(dialog.place, 0)

    async def test_ok_answers_with_the_row_cancel_with_nothing_and_the_usual_row_is_put_back(self):
        await self.open()
        await self.press(keybindings.RowDialog.MORE, keybindings.RowDialog.DONE)
        self.assertEqual(self.answers, [[A_ROW[0] + 1, *A_ROW[1:]]])
        await self.open()
        await self.press(keybindings.RowDialog.MORE, keybindings.RowDialog.CANCEL)
        self.assertEqual(self.answers, [None])
        await self.open()
        await self.press(keybindings.RowDialog.USUAL, keybindings.RowDialog.DONE)
        self.assertEqual(self.answers, [A_USUAL_ROW])

    async def test_each_cell_has_a_bar_as_high_as_its_number_and_a_row_under_zero_a_zero_line(self):
        dialog = await self.open()
        drawn = self.drawn_by(dialog)
        self.assertEqual(drawn.count(marks.MSG_ROW_DIALOG_BAR), sum(A_ROW))
        self.assertNotIn(marks.MSG_ROW_DIALOG_ZERO * len(A_ROW) * CELL_WIDTH, drawn.split(LINE_BREAK * 2)[0])
        await self.press(keybindings.RowDialog.CANCEL)
        dialog = await self.open(values=A_SIGNED_ROW, lowest=-A_ROWS_HIGHEST, highest=A_ROWS_HIGHEST)
        drawn = self.drawn_by(dialog)
        self.assertIn(marks.MSG_ROW_DIALOG_ZERO * len(A_SIGNED_ROW) * CELL_WIDTH, drawn.split(LINE_BREAK * 2)[0])
        self.assertEqual(drawn.count(marks.MSG_ROW_DIALOG_BAR), sum(abs(value) for value in A_SIGNED_ROW))

    async def test_the_longest_row_fits_an_80_column_console(self):
        dialog = await self.open(values=[A_ROWS_LOWEST] * A_ROWS_MOST)
        for line in dialog.lines(CONSOLE_WIDTH - DIALOG_MARGIN):
            self.assertLessEqual(line.cell_len, CONSOLE_WIDTH - DIALOG_MARGIN)


class TestWizardComposition(WizardTest):
    """The Composition branch, with the song's Progression, Melody and Hook on the branches under it, and the drums' Fill pattern."""

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
        for name in (labels_text.MSG_WIZARD_COMPOSITION_BRANCH,):
            await self.go_to_named_branch(name)
            await self.press(keybindings.WizardPage.INTO_FIELDS)
            self.assertFalse(self.wizard().in_fields)
            self.assertIn(errors.ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE, self.text())

    async def test_the_progression_is_chosen_on_the_chords_branch(self):
        await self.choose(genre=self.a_genre_with(PROGRESSION_TRAITS))
        choices = self.choices()
        trait = choices.song_trait(PROGRESSION_TRAITS)
        ways = choices.song_ways(trait)
        choices.set_way(trait=trait, value=ways[0])
        await self.go_to_named_branch(labels_text.MSG_WIZARD_CHORDS_BRANCH)
        self.assertIn(ways[0], self.text())
        await self.step(labels_text.MSG_WIZARD_PROGRESSION_LABEL)
        self.assertEqual(choices.get_way(trait), ways[1])

    async def test_a_progression_shows_its_numerals_and_each_kind_of_sections_chords_in_the_songs_key(self):
        await self.choose(genre=A_GENRE_WITH_RHYTHMS)
        choices = self.choices()
        choices.set_root(A_ROOT)
        choices.set_scale_type(MAJOR)
        await self.go_to_named_branch(labels_text.MSG_WIZARD_CHORDS_BRANCH)
        self.assertIn(messages.MSG_WIZARD_CHORDS_DRAWN_LATER, self.text())
        choices.set_way(trait=choices.progression_trait(), value=A_PROGRESSION)
        await self.press(Key.DOWN, Key.UP)
        shown = self.text()
        self.assertNotIn(messages.MSG_WIZARD_CHORDS_DRAWN_LATER, shown)
        self.assertIn(marks.MSG_WIZARD_PROGRESSION_SHOWN.format(name=A_PROGRESSION, numerals=ITS_NUMERALS), shown)
        self.assertIn(marks.MSG_WIZARD_CHORDS_KEY.format(root=A_ROOT, scale=labels_text.MSG_WIZARD_SCALE_TYPE_NAMES[MAJOR]), shown)
        kinds = [kind for kind, _ in choices.progression_chords(A_PROGRESSION)]
        self.assertIn(A_VERSE, kinds)
        self.assertNotIn(A_HELD_KIND, kinds)
        width = max(len(kind) for kind in kinds)
        self.assertIn(marks.MSG_WIZARD_CHORDS_LINE.format(kind=A_VERSE, width=width, chords=ITS_VERSE_CHORDS), shown)
        choices.set_way(trait=choices.progression_trait(), value=A_PLAIN_PROGRESSION)
        choices.set_scale_type(MINOR)
        await self.press(Key.DOWN, Key.UP)
        self.assertIn(marks.MSG_WIZARD_CHORDS_LINE.format(kind=A_VERSE, width=width, chords=ITS_VERSE_CHORDS_IN_MINOR), self.text())
        self.assertIn(marks.MSG_WIZARD_PROGRESSION_SHOWN.format(name=A_PLAIN_PROGRESSION, numerals=ITS_NUMERALS_IN_MINOR), self.text())

    async def test_the_progressions_list_names_each_with_its_numerals(self):
        await self.choose(genre=A_GENRE_WITH_RHYTHMS)
        choices = self.choices()
        choices.set_root(A_ROOT)
        choices.set_scale_type(MAJOR)
        await self.go_to_named_branch(labels_text.MSG_WIZARD_CHORDS_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_PROGRESSION_LABEL)
        await self.press(Key.ENTER)
        self.assertIn(marks.MSG_WIZARD_PROGRESSION_SHOWN.format(name=A_PROGRESSION, numerals=ITS_NUMERALS), self.text())

    async def test_the_hooks_panel_draws_the_hook_the_song_made_will_have(self):
        await self.choose(genre=A_GENRE_WITH_RHYTHMS)
        choices = self.choices()
        await self.go_to_named_branch(labels_text.MSG_WIZARD_HOOKS_BRANCH)
        hook = choices.hook_notes()
        shown = self.text()
        for line in picture_of(hook=hook, width=A_WIDE_PANEL):
            self.assertIn(line, shown)
        self.assertIn(messages.MSG_WIZARD_HOOK_MADE.format(player=choices.role_title(choices.tune_player())), shown)
        for _, _, pitch in hook[2]:
            self.assertIn(note_shown(pitch), shown)
        await self.create()
        self.assertEqual(WizardChoices.from_data(self.document.song().get_wizard_choices()).hook_notes(), hook)

    async def test_new_hook_makes_another_hook_and_goes_with_the_hook(self):
        await self.choose(genre=A_GENRE_WITH_RHYTHMS)
        choices = self.choices()
        await self.go_to_named_branch(labels_text.MSG_WIZARD_HOOKS_BRANCH)
        first = choices.hook_notes()
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_NEW_HOOK_BUTTON)
        await self.press(Key.ENTER)
        self.assertNotEqual(choices.hook_notes(), first)
        for line in picture_of(hook=choices.hook_notes(), width=A_WIDE_PANEL):
            self.assertIn(line, self.text())
        await self.press(keybindings.WizardPage.TO_TREE)
        choices.set_hook(False)
        await self.press(Key.DOWN, Key.UP)
        self.assertNotIn(labels_text.MSG_WIZARD_NEW_HOOK_BUTTON, self.text())

    async def test_the_hooks_picture_goes_with_the_hook(self):
        await self.choose(genre=A_GENRE_WITH_RHYTHMS)
        choices = self.choices()
        await self.go_to_named_branch(labels_text.MSG_WIZARD_HOOKS_BRANCH)
        self.assertIn(marks.MSG_WIZARD_HOOK_CELL, self.text())
        choices.set_hook(False)
        await self.press(Key.DOWN, Key.UP)
        self.assertNotIn(marks.MSG_WIZARD_HOOK_CELL, self.text())

    def test_a_note_of_the_picture_leaves_its_last_cell_empty_and_a_long_hook_is_drawn_narrow(self):
        hook = (A_HOOKS_STEPS, A_HOOKS_STEPS, [(0, 2, A_PITCH), (2, 2, A_PITCH), (4, 1, A_PITCH + 1)])
        high, low, floor = picture_of(hook=hook, width=A_WIDE_PANEL)
        self.assertIn(marks.MSG_WIZARD_HOOK_BAR_LINE + (marks.MSG_WIZARD_HOOK_CELL * 3 + marks.MSG_WIZARD_HOOK_GAP) * 2, low)
        self.assertIn(marks.MSG_WIZARD_HOOK_CELL, high)
        self.assertEqual(len(high), len(low))
        self.assertEqual(len(floor), len(low))
        narrow = picture_of(hook=hook, width=A_NARROW_PANEL)
        self.assertLess(len(narrow[1]), len(low))
        self.assertIn(marks.MSG_WIZARD_HOOK_BAR_LINE + (marks.MSG_WIZARD_HOOK_CELL + marks.MSG_WIZARD_HOOK_GAP) * 2, narrow[1])

    async def test_the_hook_is_switched_on_the_hooks_branch(self):
        await self.choose(genre=A_GENRE_WITH_RHYTHMS)
        choices = self.choices()
        self.assertTrue(choices.has_hook())
        await self.go_to_named_branch(labels_text.MSG_WIZARD_HOOKS_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_HOOK_LABEL)
        await self.press(Key.SPACE)
        self.assertFalse(choices.has_hook())
        self.assertIn(labels_text.MSG_WIZARD_HOOK_LABEL, self.text())
        await self.press(Key.SPACE)
        self.assertTrue(choices.has_hook())

    async def test_the_smart_melody_styles_gauges_show_under_the_melody_field_and_are_stepped(self):
        await self.choose(genre=A_GENRE_WITH_RHYTHMS)
        choices = self.choices()
        # The phrasing fields of a planned song, whose choices use some of the gauges' words, are left off the panel.
        choices.set_song_plan(False)
        await self.go_to_named_branch(labels_text.MSG_WIZARD_MELODY_BRANCH)
        for name in DEFAULT_GAUGES:
            self.assertNotIn(labels_text.MSG_WIZARD_GAUGE_ENDS[name][1], self.text())
        choices.set_melody(SMART)
        await self.press(Key.DOWN, Key.UP)
        shown = self.text()
        for name in DEFAULT_GAUGES:
            self.assertIn(labels_text.MSG_WIZARD_GAUGE_LABELS[name], shown)
            self.assertIn(marks.MSG_WIZARD_MELODY_GAUGE_SHOWN.format(gauge=self.gauge_drawn(choices.get_gauge(name)), low=labels_text.MSG_WIZARD_GAUGE_ENDS[name][0], high=labels_text.MSG_WIZARD_GAUGE_ENDS[name][1]), shown)
        for name in DEFAULT_GAUGES:
            before = choices.get_gauge(name)
            await self.step(labels_text.MSG_WIZARD_GAUGE_LABELS[name])
            self.assertEqual(choices.get_gauge(name), before + 1)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_GAUGE_LABELS[GAUGE_MOVES])
        await self.press(*[key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET)] * HIGHEST_GAUGE)
        self.assertEqual(choices.get_gauge(GAUGE_MOVES), HIGHEST_GAUGE)
        self.assertNotIn(marks.MSG_WIZARD_GAUGE_EMPTY, self.wizard().field().value())

    async def test_a_melody_styles_own_settings_show_while_the_style_is_in_use_and_are_changed(self):
        await self.choose(genre=A_GENRE_WITH_RHYTHMS)
        choices = self.choices()
        await self.go_to_named_branch(labels_text.MSG_WIZARD_MELODY_BRANCH)
        for name in (MOVE, LEAPS):
            self.assertNotIn(labels_text.MSG_WIZARD_MELODY_SETTING_LABELS[name], self.text())
        choices.set_melody(EVOLVING)
        await self.press(Key.DOWN, Key.UP)
        self.assertIn(labels_text.MSG_WIZARD_MELODY_SETTING_LABELS[MOVE], self.text())
        before = choices.get_melody_setting(MOVE)
        await self.step(labels_text.MSG_WIZARD_MELODY_SETTING_LABELS[MOVE])
        self.assertEqual(choices.get_melody_setting(MOVE), before + 1)
        choices.set_melody(SERIAL)
        await self.press(Key.DOWN, Key.UP)
        self.assertNotIn(labels_text.MSG_WIZARD_MELODY_SETTING_LABELS[MOVE], self.text())
        self.assertFalse(choices.get_melody_setting(LEAPS))
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_MELODY_SETTING_LABELS[LEAPS])
        await self.press(Key.SPACE)
        self.assertTrue(choices.get_melody_setting(LEAPS))

    def gauge_drawn(self, position):
        return marks.MSG_WIZARD_GAUGE_FULL * position + marks.MSG_WIZARD_GAUGE_EMPTY * (HIGHEST_GAUGE - position)

    async def test_the_progression_starts_on_any_and_is_left_to_chance_again_from_the_field(self):
        await self.choose(genre=self.a_genre_with(PROGRESSION_TRAITS))
        choices = self.choices()
        await self.go_to_named_branch(labels_text.MSG_WIZARD_CHORDS_BRANCH)
        self.assertTrue(choices.has_any_progression())
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels_text.MSG_WIZARD_PROGRESSION_LABEL)
        self.assertEqual(self.wizard().field().value(), labels_text.MSG_WIZARD_ANY_PROGRESSION)
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertFalse(choices.has_any_progression())
        self.assertEqual(choices.get_way(choices.progression_trait()), choices.song_ways(choices.progression_trait())[0])
        await self.press(key_of(binding=keybindings.WizardPage.LESS, key=Key.LEFT_BRACKET))
        self.assertTrue(choices.has_any_progression())

    async def test_the_melody_left_to_the_genre_names_the_genres_own_style(self):
        await self.choose(genre=self.a_genre_with(PROGRESSION_TRAITS))
        choices = self.choices()
        await self.go_to_named_branch(labels_text.MSG_WIZARD_MELODY_BRANCH)
        self.assertIn(marks.MSG_WIZARD_GENRE_MELODY_SHOWN.format(style=choices.genre_melody()), self.text())
        self.assertNotIn(choices.genre_melody(), choices.melody_styles())
        await self.step(labels_text.MSG_WIZARD_MELODY_LABEL)
        self.assertEqual(choices.get_melody(), choices.melody_styles()[0])
        self.assertNotIn(labels_text.MSG_WIZARD_USUAL_MELODY, self.text())

    async def test_a_progression_written_for_the_other_scale_type_says_so_and_may_still_be_chosen(self):
        await self.choose(genre=A_GENRE_WITH_RHYTHMS)
        choices = self.choices()
        trait = choices.progression_trait()
        ways = choices.song_ways(trait)
        other = next(way for way in ways if choices.progression_scale_type(way) != choices.get_scale_type())
        same = next(way for way in ways if choices.progression_scale_type(way) == choices.get_scale_type())
        choices.set_way(trait=trait, value=other)
        await self.go_to_named_branch(labels_text.MSG_WIZARD_CHORDS_BRANCH)
        marked = marks.MSG_WIZARD_PROGRESSION_FOR.format(progression='', scale=labels_text.MSG_WIZARD_SCALE_TYPE_NAMES[choices.progression_scale_type(other)])
        self.assertIn(other, self.text())
        self.assertIn(marked, self.text())
        choices.set_way(trait=trait, value=same)
        await self.press(Key.DOWN, Key.UP)
        self.assertNotIn(marks.MSG_WIZARD_PROGRESSION_FOR.format(progression='', scale=labels_text.MSG_WIZARD_SCALE_TYPE_NAMES[choices.progression_scale_type(same)]), self.text())

    async def test_the_melody_starts_on_usual_and_another_style_is_chosen_and_made(self):
        await self.choose(genre=self.a_genre_with(PROGRESSION_TRAITS))
        choices = self.choices()
        await self.go_to_named_branch(labels_text.MSG_WIZARD_MELODY_BRANCH)
        self.assertIn(labels_text.MSG_WIZARD_USUAL_MELODY, self.text())
        self.assertIsNone(choices.get_melody())
        await self.step(labels_text.MSG_WIZARD_MELODY_LABEL)
        self.assertEqual(choices.get_melody(), choices.melody_styles()[0])
        await self.create()
        self.assertIsInstance(self.app.screen, ArrangePage)

    async def test_composition_shows_what_each_branch_under_it_is_set_to(self):
        await self.choose(genre=A_GENRE_WITH_RHYTHMS)
        choices = self.choices()
        choices.set_melody(SMART)
        choices.set_hook(False)
        await self.go_to_named_branch(labels_text.MSG_WIZARD_COMPOSITION_BRANCH)
        shown = self.text()
        for name, value in ((labels_text.MSG_WIZARD_CHORDS_BRANCH, labels_text.MSG_WIZARD_ANY_PROGRESSION), (labels_text.MSG_WIZARD_MELODY_BRANCH, SMART), (labels_text.MSG_WIZARD_HOOKS_BRANCH, labels_text.MSG_WIZARD_HOOK_OFF)):
            self.assertIn(marks.MSG_WIZARD_COMPOSITION_LINE.format(name=name, width=len(WIDEST_COMPOSITION_BRANCH), value=value), shown)
        choices.set_hook(True)
        await self.press(Key.DOWN, Key.UP)
        self.assertIn(marks.MSG_WIZARD_COMPOSITION_LINE.format(name=labels_text.MSG_WIZARD_HOOKS_BRANCH, width=len(WIDEST_COMPOSITION_BRANCH), value=labels_text.MSG_WIZARD_HOOK_ON), self.text())

    async def test_composition_leaves_out_a_branch_with_nothing_to_choose(self):
        await self.choose(genre=A_GENRE_WITH_NO_HOOK)
        await self.go_to_named_branch(labels_text.MSG_WIZARD_COMPOSITION_BRANCH)
        self.assertFalse(self.choices().can_have_hook())
        self.assertNotIn(marks.MSG_WIZARD_COMPOSITION_LINE.format(name=labels_text.MSG_WIZARD_HOOKS_BRANCH, width=len(WIDEST_COMPOSITION_BRANCH), value=labels_text.MSG_WIZARD_HOOK_OFF), self.text())
        await self.go_to_named_branch(labels_text.MSG_WIZARD_HOOKS_BRANCH)
        # With no hook to switch, the panel offers a riff where a player of the band can play one, and else says there is nothing to choose.
        labels = [field.label for field in self.wizard().fields()]
        self.assertNotIn(labels_text.MSG_WIZARD_HOOK_LABEL, labels)
        if self.choices().riff_players_offered():
            self.assertEqual(labels, [labels_text.MSG_WIZARD_GROUP_RIFF, labels_text.MSG_WIZARD_RIFF_PLAYED_BY_LABEL])
        else:
            self.assertIn(messages.MSG_WIZARD_NOTHING_TO_CHOOSE, self.text())

    async def go_to_the_drums(self):
        choices = self.choices()
        await self.go_to_named_branch(choices.role_title(next(role for role in choices.roles_in() if not choices.has_sound(role))))

    async def test_the_fill_pattern_is_chosen_on_the_drums_branch(self):
        await self.choose(genre=self.a_genre_with(FILLS_TRAITS))
        choices = self.choices()
        trait = choices.song_trait(FILLS_TRAITS)
        ways = choices.song_ways(trait)
        choices.set_way(trait=trait, value=ways[0])
        await self.go_to_the_drums()
        await self.step(labels_text.MSG_WIZARD_FILLS_LABEL)
        self.assertEqual(choices.get_way(trait), ways[1])

    async def test_a_fill_pattern_with_one_way_is_not_shown(self):
        empty = [genre for genre in genre_names() if not self.fields_of(genre=genre, traits=(FILLS_TRAITS,))]
        self.assertTrue(empty)
        await self.choose(genre=empty[0])
        for place in range(len(self.wizard().rows())):
            await self.go_to_branch(place)
            self.assertNotIn(labels_text.MSG_WIZARD_FILLS_LABEL, self.text())

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
        self.assertIn(labels_text.MSG_WIZARD_START_TITLE, text)
        for start in STARTS:
            self.assertIn(labels_text.MSG_WIZARD_START_NAMES[start], text)
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, ArrangePage)

    async def test_the_last_row_of_the_dialog_is_cancel_which_opens_no_wizard(self):
        await self.make_a_song_and_open_the_wizard_on_it()
        self.assertIn(labels_text.MSG_WIZARD_START_CANCEL, self.text())
        await self.press(*[Key.DOWN] * len(STARTS), Key.ENTER)
        self.assertIsInstance(self.app.screen, ArrangePage)

    async def test_the_wizard_asks_before_closing_and_names_no_choices_until_something_is_changed_after_the_start(self):
        await self.make_a_song_and_open_the_wizard_on_it()
        await self.start_with(NEW_FROM_LAST)
        self.assertIsInstance(self.app.screen, WizardPage)
        await self.press(Key.ESCAPE)
        self.assertIn(messages.MSG_WIZARD_CLOSE_UNCHANGED_QUESTION, self.text())
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertIsInstance(self.app.screen, ArrangePage)

    async def test_a_new_song_from_the_last_settings_starts_with_the_songs_choices_and_a_name_of_its_own(self):
        first = await self.make_a_song_and_open_the_wizard_on_it()
        kept = self.document.song().get_wizard_choices()
        await self.start_with(NEW_FROM_LAST)
        self.assertEqual(self.wizard().start(), NEW_FROM_LAST)
        # The run keeps the song's choices and draws a seed of its own at once, so that what a panel shows is what Apply makes.
        self.assertEqual({**self.choices().to_data(), SEED: None}, {**kept, SEED: None})
        drawn = self.choices().get_seed()
        self.assertNotEqual(drawn, kept[SEED])
        self.assertNotEqual(self.wizard().song_name(), first)
        self.assertFalse(self.wizard().replaces())
        await self.create()
        self.assertEqual(len(self.document.song_names()), 3)
        # The settings are kept and the dice rolled again, as on every run, and the song is made with the seed the run drew.
        self.assertEqual({**self.document.song().get_wizard_choices(), SEED: None}, {**kept, SEED: None})
        self.assertEqual(self.document.song().get_wizard_choices()[SEED], drawn)

    async def test_a_new_song_from_scratch_starts_with_nothing_chosen(self):
        await self.make_a_song_and_open_the_wizard_on_it()
        await self.start_with(NEW_FROM_SCRATCH)
        self.assertEqual(list(self.choices().to_data()), [SEED])
        await self.go_to_named_branch(labels_text.MSG_WIZARD_CREATE_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        self.assertIn(errors.ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE, self.text())

    async def test_replacing_from_the_last_settings_keeps_the_settings_rolls_the_dice_again_and_leaves_nothing_behind(self):
        first = await self.make_a_song_and_open_the_wizard_on_it()
        kept = self.document.song().get_wizard_choices()
        patterns = len(self.document.setlist().get_pattern_names())
        await self.start_with(REPLACE_FROM_LAST)
        self.assertIn(first, self.wizard().caption())
        await self.create()
        self.assertIsInstance(self.app.screen, ArrangePage)
        self.assertIn(messages.MSG_WIZARD_REPLACED.format(name=first), self.text())
        self.assertEqual(self.document.song_names(), [names.MSG_DEFAULT_SONG_NAME, first])
        now = self.document.song().get_wizard_choices()
        self.assertNotEqual(now[SEED], kept[SEED])
        self.assertEqual({**now, SEED: None}, {**kept, SEED: None})
        # Another roll of the dice may need a pattern more or fewer, so the set holds what it held, less the old song's
        # patterns and with the new song's.
        self.assertEqual(len(self.document.setlist().get_pattern_names()), patterns - self.patterns_made_from(kept) + self.patterns_made_from(now))

    def patterns_made_from(self, kept):
        """How many patterns the song made from the kept choices has."""
        return len(WizardChoices.from_data(kept).made_setlist(name=A_SONG_NAME, version=VERSION).get_pattern_names())

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
        await self.select_field(labels_text.MSG_NAME_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, WizardPage)
        await self.press(keybindings.WizardPage.TO_TREE)
        await self.create()
        self.assertEqual(self.document.song_names(), [names.MSG_DEFAULT_SONG_NAME, first, third])
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
        self.assertIn(messages.MSG_WIZARD_CREATED.format(name=name), self.text())
        for pattern in starter:
            self.assertFalse(self.document.setlist().has_pattern(pattern))
        await self.press(keybindings.Page.UNDO)
        self.assertEqual(self.document.setlist().to_data(), before)
        self.assertEqual(self.document.song_names(), [names.MSG_DEFAULT_SONG_NAME])

    async def test_a_song_that_was_changed_is_kept_and_the_new_song_added_beside_it(self):
        self.document.set_tempo(self.document.song().get_tempo() + 1)
        await self.choose_genre_and_subgenre()
        name = self.wizard().song_name()
        await self.create()
        self.assertEqual(self.document.song_names(), [names.MSG_DEFAULT_SONG_NAME, name])


class TestWizardPageUndo(WizardTest):
    """Undo and the wizard: nothing to undo while it is open, and Create is one step."""

    async def test_undo_and_redo_do_nothing_in_the_wizard_and_say_why(self):
        await self.choose_genre_and_subgenre()
        chosen = self.choices().to_data()
        for key in (keybindings.Page.UNDO, keybindings.Page.REDO):
            await self.press(key)
            self.assertIsInstance(self.app.screen, WizardPage)
            self.assertIn(messages.MSG_WIZARD_NOTHING_TO_UNDO, self.text())
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
        self.assertEqual(self.document.current_song_name(), names.MSG_DEFAULT_SONG_NAME)
        self.assertIsInstance(self.app.screen, ArrangePage)
        self.assertIn(fixed_text(messages.MSG_UNDONE), self.text())
        await self.press(keybindings.Page.REDO)
        self.assertEqual(self.document.setlist().to_data(), after)
        self.assertEqual(self.document.current_song_name(), name)
        self.assertIn(fixed_text(messages.MSG_RESTORED), self.text())
