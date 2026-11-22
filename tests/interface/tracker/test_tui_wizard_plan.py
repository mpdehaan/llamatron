# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The song wizard's page on a planned song: the plan's fields on the Form panel and the hook's kind on the Hooks panel."""

from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.keys import Key
from llamatron.model.schema import limits
from llamatron.user_strings import errors, labels, marks
from llamatron.wizards.create_song import hook_writing, song_plan, wizard_limits, wizard_names
from llamatron.wizards.create_song.own_values import chords_as_text
from tests.interface.tracker.test_tui_wizard import WizardTest
from tests.support.ui_testing import key_of

A_PLANNED_GENRE = 'rock'
A_SECTION = 'verse-1'
A_PLACE = 1
SOME_CHORDS = '6 4 1 5'
NOT_A_CHORD = ' x'
A_FEW_WORDS = 20
A_SUBGENRE = 'arena rock'
A_SUBGENRE_IN_SIX = 'six-eight ballad'
AN_UNPLANNED_GENRE = 'experimental'


class TestWizardPlan(WizardTest):
    """The Form panel's Song plan, Contrast and Phrasing, and the hook's Contour, Rhythm and Detail on the panel of the kind of section that says the hook line."""

    async def choose(self, *, genre=A_PLANNED_GENRE, subgenre=A_SUBGENRE):
        choices = self.choices()
        choices.set_genre(genre)
        choices.set_subgenre(subgenre or choices.subgenres()[0])
        await self.press(Key.DOWN, Key.UP)

    async def go_to_hooks(self):
        await self.go_to_hook_panel()

    async def go_to_melody(self):
        names = [branch.name() for _, branch in self.wizard().rows()]
        await self.go_to_branch(names.index(labels.MSG_WIZARD_MELODY_BRANCH))

    async def switch_plan_on(self):
        """Go into the Form panel's fields, where a genre with a plan has the plan on from the start."""
        await self.go_to_named_branch(labels.MSG_WIZARD_FORM_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)

    async def test_a_genre_with_a_plan_plans_the_song_from_the_start_and_the_switch_takes_the_plan_s_fields_away(self):
        await self.choose()
        await self.switch_plan_on()
        choices = self.choices()
        self.assertTrue(choices.has_song_plan())
        shown = self.text()
        self.assertIn(labels.MSG_WIZARD_CONTRAST_LABEL, shown)
        for said in choices.said_of_sections():
            self.assertIn(said.split('.')[0], shown)
        await self.select_field(labels.MSG_WIZARD_SONG_PLAN_LABEL)
        await self.press(Key.ENTER)
        self.assertFalse(choices.has_song_plan())
        self.assertNotIn(labels.MSG_WIZARD_CONTRAST_LABEL, self.text())
        self.assertTrue(self.wizard().has_choices_to_lose())

    async def test_contrast_steps_and_phrasing_toggles(self):
        await self.choose()
        await self.switch_plan_on()
        await self.select_field(labels.MSG_WIZARD_CONTRAST_LABEL)
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.choices().get_contrast(), song_plan.USUAL_CONTRAST + 1)
        await self.press(keybindings.WizardPage.TO_TREE)
        await self.go_to_melody()
        self.assertIn(labels.MSG_WIZARD_EDIT_PHRASING_BUTTON, self.text())
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels.MSG_WIZARD_PHRASING_LABEL)
        await self.press(Key.ENTER)
        self.assertIsNone(self.choices().tune_phrasing())
        self.assertNotIn(labels.MSG_WIZARD_EDIT_PHRASING_BUTTON, self.text())
        await self.press(Key.ENTER)
        self.assertEqual(self.choices().tune_phrasing(), {})

    async def test_a_genre_with_no_plan_shows_no_switch_and_a_song_in_six_still_has_its_phrasing(self):
        await self.choose(genre=AN_UNPLANNED_GENRE, subgenre=None)
        await self.go_to_named_branch(labels.MSG_WIZARD_FORM_BRANCH)
        self.assertNotIn(labels.MSG_WIZARD_SONG_PLAN_LABEL, self.text())
        await self.choose(subgenre=A_SUBGENRE_IN_SIX)
        await self.switch_plan_on()
        self.assertIn(labels.MSG_WIZARD_CONTRAST_LABEL, self.text())
        await self.press(keybindings.WizardPage.TO_TREE)
        await self.go_to_melody()
        # A Phrasing counts in bars, whatever the bar holds, so a tune in six is delivered in lines as a tune in four is.
        self.assertIn(labels.MSG_WIZARD_PHRASING_LABEL, self.text())

    async def test_the_panel_of_the_section_that_says_the_hook_shows_the_behavior_and_the_gauges_with_the_genre_s_said_to_be_so(self):
        await self.choose()
        await self.go_to_hook_writing()
        choices = self.choices()
        hook_choices = choices.get_hook()
        hook = hook_choices
        shown = self.text()
        self.assertIn(labels.MSG_WIZARD_VALUE_FROM.format(value=hook.genre_hook_behavior(), origin=labels.MSG_WIZARD_USUAL_MELODY), shown)
        for name in hook.hook_gauges():
            self.assertIn(labels.MSG_WIZARD_HOOK_GAUGE_LABELS[name], shown)

    async def test_stepping_a_gauge_moves_it_the_picture_follows_and_the_delete_key_gives_it_back(self):
        await self.choose()
        await self.go_to_hook_writing()
        choices = self.choices()
        hook_choices = choices.get_hook()
        hook = hook_choices
        before = hook.hook_notes()
        usual = hook.genre_hook_gauge(hook_writing.SIMPLICITY)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels.MSG_WIZARD_HOOK_GAUGE_LABELS[hook_writing.SIMPLICITY])
        less = key_of(binding=keybindings.WizardPage.LESS, key=Key.LEFT_BRACKET)
        for _ in range(usual - wizard_names.HOOK_WRITING_LOWEST):
            await self.press(less)
        self.assertEqual(hook.get_hook_gauge(hook_writing.SIMPLICITY), wizard_names.HOOK_WRITING_LOWEST)
        self.assertNotEqual(hook.hook_notes(), before)
        await self.press(less)
        self.assertEqual(hook.get_hook_gauge(hook_writing.SIMPLICITY), wizard_names.HOOK_WRITING_LOWEST)
        await self.press(keybindings.FieldPage.CLEAR)
        self.assertEqual(hook.get_hook_gauge(hook_writing.SIMPLICITY), usual)
        self.assertEqual(hook.hook_notes(), before)

    async def test_choosing_a_behavior_leaves_only_its_gauges(self):
        await self.choose()
        self.choices().get_hook().set_hook_behavior(wizard_names.CHANT)
        await self.press(Key.DOWN, Key.UP)
        await self.go_to_hook_writing()
        self.assertIn(labels.MSG_WIZARD_HOOK_GAUGE_LABELS[hook_writing.HOLD], self.text())
        self.assertNotIn(labels.MSG_WIZARD_HOOK_GAUGE_LABELS[hook_writing.LEAP], self.text())


THE_GROUPS = (labels.MSG_WIZARD_GROUP_TUNE, labels.MSG_WIZARD_GROUP_HARMONY, labels.MSG_WIZARD_GROUP_SHAPE, labels.MSG_WIZARD_GROUP_JOINS, labels.MSG_WIZARD_GROUP_PLAYERS)


class TestWizardSectionOwnFields(WizardTest):
    """A section's panel on a planned song: what the section is given of its own."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        choices = self.choices()
        choices.set_genre(A_PLANNED_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        choices.set_song_plan(True)
        await self.press(Key.DOWN, Key.UP)
        names = [branch.name() for _, branch in self.wizard().rows()]
        await self.go_to_branch(names.index(A_SECTION))
        await self.press(keybindings.WizardPage.INTO_FIELDS)

    def label(self, field):
        return labels.MSG_WIZARD_SECTION_OWN_LABELS[field]

    async def open_every_group(self):
        """Open each heading of the section's panel that is closed, so that every field shows."""
        for label in THE_GROUPS:
            headings = [field for field in self.app.screen.shown_fields() if field.label == label]
            if headings and not self.app.screen.is_open(headings[0]):
                await self.select_field(label)
                await self.press(Key.ENTER)

    async def test_the_fields_are_in_groups_closed_until_opened_that_say_when_something_inside_is_set(self):
        choices = self.choices()
        place_section = choices.section(A_PLACE)
        shown = self.text()
        for label in THE_GROUPS:
            self.assertIn(label, shown)
        self.assertIn(self.label(wizard_names.SONG_PLAN_ENERGY), shown)
        self.assertNotIn(self.label(wizard_names.TEMPO_END_OF_PLACE), shown)
        self.assertNotIn(marks.MSG_SECTION_SET, shown)
        place_section.set_own(field=wizard_names.SONG_PLAN_RISES, value=not place_section.from_plan(field=wizard_names.SONG_PLAN_RISES))
        await self.press(Key.DOWN, Key.UP)
        self.assertIn(marks.MSG_SECTION_SET, self.text())
        await self.open_every_group()
        self.assertIn(self.label(wizard_names.TEMPO_END_OF_PLACE), self.text())

    async def test_each_field_shows_what_the_section_takes_and_where_from(self):
        choices = self.choices()
        place_section = choices.section(A_PLACE)
        await self.open_every_group()
        shown = self.text()
        for field in place_section.own_fields():
            self.assertIn(self.label(field), shown)
            if field in (wizard_names.SONG_PLAN_RISES, wizard_names.SONG_PLAN_FADES):
                # A switch shows on or off and no origin.
                continue
            self.assertIn(labels.MSG_WIZARD_VALUE_FROM.format(value=place_section.from_plan(field=field), origin=labels.MSG_WIZARD_SECTION_ORIGINS[field]), shown)

    async def test_energy_steps_from_the_plan_s_and_bksp_gives_it_back(self):
        choices = self.choices()
        place_section = choices.section(A_PLACE)
        usual = choices.energies()[A_PLACE]
        await self.select_field(self.label(wizard_names.SONG_PLAN_ENERGY))
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(place_section.own(field=wizard_names.SONG_PLAN_ENERGY), usual + 1)
        self.assertNotIn(labels.MSG_WIZARD_VALUE_FROM.format(value=usual, origin=labels.MSG_WIZARD_SECTION_ORIGINS[wizard_names.SONG_PLAN_ENERGY]), self.text())
        await self.press(keybindings.FieldPage.CLEAR)
        self.assertIsNone(place_section.own(field=wizard_names.SONG_PLAN_ENERGY))

    async def test_a_way_of_leaving_a_key_and_a_scale_are_chosen_from_a_list(self):
        choices = self.choices()
        place_section = choices.section(A_PLACE)
        for field in (wizard_names.JOINS_LEAVES, wizard_names.ROOT_OF_PLACE, wizard_names.TYPE_OF_PLACE):
            await self.select_field(self.label(field))
            await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
            self.assertIsNotNone(place_section.own(field=field))

    async def test_chords_are_typed_and_what_cannot_be_chords_is_said(self):
        choices = self.choices()
        place_section = choices.section(A_PLACE)
        await self.select_field(self.label(wizard_names.ARRANGER_CHORDS))
        await self.press(Key.ENTER)
        for _ in range(limits.MAX_NAME_LENGTH):
            await self.press(Key.BACKSPACE)
        await self.type(SOME_CHORDS)
        await self.press(Key.ENTER)
        self.assertEqual(chords_as_text(place_section.own(field=wizard_names.ARRANGER_CHORDS)), SOME_CHORDS)
        await self.press(Key.ENTER)
        await self.type(NOT_A_CHORD)
        await self.press(Key.ENTER)
        self.assertEqual(chords_as_text(place_section.own(field=wizard_names.ARRANGER_CHORDS)), SOME_CHORDS)
        self.assertIn(errors.ERR_WIZARD_CHORDS.split('{')[0][:A_FEW_WORDS], self.text())

    async def test_a_song_with_no_plan_keeps_the_chords_the_tempo_the_key_and_the_scale(self):
        self.choices().set_song_plan(False)
        await self.press(Key.DOWN, Key.UP)
        await self.open_every_group()
        shown = self.text()
        self.assertNotIn(self.label(wizard_names.SONG_PLAN_ENERGY), shown)
        for field in (wizard_names.ARRANGER_CHORDS, wizard_names.TEMPO_END_OF_PLACE, wizard_names.ROOT_OF_PLACE, wizard_names.TYPE_OF_PLACE):
            self.assertIn(self.label(field), shown)


class TestWizardFormQuestions(WizardTest):
    """The Form panel's questions, a dialog each, and the form made from the answers."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        choices = self.choices()
        choices.set_genre(A_PLANNED_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        await self.press(Key.DOWN, Key.UP)
        await self.go_to_named_branch(labels.MSG_WIZARD_FORM_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels.MSG_WIZARD_FORM_QUESTIONS_BUTTON)

    async def test_the_usual_answers_make_the_usual_form_of_the_questions(self):
        choices = self.choices()
        form_choices = choices.get_song_form()
        song_form = form_choices
        await self.press(Key.ENTER)
        for name, _, _ in song_form.form_questions():
            self.assertIn(labels.MSG_WIZARD_FORM_QUESTION_TITLES[name], self.text())
            await self.press(Key.ENTER)
        self.assertTrue(song_form.has_own_form())
        self.assertEqual(song_form.section_kinds_in_form(), song_form.form_of_answers({}))
        self.assertTrue(self.wizard().has_choices_to_lose())

    async def test_another_answer_is_in_the_form_made(self):
        choices = self.choices()
        form_choices = choices.get_song_form()
        song_form = form_choices
        await self.press(Key.ENTER)
        for name, _, _ in song_form.form_questions():
            await self.press(*([Key.DOWN] if name == wizard_limits.DRUM_SOLO_KIND else []), Key.ENTER)
        self.assertIn(wizard_limits.DRUM_SOLO_KIND, song_form.section_kinds_in_form())

    async def test_esc_at_a_question_leaves_the_form_alone(self):
        choices = self.choices()
        form_choices = choices.get_song_form()
        song_form = form_choices
        before = song_form.section_kinds_in_form()
        await self.press(Key.ENTER, Key.ENTER, Key.ESCAPE)
        self.assertFalse(song_form.has_own_form())
        self.assertEqual(song_form.section_kinds_in_form(), before)

    async def test_a_form_a_person_changed_is_replaced_only_on_a_yes(self):
        choices = self.choices()
        form_choices = choices.get_song_form()
        place_section = choices.section(A_PLACE)
        song_form = form_choices
        place_section.copy()
        before = song_form.section_kinds_in_form()
        await self.press(Key.ENTER)
        for _ in song_form.form_questions():
            await self.press(Key.ENTER)
        self.assertIn(labels.MSG_WIZARD_REPLACE_SECTIONS_TITLE, self.text())
        await self.press(keybindings.ConfirmDialog.NO)
        self.assertEqual(song_form.section_kinds_in_form(), before)

    async def test_a_genre_with_no_verse_and_chorus_has_no_questions(self):
        choices = self.choices()
        choices.set_genre(AN_UNPLANNED_GENRE)
        choices.set_subgenre(choices.subgenres()[0])
        await self.press(keybindings.WizardPage.TO_TREE, Key.DOWN, Key.UP)
        await self.go_to_named_branch(labels.MSG_WIZARD_FORM_BRANCH)
        self.assertNotIn(labels.MSG_WIZARD_FORM_QUESTIONS_BUTTON, self.text())
