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
from llamatron.macro_composer import hook_writing
from llamatron.macro_composer.melody import HEIGHT, HIGH, LAST_LINE, LOW, PLACEMENTS, REPEATS, REPEATS_A_LOT
from llamatron.macro_composer.riffs import ACCENT_CHORDS, RIFF_BARS, RIFF_BETWEEN, RIFF_NOTES, RIFF_WITH_CHORDS, STAYS_HOME
from llamatron.macro_composer.wizard_choices import ACCOMPANIMENT, MELODY_BUSY, MELODY_RANGE, MELODY_SPARSE, MELODY_WAYS, MELODY_WIDE, SMOOTH
from llamatron.strings import labels, marks, messages, names
from llamatron.tui import keybindings
from llamatron.tui.components.button_row import ROW_LINES
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.dialogs.new_riff_dialog import NewRiffDialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.drawing import NOTHING, SELECTED_MARK, Style
from llamatron.tui.keys import Key
from llamatron.tui.screens.pattern.pattern_editor import PatternEditor
from llamatron.tui.screens.shared.field import Heading
from llamatron.tui.screens.wizard.intro_melody_branch import INTRO_MELODY_KEY
from llamatron.macro_composer.wizard_choices import FIRST_TUNE_TAKE
from llamatron.tui.screens.wizard.section_melody_branch import MELODY_KEY
from llamatron.tui.screens.wizard.solo_melody_branch import FIRST_SOLO, SOLO_MELODY_KEY
from llamatron.tui.screens.wizard.wizard_page import WizardPage
from tests.support.ui_testing import key_of
from tests.tui.test_tui_wizard import WizardTest

A_GENRE = 'rock'
A_SUBGENRE = 'folk rock'
A_RIFF_SUBGENRE = 'hard rock'
A_SUBGENRE_WITH_A_PRE_CHORUS = 'arena rock'
A_KIND = 'verse'
# The room at the right of the tree on a wide console and on a narrow one, in cells.
A_WIDE_ROOM = 80
A_NARROW_ROOM = 30
THE_GUITAR = 'guitar'
THE_BASS = 'bass'
A_DEGREE = 7
A_COLUMN_GAP = '  '
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
            usual = choices.genre_melody_way(field)
            self.assertEqual(list(self.app.screen.options), [labels.MSG_WIZARD_VALUE_FROM.format(value=way, origin=labels.MSG_WIZARD_USUAL_MELODY) if way == usual else way for way in MELODY_WAYS[field]])
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
        # One list holds every value, the song's own said to be so, and picking the song's own gives the field back.
        usual = labels.MSG_WIZARD_VALUE_FROM.format(value=choices.get_melody_way(MELODY_BUSY), origin=labels.MSG_WIZARD_FROM_SONG)
        self.assertIn(usual, self.app.screen.options)
        self.assertNotIn(labels.MSG_WIZARD_FROM_SONG, self.app.screen.options)
        await self.pick(usual)
        self.assertIsNone(choices.get_section_melody(kind=A_KIND, field=MELODY_BUSY))

    async def test_the_notes_open_in_the_pattern_editor_are_kept_when_edited_and_given_back_with_bksp(self):
        choices = self.choices()
        await self.select_field(labels.MSG_WIZARD_EDIT_NOTES_BUTTON)
        self.assertIn(messages.MSG_WIZARD_HOOK_MADE, self.text())
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.change_first_step()
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, WizardPage)
        self.assertTrue(choices.tune_is_own(A_KIND))
        self.assertIn(messages.MSG_WIZARD_NOTES_BY_HAND, self.text())
        self.assertEqual(self.wizard().field().label, labels.MSG_WIZARD_EDIT_NOTES_BUTTON)
        await self.press(keybindings.WizardPage.CLEAR)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertFalse(choices.tune_is_own(A_KIND))

    async def test_regenerate_asks_first_starting_on_no_and_writes_another_melody_with_nothing_kept(self):
        choices = self.choices()
        first = choices.tune_pattern(A_KIND)
        await self.select_field(labels.MSG_WIZARD_REGENERATE_BUTTON)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        name = messages.MSG_WIZARD_MELODY_OF.format(kind=A_KIND)
        self.assertEqual(self.app.screen.title, messages.MSG_WIZARD_REGENERATE_TITLE.format(name=name))
        await self.press(Key.ENTER)
        self.assertEqual(choices.tune_pattern(A_KIND), first)
        await self.select_field(labels.MSG_WIZARD_REGENERATE_BUTTON)
        await self.press(Key.ENTER, keybindings.ConfirmDialog.YES)
        self.assertNotEqual(choices.tune_pattern(A_KIND), first)
        self.assertIn(messages.MSG_WIZARD_REGENERATED.format(name=name), self.text())

    async def test_the_panel_has_four_buttons_edit_first_with_no_key_of_their_own_and_listen_names_the_melody(self):
        buttons = [labels.MSG_WIZARD_EDIT_NOTES_BUTTON, labels.MSG_WIZARD_REGENERATE_BUTTON, labels.MSG_WIZARD_LISTEN_BUTTON, labels.MSG_WIZARD_LISTEN_BAND_BUTTON]
        self.assertEqual(self.field_labels()[-len(buttons):], buttons)
        self.assertEqual([field.key_name for field in self.wizard().shown_fields()[-len(buttons):]], [NOTHING] * len(buttons))
        self.assertIsNone(self.wizard().branch().heard_with_band()[2])

    async def test_buttons_too_wide_for_a_row_stand_one_under_another_and_up_and_down_go_through_them(self):
        wizard = self.wizard()
        buttons = [labels.MSG_WIZARD_EDIT_NOTES_BUTTON, labels.MSG_WIZARD_REGENERATE_BUTTON, labels.MSG_WIZARD_LISTEN_BUTTON, labels.MSG_WIZARD_LISTEN_BAND_BUTTON]
        fields = wizard.shown_fields()[-len(buttons):]
        self.assertEqual(len(wizard.row_of_buttons(buttons=fields, selected=0, width=A_WIDE_ROOM)), ROW_LINES)
        self.assertFalse(wizard.buttons_stacked())
        lines = wizard.row_of_buttons(buttons=fields, selected=1, width=A_NARROW_ROOM)
        self.assertEqual([line.plain.strip() for line in lines],
                         [marks.MSG_STACKED_BUTTON.format(name=name) if place != 1 else SELECTED_MARK + marks.MSG_STACKED_BUTTON.format(name=name) for place, name in enumerate(buttons)])
        self.assertTrue(wizard.buttons_stacked())
        await self.select_field(buttons[0])
        wizard.stacked_buttons = True
        wizard.move_cursor(Key.DOWN)
        self.assertEqual(wizard.field().label, buttons[1])
        wizard.move_cursor(Key.DOWN)
        wizard.move_cursor(Key.DOWN)
        wizard.move_cursor(Key.DOWN)
        self.assertEqual(wizard.field().label, buttons[-1])
        wizard.move_cursor(Key.UP)
        self.assertEqual(wizard.field().label, buttons[-2])
        what, place, track = self.wizard().branch().listens()
        self.assertEqual(what, messages.MSG_WIZARD_MELODY_OF.format(kind=A_KIND))
        self.assertEqual((place, track), (self.choices().tune_place(A_KIND), self.choices().tune_player_in(A_KIND)))

    async def test_the_chorus_with_the_hook_shows_where_the_hook_sits_and_the_gauges_of_its_other_lines(self):
        choices = self.choices()
        kind, _ = choices.hook_line_place()
        await self.press(keybindings.WizardPage.TO_TREE)
        await self.open_panel(MELODY_KEY.format(kind=kind))
        self.assertTrue(choices.is_body_of_hook(kind))
        for label in (labels.MSG_WIZARD_PLACEMENT_LABEL, *(labels.MSG_WIZARD_BODY_GAUGE_LABELS[name] for name in choices.body_gauges()), labels.MSG_WIZARD_HOOK_HEADING,
                      labels.MSG_WIZARD_BEHAVIOR_LABEL, *(labels.MSG_WIZARD_HOOK_GAUGE_LABELS[name] for name in choices.hook_gauges())):
            self.assertIn(label, self.field_labels())
        # Height there is the hook's gauge, never the melody's own field of how high the melody sits.
        self.assertEqual(self.field_labels().count(labels.MSG_WIZARD_HEIGHT_LABEL), 1)
        self.assertNotIn(labels.MSG_WIZARD_SECTION_BUSY_LABEL, self.field_labels())
        self.assertFalse(choices.is_body_of_hook(A_KIND))

    async def test_placement_lists_every_place_with_the_genres_said_to_be_so_and_moves_the_hook_line(self):
        choices = self.choices()
        kind, _ = choices.hook_line_place()
        await self.press(keybindings.WizardPage.TO_TREE)
        await self.open_panel(MELODY_KEY.format(kind=kind))
        usual = labels.MSG_WIZARD_VALUE_FROM.format(value=choices.genre_hook_placement(), origin=labels.MSG_WIZARD_USUAL_MELODY)
        await self.select_field(labels.MSG_WIZARD_PLACEMENT_LABEL)
        self.assertEqual(self.wizard().field().value(), usual)
        await self.press(Key.ENTER)
        self.assertEqual(list(self.app.screen.options), [usual if place == choices.genre_hook_placement() else place for place in PLACEMENTS])
        await self.pick(LAST_LINE)
        self.assertEqual(choices.get_hook_placement(), LAST_LINE)
        self.assertEqual(choices.hook_line_place()[1], len(PLACEMENTS) + 1)
        await self.press(Key.ENTER)
        await self.pick(usual)
        self.assertEqual(choices.get_hook_placement(), choices.genre_hook_placement())

    async def test_a_gauge_of_the_chorus_s_other_lines_steps_and_the_delete_key_gives_the_genre_s_back(self):
        choices = self.choices()
        kind, _ = choices.hook_line_place()
        await self.press(keybindings.WizardPage.TO_TREE)
        await self.open_panel(MELODY_KEY.format(kind=kind))
        usual = choices.genre_body_gauge(hook_writing.SPACE)
        await self.select_field(labels.MSG_WIZARD_BODY_GAUGE_LABELS[hook_writing.SPACE])
        self.assertIn(labels.MSG_WIZARD_VALUE_FROM.format(value=usual, origin=labels.MSG_WIZARD_USUAL_MELODY), self.wizard().field().value())
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(choices.get_body_gauge(hook_writing.SPACE), usual + 1)
        self.assertTrue(choices.writing_gauge_is_moved(part=hook_writing.BODY_WRITING, name=hook_writing.SPACE))
        await self.press(keybindings.FieldPage.CLEAR)
        self.assertFalse(choices.writing_gauge_is_moved(part=hook_writing.BODY_WRITING, name=hook_writing.SPACE))

    async def test_no_panel_of_a_kinds_melody_holds_the_hook(self):
        kind, _ = self.choices().hook_line_place()
        await self.press(keybindings.WizardPage.TO_TREE)
        await self.open_panel(MELODY_KEY.format(kind=kind))
        self.assertNotIn(labels.MSG_WIZARD_INTRO_HOOK_LABEL, self.field_labels())
        self.assertNotIn(marks.MSG_WIZARD_HOOK_CELL, self.text())


class TestWizardIntroMelody(CompositionTest):
    """The Intro panel, last under Melodies: who says the hook in the intro, and that player's notes."""

    SUBGENRE = A_SUBGENRE_WITH_A_PRE_CHORUS

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_panel(INTRO_MELODY_KEY)

    async def choose_first_player(self):
        choices = self.choices()
        await self.select_field(labels.MSG_WIZARD_INTRO_HOOK_LABEL)
        await self.press(Key.ENTER)
        await self.pick(choices.role_title(choices.intro_hook_players()[0]))

    async def test_the_panel_has_only_who_says_the_hook_until_somebody_is_chosen_and_then_its_buttons(self):
        choices = self.choices()
        self.assertEqual(self.field_labels(), [labels.MSG_WIZARD_INTRO_HOOK_LABEL])
        self.assertEqual(self.wizard().field().value(), labels.MSG_WIZARD_NOBODY)
        await self.press(Key.ENTER)
        self.assertEqual(list(self.app.screen.options), [labels.MSG_WIZARD_NOBODY, *(choices.role_title(role) for role in choices.intro_hook_players())])
        await self.pick(choices.role_title(choices.intro_hook_players()[0]))
        self.assertEqual(choices.get_intro_hook(), choices.intro_hook_players()[0])
        self.assertEqual(self.field_labels(), [labels.MSG_WIZARD_INTRO_HOOK_LABEL, labels.MSG_WIZARD_EDIT_NOTES_BUTTON, labels.MSG_WIZARD_LISTEN_BUTTON, labels.MSG_WIZARD_LISTEN_BAND_BUTTON])
        self.assertIn(messages.MSG_WIZARD_HOOK_MADE, self.text())
        what, place, track = self.wizard().branch().listens()
        self.assertEqual((place, track), (choices.intro_melody_place(), choices.get_intro_hook()))
        self.assertIsNone(self.wizard().branch().heard_with_band()[2])

    async def test_the_intros_notes_open_in_the_pattern_editor_are_kept_when_edited_and_given_back_with_bksp(self):
        choices = self.choices()
        await self.choose_first_player()
        await self.select_field(labels.MSG_WIZARD_EDIT_NOTES_BUTTON)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.change_first_step()
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, WizardPage)
        self.assertTrue(choices.intro_is_own())
        self.assertIn(messages.MSG_WIZARD_NOTES_BY_HAND, self.text())
        await self.press(keybindings.WizardPage.CLEAR)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertFalse(choices.intro_is_own())

    async def test_the_hook_panel_no_longer_holds_who_says_the_hook_in_the_intro(self):
        await self.press(keybindings.WizardPage.TO_TREE)
        await self.open_panel(labels.MSG_WIZARD_HOOKS_BRANCH)
        self.assertNotIn(labels.MSG_WIZARD_INTRO_HOOK_LABEL, self.field_labels())


class TestWizardSoloMelody(CompositionTest):
    """A solo's panel under Melodies: the solo's notes, to edit by hand and to hear."""

    SUBGENRE = A_SUBGENRE_WITH_A_PRE_CHORUS

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_panel(SOLO_MELODY_KEY.format(number=FIRST_SOLO))

    async def test_the_panel_says_who_plays_the_solo_and_in_which_section_and_has_its_buttons_edit_first(self):
        choices = self.choices()
        place = choices.solo_places()[0]
        self.assertEqual(self.field_labels(), [labels.MSG_WIZARD_SOLO_PLAYED_BY_LABEL, labels.MSG_WIZARD_SOLO_SECTION_LABEL, labels.MSG_WIZARD_EDIT_NOTES_BUTTON, labels.MSG_WIZARD_REGENERATE_BUTTON,
                                               labels.MSG_WIZARD_LISTEN_BUTTON,
                                               labels.MSG_WIZARD_LISTEN_BAND_BUTTON])
        shown = self.text()
        self.assertIn(choices.role_title(choices.solo_player()), shown)
        self.assertIn(messages.MSG_WIZARD_HOOK_MADE, shown)
        what, heard_at, track = self.wizard().branch().listens()
        self.assertEqual((heard_at, track), (place, choices.solo_player()))
        self.assertEqual(self.wizard().branch().heard_with_band()[1:], (place, None))

    async def test_the_solos_notes_open_in_the_pattern_editor_are_kept_when_edited_and_given_back_with_bksp(self):
        choices = self.choices()
        place = choices.solo_places()[0]
        await self.select_field(labels.MSG_WIZARD_EDIT_NOTES_BUTTON)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.change_first_step()
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, WizardPage)
        self.assertTrue(choices.solo_is_own(place))
        self.assertIn(messages.MSG_WIZARD_NOTES_BY_HAND, self.text())
        await self.press(keybindings.WizardPage.CLEAR)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertFalse(choices.solo_is_own(place))


    async def test_regenerate_asks_and_writes_another_solo_and_gives_up_notes_edited_by_hand(self):
        choices = self.choices()
        place = choices.solo_places()[0]
        written = choices.solo_pattern(place)
        self.assertTrue(self.wizard().branch().listens_alone())
        await self.select_field(labels.MSG_WIZARD_REGENERATE_BUTTON)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.NO)
        self.assertEqual(choices.solo_pattern(place), written)
        await self.press(Key.ENTER, keybindings.ConfirmDialog.YES)
        self.assertNotEqual(choices.solo_pattern(place), written)
        self.assertFalse(choices.solo_is_own(place))
        self.assertEqual(choices.solo_take(place), FIRST_TUNE_TAKE + 1)


class TestWizardHooks(CompositionTest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.choices().set_subgenre(A_SUBGENRE_WITH_A_PRE_CHORUS)
        await self.press(Key.DOWN, Key.UP)
        await self.open_panel(labels.MSG_WIZARD_HOOKS_BRANCH)

    async def test_the_panel_shows_both_headings_open_where_the_hook_is_sung_how_it_is_written_and_its_picture(self):
        choices = self.choices()
        edit = labels.MSG_WIZARD_EDIT_KIND_NOTES_BUTTON.format(kind=choices.hook_kind().capitalize())
        for label in (labels.MSG_WIZARD_MAIN_HOOK_HEADING, labels.MSG_WIZARD_SUNG_IN_LABEL, labels.MSG_WIZARD_HOOK_BARS_LABEL, labels.MSG_WIZARD_SECOND_HOOK_HEADING, labels.MSG_WIZARD_SECOND_HOOK_LABEL,
                      edit, labels.MSG_WIZARD_REGENERATE_BUTTON, labels.MSG_WIZARD_LISTEN_BUTTON):
            self.assertIn(label, self.field_labels())
        # How the hook is written is said on the panel of the section that says the hook.
        for label in (labels.MSG_WIZARD_BEHAVIOR_LABEL, *(labels.MSG_WIZARD_HOOK_GAUGE_LABELS[name] for name in choices.hook_gauges())):
            self.assertNotIn(label, self.field_labels())
        first, last = choices.hook_bars()
        await self.select_field(labels.MSG_WIZARD_HOOK_BARS_LABEL)
        self.assertEqual(self.wizard().field().value(), labels.MSG_WIZARD_HOOK_BARS.format(first=first, last=last))
        shown = self.text()
        self.assertIn(marks.MSG_WIZARD_HOOK_FRAME_NAME, shown)
        self.assertIn(messages.MSG_WIZARD_HOOK_IS_BARS.format(first=first, last=last, kind=choices.hook_kind()), shown)

    async def test_listen_plays_whoever_plays_the_melody_in_the_hooks_section_and_never_a_player_with_no_clip_there(self):
        choices = self.choices()
        what, scene, player = self.wizard().branch().listens()
        self.assertEqual((scene, player), (choices.hook_scene(), choices.tune_player()))
        other = next(role for role in choices.tune_players_offered() if role != choices.tune_player())
        choices.set_tune_played_by(other)
        await self.press(Key.DOWN, Key.UP)
        what, scene, player = self.wizard().branch().listens()
        self.assertEqual(player, other)
        setlist, name = choices.made_for_listening()
        self.assertTrue(setlist.get_song(name).get_scenes()[scene].has_clip_slot(player))
        self.assertFalse(setlist.get_song(name).get_scenes()[scene].has_clip_slot(choices.tune_player()))

    async def test_edit_opens_the_whole_section_in_the_pattern_editor_and_edited_notes_are_the_sections_own(self):
        choices = self.choices()
        kind = choices.hook_kind()
        await self.select_field(labels.MSG_WIZARD_EDIT_KIND_NOTES_BUTTON.format(kind=kind.capitalize()))
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.change_first_step()
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, WizardPage)
        self.assertTrue(choices.tune_is_own(kind))
        self.assertIn(messages.MSG_WIZARD_NOTES_BY_HAND, self.text())
        # Notes written by hand are never written over by another hook.
        self.assertNotIn(labels.MSG_WIZARD_REGENERATE_BUTTON, self.field_labels())
        # Where the hook sits among the chorus's lines is the chorus's to say, on the chorus's own panel.
        self.assertNotIn(labels.MSG_WIZARD_PLACEMENT_LABEL, self.field_labels())
        await self.select_field(labels.MSG_WIZARD_SUNG_IN_LABEL)
        self.assertEqual(self.wizard().field().value(), choices.hook_line_place()[0])
        self.assertIn(marks.MSG_WIZARD_HOOK_CELL, self.text())

    async def test_behavior_lists_every_behavior_with_the_genres_said_to_be_so_and_writes_another_hook(self):
        choices = self.choices()
        usual = labels.MSG_WIZARD_VALUE_FROM.format(value=choices.genre_hook_behavior(), origin=labels.MSG_WIZARD_USUAL_MELODY)
        before = choices.hook_notes()
        await self.press(keybindings.WizardPage.TO_TREE)
        await self.open_panel(MELODY_KEY.format(kind=choices.hook_kind()))
        await self.select_field(labels.MSG_WIZARD_BEHAVIOR_LABEL)
        self.assertEqual(self.wizard().field().value(), usual)
        await self.press(Key.ENTER)
        self.assertEqual(list(self.app.screen.options), [usual if behavior == choices.genre_hook_behavior() else behavior for behavior in hook_writing.BEHAVIORS])
        other = next(behavior for behavior in hook_writing.BEHAVIORS if behavior != choices.genre_hook_behavior())
        await self.pick(other)
        self.assertEqual(choices.get_hook_behavior(), other)
        self.assertNotEqual(choices.hook_notes(), before)
        await self.press(Key.ENTER)
        await self.pick(usual)
        self.assertEqual(choices.hook_notes(), before)

    async def test_regenerate_asks_first_and_writes_another_hook_with_the_gauges_kept(self):
        choices = self.choices()
        choices.set_hook_gauge(name=hook_writing.HOLD, position=hook_writing.LOWEST)
        await self.press(Key.DOWN, Key.UP)
        before = choices.hook_notes()
        await self.select_field(labels.MSG_WIZARD_REGENERATE_BUTTON)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.NO)
        self.assertEqual(choices.hook_notes(), before)
        await self.press(Key.ENTER, keybindings.ConfirmDialog.YES)
        self.assertNotEqual(choices.hook_notes(), before)
        self.assertEqual(choices.get_hook_gauge(hook_writing.HOLD), hook_writing.LOWEST)
        self.assertIn(messages.MSG_WIZARD_REGENERATED.format(name=messages.MSG_WIZARD_HOOK_NAME), self.text())

    async def test_the_second_hook_is_switched_on_names_its_kind_of_section_and_has_a_button_of_its_own(self):
        choices = self.choices()
        self.assertNotIn(labels.MSG_WIZARD_NEW_SECOND_HOOK_BUTTON, self.field_labels())
        await self.select_field(labels.MSG_WIZARD_SECOND_HOOK_LABEL)
        await self.press(Key.SPACE)
        self.assertEqual(choices.get_second_hook_kind(), choices.second_hook_kinds()[0])
        self.assertIn(labels.MSG_WIZARD_SECOND_SUNG_IN_LABEL, self.field_labels())
        take = choices.get_second_hook_take()
        await self.select_field(labels.MSG_WIZARD_NEW_SECOND_HOOK_BUTTON)
        await self.press(Key.ENTER)
        self.assertEqual(choices.get_second_hook_take(), take + 1)
        await self.select_field(labels.MSG_WIZARD_SECOND_HOOK_LABEL)
        await self.press(Key.SPACE)
        self.assertFalse(choices.has_second_hook())

    async def test_listen_plays_the_hook_under_the_cursors_heading(self):
        choices = self.choices()
        choices.set_second_hook(choices.second_hook_kinds()[0])
        await self.press(Key.DOWN, Key.UP)
        await self.select_field(labels.MSG_WIZARD_SUNG_IN_LABEL)
        self.assertEqual(self.wizard().branch().listens(), (messages.MSG_WIZARD_LISTEN_HOOK, choices.hook_scene(), choices.tune_player()))
        await self.select_field(labels.MSG_WIZARD_SECOND_SUNG_IN_LABEL)
        self.assertEqual(self.wizard().branch().listens(), (messages.MSG_WIZARD_LISTEN_SECOND_HOOK, choices.second_hook_scene(), choices.tune_player()))


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
        self.assertEqual(self.wizard().field().value(), self.title(THE_GUITAR))
        bass = next(field for field in self.wizard().shown_fields() if field.label == self.title(THE_BASS))
        self.assertEqual(bass.value(), marks.MSG_WIZARD_COUNT_SHOWN.format(count=0))

    async def test_the_for_column_is_as_wide_as_its_widest_value_so_that_played_in_starts_at_one_place_on_every_row(self):
        choices = self.choices()
        guitar = self.title(THE_GUITAR)
        self.assertGreater(len(guitar), len(labels.MSG_WIZARD_RIFF_FOR_COLUMN))
        choices.give_riff(role=THE_BASS, riff=self.riff)
        choices.set_section_part(kind=A_KIND, role=THE_GUITAR, part=self.riff)
        await self.press(Key.DOWN, Key.UP)
        self.wizard().app.open_field_sections.add(guitar)
        await self.press(Key.DOWN, Key.UP)
        heading = next(field for field in self.wizard().shown_fields() if field.label == guitar)
        row = next(field for field in self.wizard().shown_fields() if field.label == self.riff)
        played_in = heading.value().index(labels.MSG_WIZARD_RIFF_PLAYED_IN_COLUMN)
        self.assertEqual(played_in, len(guitar) + len(A_COLUMN_GAP))
        self.assertTrue(heading.value().startswith(labels.MSG_WIZARD_RIFF_FOR_COLUMN))
        self.assertEqual(row.value()[:played_in].rstrip(), guitar)
        self.assertEqual(row.value()[played_in:], A_KIND)

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
