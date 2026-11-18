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

"""The song wizard's Tunes panel: a tune for each kind of section, opened in the pattern editor on a draft of the set and kept as the person's own."""

from llamatron.composition.file_format import Row
from llamatron.macro_composer.arranger import NOBODY
from llamatron.macro_composer.riffs import FIRST_TAKE as FIRST_RIFF_TAKE
from llamatron.macro_composer.wizard_choices import FIRST_TUNE_TAKE, genre_title
from llamatron.strings import errors, labels, marks, messages
from llamatron.tui import keybindings
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.pattern.pattern_editor import PatternEditor
from llamatron.tui.screens.shared.field import Heading
from llamatron.tui.screens.wizard.wizard_page import WizardPage
from tests.support.ui_testing import fixed_text
from tests.tui.test_tui_wizard import WizardTest

A_GENRE = 'rock'
A_SUBGENRE = 'folk rock'
A_KIND = 'verse'
ANOTHER_GENRE = 'blues'
# The degree a test writes on a tune's first step, and another for a second edit.
A_DEGREE = 7
# How the row shows the take after the first.
SECOND_TAKE_SHOWN = 2
# The attribute a field keeps its label in.
LABEL = 'label'


class TunesPanelTest(WizardTest):
    """The wizard opened on the Tunes and Riffs panel of a song, with what its tests share."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        choices = self.choices()
        choices.set_genre(A_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        await self.press(Key.DOWN, Key.UP)
        await self.go_to_named_branch(labels.MSG_WIZARD_TUNES_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)

    def heading(self, *, kind=A_KIND):
        return labels.MSG_WIZARD_KIND_HEADING.format(kind=kind)

    async def select_in_kind(self, *, label, kind=A_KIND):
        """Move the cursor to a field of a kind of section's part of the panel, opening the kind's heading first where it is closed."""
        await self.select_field(self.heading(kind=kind))
        page = self.wizard()
        if not page.is_open(page.field()):
            await self.press(keybindings.FieldPage.TOGGLE)
        for _ in self.labels_under(kind=kind):
            if page.label_under_cursor() != label:
                await self.press(Key.DOWN)
        self.assertEqual(page.label_under_cursor(), label)
        self.assertEqual(page.heading_over_cursor(), self.heading(kind=kind))

    def labels_under(self, *, kind=A_KIND):
        """Return the labels of the fields that show under a kind of section's heading."""
        fields = self.wizard().shown_fields()
        start = [getattr(field, LABEL, None) for field in fields].index(self.heading(kind=kind)) + 1
        under = []
        for field in fields[start:]:
            if isinstance(field, Heading):
                break
            under.append(field.label)
        return under

    def tune_labels_under(self, *, kind=A_KIND):
        """Return the labels under a kind of section's heading that are the tune's: its row and who plays it."""
        return [label for label in self.labels_under(kind=kind) if label in (labels.MSG_WIZARD_TUNE_ROW_LABEL, labels.MSG_WIZARD_PLAYED_BY_LABEL)]

    async def open_tune(self):
        await self.select_in_kind(label=labels.MSG_WIZARD_TUNE_ROW_LABEL)
        await self.press(Key.ENTER)

    def change_first_step(self):
        """Write another degree on the first step of the pattern the editor shows, as a key in the editor would."""
        editor = self.app.screen
        editor.document().set_step_value(name=editor.item, row=Row.DEGREE, step=0, value=A_DEGREE)


class TestWizardTunes(TunesPanelTest):

    async def test_the_panel_has_a_heading_for_each_kind_of_section_with_a_tune_closed_until_opened_with_its_tune_inside(self):
        choices = self.choices()
        headings = [field.label for field in self.wizard().shown_fields() if isinstance(field, Heading)]
        for kind in choices.tune_kinds():
            self.assertIn(self.heading(kind=kind), headings)
        for kind in choices.tune_kinds():
            self.assertNotIn(choices.tune_pattern_name(kind), self.text())
            await self.select_in_kind(label=labels.MSG_WIZARD_TUNE_ROW_LABEL, kind=kind)
            self.assertIn(choices.tune_pattern_name(kind), self.text())
            self.assertEqual(self.tune_labels_under(kind=kind), [labels.MSG_WIZARD_TUNE_ROW_LABEL, labels.MSG_WIZARD_PLAYED_BY_LABEL])
        shown = self.text()
        self.assertNotIn(marks.MSG_WIZARD_TUNE_EDITED.format(name=self.choices().tune_pattern_name(A_KIND)), shown)

    async def test_enter_opens_the_pattern_editor_on_a_draft_and_esc_unchanged_keeps_nothing(self):
        real = self.app.get_document()
        await self.open_tune()
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertTrue(self.app.is_drafting())
        self.assertIsNot(self.app.get_document(), real)
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, WizardPage)
        self.assertFalse(self.app.is_drafting())
        self.assertIs(self.app.get_document(), real)
        self.assertFalse(self.choices().tune_is_own(A_KIND))
        self.assertIn(messages.MSG_WIZARD_TUNE_UNCHANGED.format(kind=A_KIND), self.text())

    async def test_notes_changed_in_the_editor_are_kept_as_the_kinds_own_and_every_section_of_the_kind_plays_them(self):
        await self.open_tune()
        self.change_first_step()
        await self.press(Key.ESCAPE)
        choices = self.choices()
        self.assertTrue(choices.tune_is_own(A_KIND))
        self.assertEqual(choices.tune_pattern(A_KIND)[Row.DEGREE][0], A_DEGREE)
        self.assertIn(marks.MSG_WIZARD_TUNE_EDITED.format(name=choices.tune_pattern_name(A_KIND)), self.text())
        setlist, name = choices.made_for_listening()
        player = choices.tune_player()
        played = [scene.get_clip_slot(player).get_pattern_name() for place, scene in enumerate(setlist.get_song(name).get_scenes())
                  if choices.section_kind(place) == A_KIND and scene.has_clip_slot(player)]
        self.assertGreater(len(played), 1)
        self.assertEqual(set(played), {choices.tune_pattern_name(A_KIND)})
        self.assertTrue(self.wizard().has_choices_to_lose())

    async def test_an_edited_tune_is_not_written_over_by_another_choice_or_another_genre(self):
        await self.open_tune()
        self.change_first_step()
        await self.press(Key.ESCAPE)
        choices = self.choices()
        kept = choices.tune_pattern(A_KIND)
        choices.draw_seed()
        self.assertEqual(choices.tune_pattern(A_KIND), kept)
        choices.set_genre(ANOTHER_GENRE)
        choices.set_genre(A_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        self.assertEqual(choices.tune_pattern(A_KIND), kept)

    async def test_bksp_gives_an_edited_tune_back_to_the_wizard_after_asking_and_no_starts_selected(self):
        await self.open_tune()
        self.change_first_step()
        await self.press(Key.ESCAPE)
        await self.select_in_kind(label=labels.MSG_WIZARD_TUNE_ROW_LABEL)
        await self.press(keybindings.WizardPage.CLEAR)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(Key.ENTER)
        self.assertTrue(self.choices().tune_is_own(A_KIND))
        await self.press(keybindings.WizardPage.CLEAR, keybindings.ConfirmDialog.YES)
        self.assertFalse(self.choices().tune_is_own(A_KIND))

    async def test_t_writes_a_new_take_of_the_tune_under_the_cursor_alone_and_the_row_says_which_take(self):
        choices = self.choices()
        other = next(kind for kind in choices.tune_kinds() if kind != A_KIND)
        first = choices.tune_pattern(A_KIND)
        others = choices.tune_pattern(other)
        await self.select_in_kind(label=labels.MSG_WIZARD_TUNE_ROW_LABEL)
        await self.press(keybindings.WizardPage.NEW_TAKE)
        self.assertEqual(choices.tune_take(A_KIND), FIRST_TUNE_TAKE + 1)
        self.assertNotEqual(choices.tune_pattern(A_KIND)[Row.DEGREE], first[Row.DEGREE])
        self.assertEqual(choices.tune_pattern(other), others)
        self.assertIn(marks.MSG_WIZARD_TUNE_TAKE_SHOWN.format(name=choices.tune_pattern_name(A_KIND), take=SECOND_TAKE_SHOWN), self.text())
        self.assertTrue(self.wizard().has_choices_to_lose())

    async def test_a_new_take_of_an_edited_tune_asks_first_and_no_keeps_the_notes(self):
        await self.open_tune()
        self.change_first_step()
        await self.press(Key.ESCAPE)
        await self.select_in_kind(label=labels.MSG_WIZARD_TUNE_ROW_LABEL)
        await self.press(keybindings.WizardPage.NEW_TAKE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(Key.ENTER)
        self.assertTrue(self.choices().tune_is_own(A_KIND))
        await self.press(keybindings.WizardPage.NEW_TAKE, keybindings.ConfirmDialog.YES)
        self.assertFalse(self.choices().tune_is_own(A_KIND))
        self.assertEqual(self.choices().tune_take(A_KIND), FIRST_TUNE_TAKE + 1)

    async def test_tune_played_by_gives_the_songs_tune_to_another_player_and_each_kind_goes_by_the_song(self):
        choices = self.choices()
        usual = choices.tune_played_by()
        other = next(role for role in choices.tune_players_offered() if role != usual)
        await self.select_in_kind(label=labels.MSG_WIZARD_PLAYED_BY_LABEL)
        self.assertIn(marks.MSG_WIZARD_FROM_SONG_SHOWN.format(value=choices.role_title(usual)), self.text())
        await self.select_field(labels.MSG_WIZARD_TUNE_LABEL)
        await self.press(Key.ENTER)
        await self.type(choices.role_title(other))
        await self.press(Key.ENTER)
        self.assertEqual(choices.tune_played_by(), other)
        self.assertEqual(choices.tune_player_in(A_KIND), other)
        self.assertIn(marks.MSG_WIZARD_FROM_SONG_SHOWN.format(value=choices.role_title(other)), self.text())

    async def test_a_kinds_played_by_takes_a_player_of_its_own_or_nobody_which_hides_the_kinds_tune(self):
        choices = self.choices()
        other_kind = next(kind for kind in choices.tune_kinds() if kind != A_KIND)
        await self.select_in_kind(label=labels.MSG_WIZARD_PLAYED_BY_LABEL, kind=other_kind)
        await self.select_in_kind(label=labels.MSG_WIZARD_PLAYED_BY_LABEL)
        await self.press(Key.ENTER)
        await self.type(labels.MSG_WIZARD_NOBODY)
        await self.press(Key.ENTER)
        self.assertEqual(choices.tune_played_by_in(A_KIND), NOBODY)
        self.assertIsNone(choices.tune_player_in(A_KIND))
        self.assertEqual(self.tune_labels_under(), [labels.MSG_WIZARD_PLAYED_BY_LABEL])
        self.assertEqual(self.tune_labels_under(kind=other_kind), [labels.MSG_WIZARD_TUNE_ROW_LABEL, labels.MSG_WIZARD_PLAYED_BY_LABEL])
        # The cursor stays on the field that was changed, whose heading now says something inside was chosen.
        self.assertEqual(self.wizard().label_under_cursor(), labels.MSG_WIZARD_PLAYED_BY_LABEL)
        self.assertEqual(self.wizard().heading_over_cursor(), self.heading())

    async def test_the_set_cannot_be_saved_opened_or_exported_while_a_tune_is_edited(self):
        await self.open_tune()
        for binding in (keybindings.Page.SAVE, keybindings.Page.OPEN_SET, keybindings.Page.EXPORT, keybindings.Page.WIZARD):
            await self.press(binding)
            self.assertIsInstance(self.app.screen, PatternEditor)
            self.assertIn(errors.ERR_NOT_WHILE_DRAFTING, self.text())


class TestWizardRiffs(TunesPanelTest):

    async def add_riff(self, *, kind=A_KIND):
        """Add a new riff to a kind of section for the first player the picker offers, and return the riff's name."""
        before = self.choices().added_riffs()
        await self.select_in_kind(label=labels.MSG_WIZARD_ADD_RIFF_LABEL, kind=kind)
        await self.press(Key.ENTER)
        # The picker first asks which riff, a new one its first choice, and then who plays.
        self.assertIn(labels.MSG_WIZARD_NEW_RIFF, self.text())
        await self.press(Key.ENTER, Key.ENTER)
        return next(riff for riff in self.choices().added_riffs() if riff not in before)

    async def test_every_kind_of_the_form_has_a_heading_and_a_kind_with_no_tune_holds_add_riff_alone(self):
        choices = self.choices()
        headings = [field.label for field in self.wizard().shown_fields() if isinstance(field, Heading)]
        self.assertEqual(headings, [self.heading(kind=kind) for kind in choices.riff_kinds_offered()])
        no_tune = next(kind for kind in choices.riff_kinds_offered() if kind not in choices.tune_kinds())
        await self.select_in_kind(label=labels.MSG_WIZARD_ADD_RIFF_LABEL, kind=no_tune)
        self.assertEqual(self.labels_under(kind=no_tune), [labels.MSG_WIZARD_ADD_RIFF_LABEL])

    async def test_add_riff_asks_who_plays_and_the_riff_has_a_row_of_its_name_and_its_players(self):
        choices = self.choices()
        offered = choices.riff_players_free(A_KIND)
        await self.select_in_kind(label=labels.MSG_WIZARD_ADD_RIFF_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        for said in (labels.MSG_WIZARD_NEW_RIFF, labels.MSG_WIZARD_BLANK_RIFF):
            self.assertIn(said, self.text())
        await self.press(Key.ENTER)
        for role in offered:
            self.assertIn(choices.role_title(role), self.text())
        await self.press(Key.ENTER)
        riff = choices.added_riffs()[0]
        self.assertEqual(choices.riff_players_of(riff), offered[:1])
        self.assertEqual(self.labels_under()[-2:] if len(offered) > 1 else self.labels_under()[-1:], [riff, labels.MSG_WIZARD_ADD_RIFF_LABEL][:2 if len(offered) > 1 else 1])
        self.assertIn(choices.role_title(offered[0]), self.text())
        self.assertIn(messages.MSG_WIZARD_RIFF_ADDED.format(riff=riff, kind=A_KIND), self.text())
        self.assertTrue(self.wizard().has_choices_to_lose())

    async def test_a_riff_of_the_song_is_offered_again_in_another_kind_under_new_riff(self):
        choices = self.choices()
        riff = await self.add_riff()
        other_kind = next(kind for kind in choices.tune_kinds() if kind != A_KIND)
        await self.select_in_kind(label=labels.MSG_WIZARD_ADD_RIFF_LABEL, kind=other_kind)
        await self.press(Key.ENTER)
        self.assertIn(labels.MSG_WIZARD_NEW_RIFF, self.text())
        await self.type(riff)
        await self.press(Key.ENTER)
        self.assertEqual(choices.riff_kinds_of(riff), [A_KIND, other_kind])
        self.assertIn(riff, self.labels_under(kind=other_kind))

    async def test_t_on_a_riff_writes_a_new_take_of_the_riff_and_bksp_removes_it_after_asking(self):
        choices = self.choices()
        riff = await self.add_riff()
        await self.select_in_kind(label=riff)
        await self.press(keybindings.WizardPage.NEW_TAKE)
        self.assertEqual(choices.riff_take_of(riff), FIRST_RIFF_TAKE + 1)
        self.assertIn(messages.MSG_WIZARD_RIFF_TAKEN.format(take=SECOND_TAKE_SHOWN, riff=riff), self.text())
        await self.press(keybindings.FieldPage.CLEAR)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.NO)
        self.assertEqual(choices.riffs_in(A_KIND), [riff])
        await self.press(keybindings.FieldPage.CLEAR, keybindings.ConfirmDialog.YES)
        self.assertEqual(choices.added_riffs(), [])
        self.assertNotIn(riff, self.labels_under())

    async def test_a_second_riff_in_a_kind_is_for_the_players_still_free_and_add_riff_leaves_when_none_is(self):
        choices = self.choices()
        free = list(choices.riff_players_free(A_KIND))
        riffs = [await self.add_riff() for _ in free]
        self.assertEqual([choices.riff_players_of(riff) for riff in riffs], [[role] for role in free])
        self.assertEqual(choices.riff_players_free(A_KIND), [])
        self.assertNotIn(labels.MSG_WIZARD_ADD_RIFF_LABEL, self.labels_under())

    async def test_enter_on_a_riff_edits_its_notes_which_are_kept_as_the_riffs_own_and_a_new_take_then_asks(self):
        choices = self.choices()
        riff = await self.add_riff()
        await self.select_in_kind(label=riff)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertEqual(self.app.screen.item, choices.riff_pattern_name(riff))
        await self.press(Key.ESCAPE)
        self.assertFalse(choices.added_riff_is_own(riff))
        self.assertIn(messages.MSG_WIZARD_RIFF_UNCHANGED.format(riff=riff), self.text())
        await self.press(Key.ENTER)
        self.change_first_step()
        await self.press(Key.ESCAPE)
        self.assertTrue(choices.added_riff_is_own(riff))
        self.assertEqual(choices.riff_pattern(riff)[Row.DEGREE][0], A_DEGREE)
        self.assertIn(messages.MSG_WIZARD_RIFF_KEPT.format(riff=riff), self.text())
        await self.press(keybindings.WizardPage.NEW_TAKE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(Key.ENTER)
        self.assertTrue(choices.added_riff_is_own(riff))
        await self.press(keybindings.WizardPage.NEW_TAKE, keybindings.ConfirmDialog.YES)
        self.assertFalse(choices.added_riff_is_own(riff))

    async def test_a_blank_riff_opens_in_the_pattern_editor_with_no_note_and_is_the_persons_own(self):
        choices = self.choices()
        await self.select_in_kind(label=labels.MSG_WIZARD_ADD_RIFF_LABEL)
        await self.press(Key.ENTER)
        await self.type(labels.MSG_WIZARD_BLANK_RIFF)
        await self.press(Key.ENTER, Key.ENTER)
        self.assertIsInstance(self.app.screen, PatternEditor)
        riff = choices.added_riffs()[0]
        self.assertTrue(choices.added_riff_is_own(riff))
        self.assertNotIn(Row.DEGREE, choices.riff_pattern(riff))
        self.change_first_step()
        await self.press(Key.ESCAPE)
        self.assertEqual(choices.riff_pattern(riff)[Row.DEGREE][0], A_DEGREE)


class TestWizardChangeGenre(WizardTest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        choices = self.choices()
        choices.set_genre(A_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        await self.press(Key.DOWN, Key.UP)
        await self.go_to_named_branch(labels.MSG_WIZARD_GENRE_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels.MSG_GENRE_LABEL)

    async def choose_another_genre(self):
        await self.press(Key.ENTER)
        await self.type(genre_title(ANOTHER_GENRE))
        await self.press(Key.ENTER)

    async def test_another_genre_is_taken_at_once_while_nothing_was_changed_by_hand(self):
        await self.choose_another_genre()
        self.assertIsInstance(self.app.screen, WizardPage)
        self.assertEqual(self.choices().get_genre(), ANOTHER_GENRE)

    async def test_another_genre_asks_first_counting_what_is_lost_and_kept_and_enter_alone_keeps_the_genre(self):
        choices = self.choices()
        choices.new_tune_take(A_KIND)
        other_kind = next(kind for kind in choices.tune_kinds() if kind != A_KIND)
        choices.set_tune_pattern(kind=other_kind, pattern=choices.tune_pattern(other_kind))
        await self.choose_another_genre()
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        shown = self.text()
        for said in (messages.MSG_CHANGE_GENRE_TITLE, messages.MSG_CHANGE_GENRE_LOST, messages.MSG_CHANGE_GENRE_KEPT, messages.MSG_CHANGE_GENRE_TUNE_TAKES.format(count=1),
                     messages.MSG_CHANGE_GENRE_OWN_TUNES.format(count=1)):
            self.assertIn(said, shown)
        for unsaid in (fixed_text(messages.MSG_CHANGE_GENRE_BAND_SETTINGS), messages.MSG_CHANGE_GENRE_FORM, choices.tune_pattern_name(other_kind)):
            self.assertNotIn(unsaid, shown)
        await self.press(Key.ENTER)
        self.assertEqual(choices.get_genre(), A_GENRE)
        self.assertEqual(choices.tune_take(A_KIND), FIRST_TUNE_TAKE + 1)

    async def test_yes_takes_the_genre_gives_up_what_was_counted_lost_and_keeps_the_edited_tunes(self):
        choices = self.choices()
        choices.new_tune_take(A_KIND)
        other_kind = next(kind for kind in choices.tune_kinds() if kind != A_KIND)
        choices.set_tune_pattern(kind=other_kind, pattern=choices.tune_pattern(other_kind))
        await self.choose_another_genre()
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertEqual(choices.get_genre(), ANOTHER_GENRE)
        self.assertEqual(choices.tune_take(A_KIND), FIRST_TUNE_TAKE)
        choices.set_genre(A_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        self.assertTrue(choices.tune_is_own(other_kind))
