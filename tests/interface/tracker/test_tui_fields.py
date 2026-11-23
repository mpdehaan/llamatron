# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The kinds of field a settings page is made of (interface/tracker/screens/shared/field.py): a toggle, a name, a number and a choice.

Each kind is tested on its own, with a stand-in for the page, and then on the real pages: every
number field stops at both of its ends whether it is stepped or typed, and every toggle answers
to Space and Enter alike.
"""

import unittest

from llamatron.engine.generators import arp as arp_plugin, chords as chords_plugin, drift as drift_plugin, guitarify as guitarify_plugin, hocket as hocket_plugin, musician as musician_plugin, phrasing as phrasing_plugin, shapes as shapes_plugin, timing as timing_plugin
from llamatron.engine.generators.chords import strings as chords_strings
from llamatron.interface.forms.nodes import Field, NameField, NumberField, Toggle, within
from llamatron.interface.tracker import key_table, keybindings
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.dialogs.prompt_dialog import PromptDialog
from llamatron.interface.tracker.document_parts.built_in_place import BuiltInPlace
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.arrange.clip_page import ClipPage
from llamatron.interface.tracker.screens.arrange.scene_page import ScenePage
from llamatron.interface.tracker.screens.arrange.track_editor import TrackEditor
from llamatron.interface.tracker.screens.generators.chain_statements_page import ChainStatementsPage
from llamatron.interface.tracker.screens.set.draws_page import DrawsPage
from llamatron.interface.tracker.screens.set.file_page import FilePage
from llamatron.interface.tracker.screens.set.instrument_editor import InstrumentEditor
from llamatron.interface.tracker.screens.set.scale_page import ScalePage
from llamatron.interface.tracker.screens.set.song_page import SongPage
from llamatron.interface.tracker.screens.shared.field import ChoiceField, Heading
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.interface.tracker.screens.shared.generator_statements_page import GeneratorStatementsPage
from llamatron.interface.tracker.screens.shared.plugin_editor import PluginEditor
from llamatron.interface.tracker.screens.wizard.wizard_page import WizardPage
from llamatron.model.objects import setlist
from llamatron.model.schema import limits
from llamatron.user_strings import errors, labels, legends, marks
from llamatron.wizards.create_song.wizard_choices import genre_names
from tests.support import ui_testing
from tests.support.ui_testing import leaf_pages, UITest

A_LABEL = 'Amount'
A_TITLE = 'Amount, from 1 to 9'
LOWEST = 1
HIGHEST = 9
IN_THE_MIDDLE = 5
A_START = 3
SHOWN = 'five of them'
ON_TEXT = 'yes'
OFF_TEXT = 'no'
CHOICES = ['low', 'middle', 'high']
CHOICE_NAMES = ['Low', 'Middle', 'High']
NOT_A_CHOICE = 'elsewhere'
FIRST_SCENE = 0
# How many presses of Left or Right are more than enough to reach an end of any stepped number.
MORE_THAN_ANY_RANGE = 12000
STEPS_PAST_THE_END = 3


class Kept:
    """What a field stored and what the field asked the page for, for a test to read."""

    __slots__ = ('stored', 'asked', 'dialog', 'answer')

    def __init__(self):
        self.stored = []
        self.asked = None
        self.dialog = None
        self.answer = None

    def set(self, value):
        self.stored.append(value)

    def ask_number(self, *, title, value, then, low=None, high=None):
        self.asked = (title, value, low, high)
        self.answer = then

    def ask(self, *, dialog, then):
        self.dialog = dialog
        self.answer = then


class TestWithin(unittest.TestCase):

    def test_a_number_is_kept_between_its_ends(self):
        self.assertEqual(within(number=LOWEST - 1, lowest=LOWEST, highest=HIGHEST), LOWEST)
        self.assertEqual(within(number=HIGHEST + 1, lowest=LOWEST, highest=HIGHEST), HIGHEST)
        self.assertEqual(within(number=IN_THE_MIDDLE, lowest=LOWEST, highest=HIGHEST), IN_THE_MIDDLE)

    def test_a_missing_end_is_no_end(self):
        self.assertEqual(within(number=HIGHEST + 1, lowest=LOWEST, highest=None), HIGHEST + 1)
        self.assertEqual(within(number=LOWEST - 1, lowest=None, highest=HIGHEST), LOWEST - 1)


class TestToggle(unittest.TestCase):

    def test_it_shows_the_dot_when_on_and_enter_stores_the_other_state(self):
        kept = Kept()
        field = Toggle(label=A_LABEL, on=True, set=kept.set)
        self.assertEqual(field.value(), marks.MSG_TOGGLE_ON)
        field.enter()
        self.assertEqual(kept.stored, [False])

    def test_off_shows_a_blank_and_enter_turns_it_on(self):
        kept = Kept()
        field = Toggle(label=A_LABEL, on=False, set=kept.set)
        self.assertEqual(field.value(), marks.MSG_FIELD_TOGGLE_OFF)
        field.enter()
        self.assertEqual(kept.stored, [True])

    def test_it_can_show_words_of_its_own(self):
        self.assertEqual(Toggle(label=A_LABEL, on=True, set=Kept().set, shown_on=ON_TEXT, shown_off=OFF_TEXT).value(), ON_TEXT)
        self.assertEqual(Toggle(label=A_LABEL, on=False, set=Kept().set, shown_on=ON_TEXT, shown_off=OFF_TEXT).value(), OFF_TEXT)

    def test_only_a_toggle_says_it_is_one_and_it_steps_and_clears_nothing(self):
        field = Toggle(label=A_LABEL, on=True, set=Kept().set)
        self.assertTrue(field.is_toggle())
        self.assertEqual(field.enter_what, legends.What.TOGGLE)
        self.assertIsNone(field.adjust)
        self.assertIsNone(field.clear)
        self.assertFalse(Field(label=A_LABEL, value=lambda: SHOWN, enter=Kept().set, enter_what=legends.What.TOGGLE).is_toggle())


class TestNameField(unittest.TestCase):

    def test_enter_renames_and_the_label_is_name(self):
        kept = Kept()
        field = NameField(value=lambda: SHOWN, rename=lambda: kept.set(SHOWN))
        self.assertEqual(field.label, labels.MSG_NAME_LABEL)
        self.assertEqual(field.value(), SHOWN)
        self.assertEqual(field.enter_what, legends.What.RENAME)
        self.assertFalse(field.is_toggle())
        field.enter()
        self.assertEqual(kept.stored, [SHOWN])


class TestNumberField(unittest.TestCase):

    def field(self, *, kept, number=IN_THE_MIDDLE, **named):
        return NumberField(page=kept, label=A_LABEL, number=number, set=kept.set, lowest=LOWEST, highest=HIGHEST, **named)

    def test_it_shows_the_number_and_steps_it_either_way(self):
        kept = Kept()
        field = self.field(kept=kept)
        self.assertEqual(field.value(), IN_THE_MIDDLE)
        field.adjust(key_table.STEP_FORWARD)
        field.adjust(key_table.STEP_BACK)
        self.assertEqual(kept.stored, [IN_THE_MIDDLE + 1, IN_THE_MIDDLE - 1])

    def test_stepping_stops_at_both_ends(self):
        kept = Kept()
        self.field(kept=kept, number=HIGHEST).adjust(key_table.STEP_FORWARD)
        self.field(kept=kept, number=LOWEST).adjust(key_table.STEP_BACK)
        self.assertEqual(kept.stored, [HIGHEST, LOWEST])

    def test_a_number_with_no_ends_steps_without_stopping(self):
        kept = Kept()
        field = NumberField(page=kept, label=A_LABEL, number=HIGHEST, set=kept.set)
        field.adjust(key_table.STEP_FORWARD)
        self.assertEqual(kept.stored, [HIGHEST + 1])

    def test_a_setting_with_no_number_steps_and_types_from_its_start(self):
        kept = Kept()
        field = self.field(kept=kept, number=None, start=A_START)
        field.adjust(key_table.STEP_FORWARD)
        self.assertEqual(kept.stored, [A_START + 1])
        field.enter()
        self.assertEqual(kept.asked, (A_LABEL, A_START, LOWEST, HIGHEST))

    def test_zero_is_a_number_and_not_a_missing_one(self):
        kept = Kept()
        field = NumberField(page=kept, label=A_LABEL, number=0, start=A_START, set=kept.set)
        self.assertEqual(field.value(), 0)
        field.adjust(key_table.STEP_FORWARD)
        self.assertEqual(kept.stored, [1])

    def test_enter_asks_for_a_number_between_the_ends_and_stores_the_answer(self):
        kept = Kept()
        self.field(kept=kept).enter()
        self.assertEqual(kept.asked, (A_LABEL, IN_THE_MIDDLE, LOWEST, HIGHEST))
        kept.answer(HIGHEST)
        self.assertEqual(kept.stored, [HIGHEST])

    def test_the_text_shown_the_text_typed_over_and_the_title_can_each_be_given(self):
        kept = Kept()
        field = self.field(kept=kept, shown=SHOWN, typed=SHOWN, title=A_TITLE)
        self.assertEqual(field.value(), SHOWN)
        field.enter()
        self.assertEqual(kept.asked, (A_TITLE, SHOWN, LOWEST, HIGHEST))


class TestChoiceField(unittest.TestCase):

    def field(self, *, kept, current=CHOICES[1], **named):
        return ChoiceField(page=kept, label=A_LABEL, choices=CHOICES, current=current, set=kept.set, **named)

    def test_it_shows_the_choice_and_steps_through_the_list_stopping_at_both_ends(self):
        kept = Kept()
        self.assertEqual(self.field(kept=kept).value(), CHOICES[1])
        self.field(kept=kept).adjust(key_table.STEP_FORWARD)
        self.field(kept=kept).adjust(key_table.STEP_BACK)
        self.field(kept=kept, current=CHOICES[-1]).adjust(key_table.STEP_FORWARD)
        self.field(kept=kept, current=CHOICES[0]).adjust(key_table.STEP_BACK)
        self.assertEqual(kept.stored, [CHOICES[2], CHOICES[0], CHOICES[-1], CHOICES[0]])

    def test_enter_opens_a_picker_on_the_current_choice_and_stores_the_one_picked(self):
        kept = Kept()
        field = self.field(kept=kept, current=CHOICES[2])
        self.assertEqual(field.enter_what, legends.What.CHOOSE)
        field.enter()
        self.assertIsInstance(kept.dialog, ChoiceDialog)
        self.assertEqual(kept.dialog.cursor.get_place(), 2)
        kept.answer(0)
        self.assertEqual(kept.stored, [CHOICES[0]])

    def test_the_picker_can_name_the_choices_and_open_on_another(self):
        kept = Kept()
        field = self.field(kept=kept, current=None, names=CHOICE_NAMES, shown=SHOWN, picked=CHOICES[1])
        self.assertEqual(field.value(), SHOWN)
        field.enter()
        self.assertEqual(kept.dialog.options, CHOICE_NAMES)
        self.assertEqual(kept.dialog.cursor.get_place(), 1)

    def test_a_value_outside_the_list_opens_the_picker_on_the_first_choice(self):
        kept = Kept()
        self.field(kept=kept, current=NOT_A_CHOICE).enter()
        self.assertEqual(kept.dialog.cursor.get_place(), 0)


AN_INSTRUMENT = 'synth'


class FieldPagesTest(UITest):
    """What the tests of the real settings pages share: the pages, every settings page of the tracker, and showing one."""

    def pages(self):
        holder = self.app.screen.holder
        if not self.document.get_setlist().has_instrument(AN_INSTRUMENT):
            self.document.add_instrument(AN_INSTRUMENT)
        return [
            SongPage(holder), ScenePage(holder=holder, index=FIRST_SCENE), ClipPage(holder=holder, index=FIRST_SCENE, track=ui_testing.LEAD), PluginEditor(holder=holder, name=ui_testing.UP_ARP, section=arp_plugin.SECTION),
            TrackEditor(holder=holder, name=ui_testing.LEAD), DrawsPage(holder), FilePage(holder), PluginEditor(holder=holder, name=ui_testing.SWAY, section=drift_plugin.SECTION),
            PluginEditor(holder=holder, name=ui_testing.POP, section=chords_plugin.SECTION), PluginEditor(holder=holder, name=ui_testing.SMOOTH, section=chords_plugin.SECTION), PluginEditor(holder=holder, name=ui_testing.TRADE, section=hocket_plugin.SECTION), PluginEditor(holder=holder, name=ui_testing.FOLLOWS, section=chords_plugin.SECTION), PluginEditor(holder=holder, name=ui_testing.BREATHES, section=phrasing_plugin.SECTION), PluginEditor(holder=holder, name=ui_testing.STRUMMER, section=musician_plugin.SECTION), PluginEditor(holder=holder, name=ui_testing.PICKED, section=guitarify_plugin.SECTION),
            PluginEditor(holder=holder, name=ui_testing.LOOSE, section=timing_plugin.SECTION),
            PluginEditor(holder=holder, name=ui_testing.SHAPED, section=shapes_plugin.SECTION),
            ScalePage(holder=holder, name=setlist.DEFAULT_SCALE), ChainStatementsPage(holder=holder, name=ui_testing.NAMED),
            GeneratorStatementsPage(holder=holder, name=chords_strings.MSG_LABEL, section=chords_plugin.SECTION, built_in=BuiltInPlace(track=ui_testing.LEAD, scene=FIRST_SCENE, kind=chords_plugin.NAME)),
            InstrumentEditor(holder=holder, name=AN_INSTRUMENT), self.a_wizard(holder),
        ]

    def a_wizard(self, holder):
        """Return the song wizard with a genre and a subgenre chosen, so that its Genre branch shows every field, the tempo among them."""
        wizard = WizardPage(holder)
        choices = wizard.get_choices()
        choices.set_genre(genre_names()[0])
        choices.set_subgenre(choices.subgenres()[0])
        wizard.in_fields = True
        return wizard

    async def show(self, page):
        self.app.screen.show_page(page)
        await self.pilot.pause()

class TestFieldsOnThePages(FieldPagesTest):
    """The number fields and toggles of the real settings pages."""

    async def test_every_toured_page_has_a_class_for_its_numbers(self):
        self.assertEqual(len(self.pages()), PAGES_TOURED)

    async def test_every_page_of_fields_is_toured(self):
        every = sorted(page.__name__ for page in leaf_pages() if issubclass(page, FieldPage))
        # The page drawn from a plugin's view is toured once for each plugin that has one.
        self.assertEqual(sorted({type(page).__name__ for page in self.pages()}), every)

    async def test_every_toggle_answers_to_space_and_to_enter(self):
        found = 0
        for page in self.pages():
            await self.show(page)
            for place, field in enumerate(page.shown_fields()):
                # A section's heading answers to the same keys, opening and closing, which its own test checks.
                if not field.is_toggle() or isinstance(field, Heading):
                    continue
                found += 1
                page.cursor.set_place(place)
                before = page.shown_fields()[place].on
                await self.press(Key.SPACE)
                if self.app.screen is not page:
                    await self.press(Key.ENTER)
                self.assertEqual(page.shown_fields()[place].on, not before, (type(page).__name__, field.label))
                await self.press(Key.ENTER)
                if self.app.screen is not page:
                    await self.press(Key.ENTER)
                self.assertEqual(page.shown_fields()[place].on, before, (type(page).__name__, field.label))
            self.app.pop_screen()
            await self.pilot.pause()
        self.assertGreater(found, 0)

    async def test_the_songs_tempo_stops_at_both_ends_and_a_typed_one_past_an_end_is_refused(self):
        await self.press(keybindings.MainPage.SONGS, Key.ENTER)
        await self.select_field(labels.MSG_TEMPO_LABEL)
        self.document.change_set(self.document.song().set_tempo, limits.MAX_TEMPO)
        await self.press(Key.RIGHT)
        self.assertEqual(self.document.song().get_tempo(), limits.MAX_TEMPO)
        self.document.change_set(self.document.song().set_tempo, limits.MIN_TEMPO)
        await self.press(Key.LEFT)
        self.assertEqual(self.document.song().get_tempo(), limits.MIN_TEMPO)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.app.screen.value = str(limits.MAX_TEMPO + 1)
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_tempo(), limits.MIN_TEMPO)
        self.assertIn(errors.ERR_OUT_OF_RANGE.format(number=limits.MAX_TEMPO + 1, low=limits.MIN_TEMPO, high=limits.MAX_TEMPO), self.text())

    async def test_a_scenes_and_a_clips_repeat_stop_where_typing_stops(self):
        await self.show(ScenePage(holder=self.app.screen.holder, index=FIRST_SCENE))
        await self.select_field(labels.MSG_REPEAT_LABEL)
        self.document.change_set(self.document.song().get_scene(FIRST_SCENE).set_repeat, limits.MAX_SCENE_REPEAT)
        await self.press(Key.RIGHT)
        self.assertEqual(self.document.song().get_scene(FIRST_SCENE).get_repeat(), limits.MAX_SCENE_REPEAT)
        await self.press(Key.ESCAPE)
        await self.show(ClipPage(holder=self.app.screen.holder, index=FIRST_SCENE, track=ui_testing.LEAD))
        await self.select_field(labels.MSG_REPEAT_LABEL)
        self.document.set_clip_slot_repeat(index=FIRST_SCENE, track=ui_testing.LEAD, repeat=limits.MAX_CLIP_REPEAT)
        await self.press(Key.RIGHT)
        self.assertEqual(self.document.clip_slot(index=FIRST_SCENE, track=ui_testing.LEAD).get_repeat(), limits.MAX_CLIP_REPEAT)
        self.document.set_clip_slot_repeat(index=FIRST_SCENE, track=ui_testing.LEAD, repeat=limits.MIN_REPEAT)
        await self.press(Key.LEFT)
        self.assertEqual(self.document.clip_slot(index=FIRST_SCENE, track=ui_testing.LEAD).get_repeat(), limits.MIN_REPEAT)



class NumbersStopAtTheirEnds:
    """Every number with ends on one settings page stops at them. A test class takes it with FieldPagesTest and says its page's place."""

    __slots__ = ()

    # The place of the page among FieldPagesTest.pages().
    PAGE = 0

    async def test_every_number_with_ends_stops_at_them_however_long_an_arrow_is_held(self):
        page = self.pages()[self.PAGE]
        await self.show(page)
        for place, field in enumerate(page.fields()):
            if not isinstance(field, NumberField) or field.lowest is None or field.highest is None:
                continue
            page.cursor.set_place(place)
            for direction in (key_table.STEP_FORWARD, key_table.STEP_BACK):
                # The walk starts a step short of the end it walks to, since stepping the whole range, as far as 9999 steps, took long
                # and proved no more than the last steps do.
                held = page.fields()[place]
                held.set(held.highest - 1 if direction == key_table.STEP_FORWARD else held.lowest + 1)
                for _ in range(MORE_THAN_ANY_RANGE):
                    held = page.fields()[place]
                    before = held.number
                    held.adjust(direction)
                    if page.fields()[place].number == before:
                        break
                for _ in range(STEPS_PAST_THE_END):
                    page.fields()[place].adjust(direction)
                now = page.fields()[place]
                self.assertGreaterEqual(now.counted_from(), now.lowest, (type(page).__name__, now.label))
                self.assertLessEqual(now.counted_from(), now.highest, (type(page).__name__, now.label))
        self.app.pop_screen()
        await self.pilot.pause()


# The settings pages FieldPagesTest tours.
PAGES_TOURED = 22


class TestNumbersStopAtTheirEndsOnTheSongPage(NumbersStopAtTheirEnds, FieldPagesTest):
    """Holding an arrow on the Song page's numbers. Every number field is the one Field class, which the stand-in tests above try
    in every kind, so two real pages stand for them all."""

    __slots__ = ()
    PAGE = 0


class TestNumbersStopAtTheirEndsOnTheArpEditor(NumbersStopAtTheirEnds, FieldPagesTest):
    """Holding an arrow on the Arpeggiator editor's numbers, a generator's settings standing for every generator's."""

    __slots__ = ()
    PAGE = 3


if __name__ == '__main__':
    unittest.main()
