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

"""The song wizard's Composition panels: Melody, a kind of section's melody, Riffs, Riff Assign and Section Players."""

from llamatron.composition.file_format import Row
from llamatron.macro_composer.melody import HEIGHT, HIGH, LOW, REPEATS, REPEATS_A_LOT
from llamatron.macro_composer.riffs import ACCENT_CHORDS, RIFF_BARS, RIFF_BETWEEN, RIFF_NOTES, RIFF_WITH_CHORDS, STAYS_HOME
from llamatron.macro_composer.wizard_choices import ACCOMPANIMENT, MELODY_BUSY, MELODY_RANGE, MELODY_SPARSE, MELODY_WAYS, MELODY_WIDE, SMOOTH
from llamatron.strings import labels, marks, messages, names
from llamatron.tui import keybindings
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.dialogs.new_riff_dialog import NewRiffDialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.drawing import Style
from llamatron.tui.keys import Key
from llamatron.tui.screens.pattern.pattern_editor import PatternEditor
from llamatron.tui.screens.shared.field import Heading
from llamatron.tui.screens.wizard.section_melody_branch import MELODY_KEY
from llamatron.tui.screens.wizard.wizard_page import WizardPage
from tests.tui.test_tui_wizard import WizardTest

A_GENRE = 'rock'
A_SUBGENRE = 'folk rock'
A_RIFF_SUBGENRE = 'hard rock'
A_KIND = 'verse'
THE_GUITAR = 'guitar'
THE_BASS = 'bass'
A_DEGREE = 7
A_NEW_NAME = 'main riff'
FIRST_RIFF = names.MSG_NEW_RIFF_WORD + '-1'
# The attribute a field keeps its label in.
LABEL = 'label'


class CompositionTest(WizardTest):
    """The wizard on a song of a subgenre, with the steps the Composition panels' tests share."""

    SUBGENRE = A_SUBGENRE

    async def asyncSetUp(self):
        await super().asyncSetUp()
        choices = self.choices()
        choices.set_genre(A_GENRE)
        choices.set_subgenre(self.SUBGENRE)
        await self.press(Key.DOWN, Key.UP)

    async def open_panel(self, key):
        """Move the tree's cursor to a panel by what the page remembers it by, and go into its fields."""
        await self.go_to_branch([branch.key() for _, branch in self.wizard().rows()].index(key))
        await self.press(keybindings.WizardPage.INTO_FIELDS)

    async def open_heading(self, label):
        await self.select_field(label)
        if not self.wizard().is_open(self.wizard().field()):
            await self.press(keybindings.FieldPage.TOGGLE)

    async def select_under(self, *, heading, label):
        """Move the cursor to a field under a heading, which is opened first, since two headings may hold fields of one label."""
        await self.open_heading(heading)
        page = self.wizard()
        for _ in page.shown_fields():
            if page.label_under_cursor() != label:
                await self.press(Key.DOWN)
        self.assertEqual(page.label_under_cursor(), label)
        self.assertEqual(page.heading_over_cursor(), heading)

    def title(self, role):
        return self.choices().role_title(role)

    def change_first_step(self):
        """Write another degree on the first step of the pattern the editor shows, as a key in the editor would."""
        editor = self.app.screen
        editor.document().set_step_value(name=editor.item, row=Row.DEGREE, step=0, value=A_DEGREE)

    def field_labels(self):
        return [getattr(field, LABEL, None) for field in self.wizard().shown_fields()]


class TestWizardMelody(CompositionTest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_panel(labels.MSG_WIZARD_MELODY_BRANCH)

    async def test_the_panel_holds_who_plays_the_melody_then_what_every_melody_shares_and_the_phrasing(self):
        choices = self.choices()
        ways = [labels.MSG_WIZARD_MELODY_WAY_LABELS[field] for field in choices.melody_fields()]
        self.assertEqual(self.field_labels()[:len(ways) + 2], [labels.MSG_WIZARD_TUNE_LABEL, *ways, labels.MSG_WIZARD_CHARACTER_LABEL])
        self.assertIn(labels.MSG_WIZARD_PHRASING_LABEL, self.field_labels())
        self.assertEqual(set(choices.melody_fields()), {MELODY_BUSY, MELODY_RANGE, REPEATS})

    async def test_each_field_is_chosen_from_its_list_and_changes_the_song(self):
        choices = self.choices()
        for field, value in ((MELODY_BUSY, MELODY_SPARSE), (MELODY_RANGE, MELODY_WIDE), (REPEATS, REPEATS_A_LOT)):
            before = choices.made_for_listening()[0].to_data()
            await self.select_field(labels.MSG_WIZARD_MELODY_WAY_LABELS[field])
            await self.press(Key.ENTER)
            self.assertEqual(list(self.app.screen.options), list(MELODY_WAYS[field]))
            await self.pick(value)
            self.assertEqual(choices.get_melody_way(field), value)
            self.assertNotEqual(choices.made_for_listening()[0].to_data(), before)

    async def test_the_character_is_the_genres_until_one_is_chosen_and_the_first_entry_gives_it_back(self):
        choices = self.choices()
        await self.select_field(labels.MSG_WIZARD_CHARACTER_LABEL)
        self.assertEqual(self.wizard().field().value(), labels.MSG_WIZARD_USUAL_MELODY)
        await self.press(Key.ENTER)
        self.assertEqual(list(self.app.screen.options), [labels.MSG_WIZARD_USUAL_MELODY, *choices.melody_characters_offered()])
        await self.pick(SMOOTH)
        self.assertEqual(choices.get_melody_character(), SMOOTH)
        await self.press(Key.ENTER)
        await self.pick(labels.MSG_WIZARD_USUAL_MELODY)
        self.assertIsNone(choices.get_melody_character())

    async def test_the_melody_is_given_to_another_player(self):
        choices = self.choices()
        other = next(role for role in choices.tune_players_offered() if role != choices.tune_played_by())
        title = self.title(other)
        await self.select_field(labels.MSG_WIZARD_TUNE_LABEL)
        await self.press(Key.ENTER)
        await self.pick(title)
        self.assertEqual(choices.tune_played_by(), other)


class TestWizardSectionMelody(CompositionTest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_panel(MELODY_KEY.format(kind=A_KIND))

    async def test_height_is_the_genres_until_chosen_and_busy_is_the_songs_until_chosen(self):
        choices = self.choices()
        await self.select_field(labels.MSG_WIZARD_HEIGHT_LABEL)
        self.assertEqual(self.wizard().field().value(), labels.MSG_WIZARD_VALUE_FROM.format(value=choices.genre_height_in(A_KIND), origin=labels.MSG_WIZARD_USUAL_MELODY))
        before = choices.made_for_listening()[0].to_data()
        other = HIGH if choices.genre_height_in(A_KIND) != HIGH else LOW
        await self.press(Key.ENTER)
        await self.pick(other)
        self.assertEqual(choices.get_section_melody(kind=A_KIND, field=HEIGHT), other)
        self.assertNotEqual(choices.made_for_listening()[0].to_data(), before)
        await self.select_field(labels.MSG_WIZARD_SECTION_BUSY_LABEL)
        self.assertEqual(self.wizard().field().value(), labels.MSG_WIZARD_VALUE_FROM.format(value=choices.get_melody_way(MELODY_BUSY), origin=labels.MSG_WIZARD_FROM_SONG))
        await self.press(Key.ENTER)
        await self.pick(MELODY_SPARSE)
        self.assertEqual(choices.get_section_melody(kind=A_KIND, field=MELODY_BUSY), MELODY_SPARSE)
        await self.press(Key.ENTER)
        await self.pick(labels.MSG_WIZARD_FROM_SONG)
        self.assertIsNone(choices.get_section_melody(kind=A_KIND, field=MELODY_BUSY))

    async def test_the_notes_open_in_the_pattern_editor_are_kept_when_edited_and_given_back_with_bksp(self):
        choices = self.choices()
        await self.select_field(labels.MSG_WIZARD_NOTES_LABEL)
        self.assertEqual(self.wizard().field().value(), labels.MSG_WIZARD_NOTES_WIZARD)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.change_first_step()
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, WizardPage)
        self.assertTrue(choices.tune_is_own(A_KIND))
        self.assertEqual(self.wizard().field().value(), labels.MSG_WIZARD_NOTES_EDITED)
        await self.press(keybindings.WizardPage.CLEAR)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertFalse(choices.tune_is_own(A_KIND))

    async def test_regenerate_asks_first_starting_on_no_and_writes_another_melody_with_nothing_kept(self):
        choices = self.choices()
        first = choices.tune_pattern(A_KIND)
        await self.press(keybindings.WizardPage.REGENERATE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        name = messages.MSG_WIZARD_MELODY_OF.format(kind=A_KIND)
        self.assertEqual(self.app.screen.title, messages.MSG_WIZARD_REGENERATE_TITLE.format(name=name))
        await self.press(Key.ENTER)
        self.assertEqual(choices.tune_pattern(A_KIND), first)
        await self.select_field(labels.MSG_WIZARD_REGENERATE_BUTTON)
        await self.press(Key.ENTER, keybindings.ConfirmDialog.YES)
        self.assertNotEqual(choices.tune_pattern(A_KIND), first)
        self.assertIn(messages.MSG_WIZARD_REGENERATED.format(name=name), self.text())

    async def test_the_panel_has_buttons_to_listen_and_to_regenerate_and_listen_names_the_melody(self):
        for button in (labels.MSG_WIZARD_LISTEN_BUTTON, labels.MSG_WIZARD_REGENERATE_BUTTON):
            self.assertIn(button, self.field_labels())
        what, place, track = self.wizard().branch().listens()
        self.assertEqual(what, messages.MSG_WIZARD_MELODY_OF.format(kind=A_KIND))
        self.assertEqual((place, track), (self.choices().tune_place(A_KIND), self.choices().tune_player_in(A_KIND)))

    async def test_only_the_panel_of_the_kind_that_says_the_hook_line_holds_the_hook(self):
        kind, _ = self.choices().hook_line_place()
        self.assertEqual(labels.MSG_WIZARD_HOOK_LINE_LABEL in self.field_labels(), kind == A_KIND)
        await self.press(keybindings.WizardPage.TO_TREE)
        await self.open_panel(MELODY_KEY.format(kind=kind))
        self.assertIn(labels.MSG_WIZARD_HOOK_LINE_LABEL, self.field_labels())
        self.assertIn(labels.MSG_WIZARD_NEW_HOOK_BUTTON, self.field_labels())
        self.assertIn(marks.MSG_WIZARD_HOOK_CELL, self.text())


class TestWizardRiffs(CompositionTest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_panel(labels.MSG_WIZARD_RIFFS_BRANCH)

    async def add(self, *, role=THE_GUITAR, keys=()):
        """Add a riff for a player from the player's heading, pressing keys in the New Riff dialog before writing."""
        await self.select_field(self.title(role))
        await self.press(keybindings.WizardPage.ADD)
        self.assertIsInstance(self.app.screen, NewRiffDialog)
        await self.press(*keys, keybindings.NewRiffDialog.WRITE)

    async def test_a_heading_for_each_player_who_can_have_a_riff_is_closed_at_first_and_says_how_many_it_holds(self):
        choices = self.choices()
        headings = [field for field in self.wizard().shown_fields() if isinstance(field, Heading)]
        self.assertEqual([heading.label for heading in headings], [self.title(role) for role in choices.riff_instruments()])
        for heading in headings:
            self.assertFalse(self.wizard().is_open(heading))
            self.assertEqual(heading.value(), marks.MSG_WIZARD_COUNT_SHOWN.format(count=0))

    async def test_add_opens_the_new_riff_dialog_and_the_riff_written_is_under_the_cursor_with_its_heading_open(self):
        await self.add()
        choices = self.choices()
        self.assertEqual(choices.riffs_for(THE_GUITAR), [FIRST_RIFF])
        self.assertEqual(self.wizard().label_under_cursor(), FIRST_RIFF)
        self.assertEqual(self.wizard().heading_over_cursor(), self.title(THE_GUITAR))
        self.assertIn(messages.MSG_WIZARD_RIFF_WRITTEN.format(riff=FIRST_RIFF, player=self.title(THE_GUITAR)), self.text())
        self.assertIn(labels.MSG_WIZARD_RIFF_COLUMNS, self.text())
        self.assertEqual(self.wizard().field().value(), marks.MSG_WIZARD_RIFF_ROW.format(bars=RIFF_BARS, used=''))

    async def test_the_dialog_asks_of_the_gaps_only_for_notes_and_chords_and_answers_what_was_chosen(self):
        choices = self.choices()
        guitar = self.title(THE_GUITAR)
        await self.select_field(guitar)
        await self.press(keybindings.WizardPage.ADD)
        dialog = self.app.screen
        self.assertEqual(dialog.title, labels.MSG_NEW_RIFF_TITLE.format(player=guitar))
        self.assertNotIn(RIFF_BETWEEN, dialog.rows())
        await self.press(Key.DOWN, keybindings.NewRiffDialog.MORE)
        self.assertEqual(dialog.settings[RIFF_NOTES], ACCENT_CHORDS)
        self.assertIn(RIFF_BETWEEN, dialog.rows())
        await self.press(Key.DOWN, keybindings.NewRiffDialog.TOGGLE)
        self.assertEqual(dialog.settings[RIFF_WITH_CHORDS], STAYS_HOME)
        await self.press(Key.DOWN, Key.DOWN, keybindings.NewRiffDialog.PRESS)
        riff = choices.riffs_for(THE_GUITAR)[0]
        self.assertEqual(choices.riff_setting(riff=riff, field=RIFF_NOTES), ACCENT_CHORDS)
        self.assertEqual(choices.riff_setting(riff=riff, field=RIFF_WITH_CHORDS), STAYS_HOME)

    async def test_escape_in_the_dialog_writes_nothing_and_the_add_row_adds_as_the_key_does(self):
        await self.select_field(self.title(THE_GUITAR))
        await self.press(keybindings.WizardPage.ADD, Key.ESCAPE)
        self.assertEqual(self.choices().riff_names(), [])
        await self.open_heading(self.title(THE_GUITAR))
        await self.press(Key.DOWN)
        self.assertEqual(self.wizard().label_under_cursor(), marks.MSG_ADD_ROW_MARK)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, NewRiffDialog)
        await self.press(keybindings.NewRiffDialog.WRITE)
        self.assertEqual(self.choices().riff_names(), [FIRST_RIFF])

    async def test_enter_opens_the_riffs_notes_and_notes_changed_mark_the_riff_edited(self):
        await self.add()
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.change_first_step()
        await self.press(Key.ESCAPE)
        self.assertTrue(self.choices().riff_is_edited(FIRST_RIFF))
        self.assertIn(marks.MSG_WIZARD_TUNE_EDITED.format(name=marks.MSG_WIZARD_RIFF_ROW.format(bars=RIFF_BARS, used='').rstrip()), self.text())

    async def test_a_riff_is_renamed_copied_for_another_player_and_regenerated_after_a_question(self):
        await self.add()
        choices = self.choices()
        await self.press(keybindings.WizardPage.RENAME_RIFF)
        self.assertIsInstance(self.app.screen, PromptDialog)
        await self.press(*[Key.BACKSPACE] * len(FIRST_RIFF))
        await self.type(A_NEW_NAME)
        await self.press(Key.ENTER)
        self.assertEqual(choices.riff_names(), [A_NEW_NAME])
        self.assertEqual(self.wizard().label_under_cursor(), A_NEW_NAME)
        bass = self.title(THE_BASS)
        await self.press(keybindings.WizardPage.COPY)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        await self.pick(bass)
        copy = choices.riffs_for(THE_BASS)[0]
        self.assertEqual(self.wizard().label_under_cursor(), copy)
        self.assertEqual(self.wizard().heading_over_cursor(), bass)
        before = choices.riff_heard(copy)[0].to_data()
        await self.press(keybindings.WizardPage.REGENERATE)
        self.assertEqual(self.app.screen.title, messages.MSG_WIZARD_REGENERATE_TITLE.format(name=copy))
        await self.press(Key.ENTER)
        self.assertEqual(choices.riff_heard(copy)[0].to_data(), before)
        await self.press(keybindings.WizardPage.REGENERATE, keybindings.ConfirmDialog.YES)
        self.assertNotEqual(choices.riff_heard(copy)[0].to_data(), before)

    async def test_delete_asks_in_red_saying_where_the_riff_is_used_and_starts_on_no(self):
        await self.add()
        choices = self.choices()
        choices.set_section_part(kind=A_KIND, role=THE_GUITAR, part=FIRST_RIFF)
        await self.press(keybindings.WizardPage.CLEAR)
        dialog = self.app.screen
        self.assertIsInstance(dialog, ConfirmDialog)
        self.assertEqual(dialog.title, messages.MSG_WIZARD_DELETE_RIFF_TITLE.format(riff=FIRST_RIFF))
        self.assertEqual(dialog.heading(0).style, Style.DELETE_TITLE)
        self.assertEqual(dialog.messages, [messages.MSG_WIZARD_RIFF_USED_IN.format(kinds=A_KIND)])
        await self.press(Key.ENTER)
        self.assertEqual(choices.riff_names(), [FIRST_RIFF])
        await self.press(keybindings.WizardPage.CLEAR, keybindings.ConfirmDialog.YES)
        self.assertEqual(choices.riff_names(), [])
        self.assertEqual(choices.section_part(kind=A_KIND, role=THE_GUITAR), ACCOMPANIMENT)

    async def test_listen_plays_the_riff_under_the_cursor_alone_in_a_song_where_its_player_plays_it(self):
        await self.add()
        what, place, track, made = self.wizard().branch().listens()
        self.assertEqual((what, track), (FIRST_RIFF, THE_GUITAR))
        setlist, name = made
        self.assertIsNotNone(setlist.get_song(name).get_scenes()[place].get_clip_slot(THE_GUITAR))
        await self.select_field(self.title(THE_GUITAR))
        self.assertIsNone(self.wizard().branch().listens())


class TestWizardGenreRiff(CompositionTest):

    SUBGENRE = A_RIFF_SUBGENRE

    async def test_the_genres_riff_arrives_written_under_its_players_heading_with_where_it_is_used(self):
        await self.open_panel(labels.MSG_WIZARD_RIFFS_BRANCH)
        choices = self.choices()
        self.assertEqual(choices.riff_names(), [FIRST_RIFF])
        heading = next(field for field in self.wizard().shown_fields() if field.label == self.title(THE_GUITAR))
        self.assertEqual(heading.value(), marks.MSG_WIZARD_COUNT_SHOWN.format(count=1))
        await self.select_under(heading=self.title(THE_GUITAR), label=FIRST_RIFF)
        for kind in choices.riff_kinds_used(FIRST_RIFF):
            self.assertIn(kind, self.wizard().field().value())


class TestWizardRiffAssign(CompositionTest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.riff = self.choices().add_riff(role=THE_GUITAR)
        await self.press(Key.DOWN, Key.UP)
        await self.open_panel(labels.MSG_WIZARD_RIFF_ASSIGN_BRANCH)

    async def test_each_player_lists_the_riffs_the_player_knows_with_who_each_was_written_for(self):
        await self.select_under(heading=self.title(THE_GUITAR), label=self.riff)
        self.assertEqual(self.wizard().field().value(), marks.MSG_WIZARD_RIFF_KNOWN_ROW.format(player=self.title(THE_GUITAR), used='').rstrip())
        bass = next(field for field in self.wizard().shown_fields() if field.label == self.title(THE_BASS))
        self.assertEqual(bass.value(), marks.MSG_WIZARD_COUNT_SHOWN.format(count=0))

    async def test_a_player_is_given_a_riff_of_another_from_a_list_and_a_player_who_knows_every_riff_is_refused(self):
        choices = self.choices()
        await self.select_field(self.title(THE_BASS))
        await self.press(keybindings.WizardPage.ADD)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(list(self.app.screen.options), [self.riff])
        await self.pick(self.riff)
        self.assertEqual(choices.riffs_known_by(THE_BASS), [self.riff])
        self.assertIn(messages.MSG_WIZARD_RIFF_GIVEN.format(player=self.title(THE_BASS), riff=self.riff), self.text())
        await self.press(keybindings.WizardPage.ADD)
        self.assertIsInstance(self.app.screen, WizardPage)
        self.assertEqual(choices.riffs_known_by(THE_BASS), [self.riff])

    async def test_bksp_takes_a_riff_from_a_player_asking_first_only_where_the_player_plays_it(self):
        choices = self.choices()
        choices.give_riff(role=THE_BASS, riff=self.riff)
        choices.set_section_part(kind=A_KIND, role=THE_GUITAR, part=self.riff)
        await self.press(keybindings.WizardPage.TO_TREE, keybindings.WizardPage.INTO_FIELDS)
        await self.select_under(heading=self.title(THE_BASS), label=self.riff)
        await self.press(keybindings.WizardPage.CLEAR)
        self.assertIsInstance(self.app.screen, WizardPage)
        self.assertEqual(choices.riffs_known_by(THE_BASS), [])
        await self.select_under(heading=self.title(THE_GUITAR), label=self.riff)
        await self.press(keybindings.WizardPage.CLEAR)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertEqual(choices.riffs_known_by(THE_GUITAR), [])
        self.assertEqual(choices.riff_names(), [self.riff])


class TestWizardSectionPlayers(CompositionTest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.riff = self.choices().add_riff(role=THE_GUITAR)
        await self.press(Key.DOWN, Key.UP)
        await self.open_panel(labels.MSG_WIZARD_SECTION_PLAYERS_BRANCH)

    async def test_a_heading_for_each_kind_of_section_holds_a_field_for_each_player_with_a_choice(self):
        choices = self.choices()
        kinds = [kind for kind in choices.section_player_kinds() if choices.section_players(kind)]
        headings = [field.label for field in self.wizard().shown_fields() if isinstance(field, Heading)]
        self.assertEqual(headings, [kind.capitalize() for kind in kinds])
        await self.open_heading(A_KIND.capitalize())
        for role in choices.section_players(A_KIND):
            self.assertIn(self.title(role), self.field_labels())

    async def test_a_player_is_given_a_riff_the_player_knows_and_the_heading_then_says_set(self):
        choices = self.choices()
        heading = A_KIND.capitalize()
        await self.select_under(heading=heading, label=self.title(THE_GUITAR))
        self.assertEqual(self.wizard().field().value(), ACCOMPANIMENT)
        await self.press(Key.ENTER)
        self.assertEqual(list(self.app.screen.options), choices.section_parts_offered(kind=A_KIND, role=THE_GUITAR))
        await self.pick(self.riff)
        self.assertEqual(choices.section_part(kind=A_KIND, role=THE_GUITAR), self.riff)
        self.assertEqual(choices.riff_kinds_used(self.riff), [A_KIND])
        shown = next(field for field in self.wizard().shown_fields() if field.label == heading)
        self.assertEqual(shown.value(), marks.MSG_SECTION_SET)
