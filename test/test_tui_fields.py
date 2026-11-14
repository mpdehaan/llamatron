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
"""The kinds of field a settings page is made of (tui/screens/field.py): a toggle, a name, a number and a choice.

Each kind is tested on its own, with a stand-in for the page, and then on the real pages: every
number field stops at both of its ends whether it is stepped or typed, and every toggle answers
to Space and Enter alike.
"""

import unittest

from ui_testing import TRADE, CLIPS, LAZY, PUSH, SLIDES, CLAVE, CLIPPED, FADE, FOLK, POP, SMOOTH, SWAY, LEAD, ROLLS, THIN, UITest, UP_ARP, leaf_pages
from llamatron.composition.limits import MAX_CLIP_REPEAT, MAX_SCENE_REPEAT, MAX_TEMPO, MIN_REPEAT, MIN_TEMPO
from llamatron.composition.setlist import DEFAULT_SCALE
from llamatron.strings.errors import ERR_OUT_OF_RANGE
from llamatron.strings.labels import MSG_NAME_LABEL, MSG_REPEAT_LABEL, MSG_SEED_LABEL, MSG_TEMPO_LABEL
from llamatron.strings.legends import What
from llamatron.strings.marks import MSG_FIELD_TOGGLE_OFF, MSG_TOGGLE_ON
from llamatron.tui import keybindings
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.key_table import STEP_BACK, STEP_FORWARD
from llamatron.tui.keys import Key
from llamatron.tui.screens.arp_editor import ArpEditor
from llamatron.tui.screens.auto_ratchet_editor import AutoRatchetEditor
from llamatron.tui.screens.drift_editor import DriftEditor
from llamatron.tui.screens.clip_page import ClipPage
from llamatron.tui.screens.density_editor import DensityEditor
from llamatron.tui.screens.progression_editor import ProgressionEditor
from llamatron.tui.screens.voice_leading_editor import VoiceLeadingEditor
from llamatron.tui.screens.hocket_editor import HocketEditor
from llamatron.tui.screens.strum_editor import StrumEditor
from llamatron.tui.screens.euclid_editor import EuclidEditor
from llamatron.tui.screens.glide_editor import GlideEditor
from llamatron.tui.screens.shorten_editor import ShortenEditor
from llamatron.tui.screens.rush_editor import RushEditor
from llamatron.tui.screens.drag_editor import DragEditor
from llamatron.tui.screens.swell_editor import SwellEditor
from llamatron.tui.screens.articulate_editor import ArticulateEditor
from llamatron.tui.screens.field import ChoiceField, Field, Heading, NameField, NumberField, Toggle, within
from llamatron.tui.screens.field_page import FieldPage
from llamatron.tui.screens.file_page import FilePage
from llamatron.tui.screens.registers_page import RegistersPage
from llamatron.tui.screens.scale_page import ScalePage
from llamatron.tui.screens.scene_page import ScenePage
from llamatron.tui.screens.song_page import SongPage
from llamatron.tui.screens.track_editor import TrackEditor
from llamatron.tui.screens.instrument_editor import InstrumentEditor

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
        self.assertEqual(field.value(), MSG_TOGGLE_ON)
        field.enter()
        self.assertEqual(kept.stored, [False])

    def test_off_shows_a_blank_and_enter_turns_it_on(self):
        kept = Kept()
        field = Toggle(label=A_LABEL, on=False, set=kept.set)
        self.assertEqual(field.value(), MSG_FIELD_TOGGLE_OFF)
        field.enter()
        self.assertEqual(kept.stored, [True])

    def test_it_can_show_words_of_its_own(self):
        self.assertEqual(Toggle(label=A_LABEL, on=True, set=Kept().set, shown_on=ON_TEXT, shown_off=OFF_TEXT).value(), ON_TEXT)
        self.assertEqual(Toggle(label=A_LABEL, on=False, set=Kept().set, shown_on=ON_TEXT, shown_off=OFF_TEXT).value(), OFF_TEXT)

    def test_only_a_toggle_says_it_is_one_and_it_steps_and_clears_nothing(self):
        field = Toggle(label=A_LABEL, on=True, set=Kept().set)
        self.assertTrue(field.is_toggle())
        self.assertEqual(field.enter_what, What.TOGGLE)
        self.assertIsNone(field.adjust)
        self.assertIsNone(field.clear)
        self.assertFalse(Field(label=A_LABEL, value=lambda: SHOWN, enter=Kept().set, enter_what=What.TOGGLE).is_toggle())


class TestNameField(unittest.TestCase):

    def test_enter_renames_and_the_label_is_name(self):
        kept = Kept()
        field = NameField(value=lambda: SHOWN, rename=lambda: kept.set(SHOWN))
        self.assertEqual(field.label, MSG_NAME_LABEL)
        self.assertEqual(field.value(), SHOWN)
        self.assertEqual(field.enter_what, What.RENAME)
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
        field.adjust(STEP_FORWARD)
        field.adjust(STEP_BACK)
        self.assertEqual(kept.stored, [IN_THE_MIDDLE + 1, IN_THE_MIDDLE - 1])

    def test_stepping_stops_at_both_ends(self):
        kept = Kept()
        self.field(kept=kept, number=HIGHEST).adjust(STEP_FORWARD)
        self.field(kept=kept, number=LOWEST).adjust(STEP_BACK)
        self.assertEqual(kept.stored, [HIGHEST, LOWEST])

    def test_a_number_with_no_ends_steps_without_stopping(self):
        kept = Kept()
        field = NumberField(page=kept, label=A_LABEL, number=HIGHEST, set=kept.set)
        field.adjust(STEP_FORWARD)
        self.assertEqual(kept.stored, [HIGHEST + 1])

    def test_a_setting_with_no_number_steps_and_types_from_its_start(self):
        kept = Kept()
        field = self.field(kept=kept, number=None, start=A_START)
        field.adjust(STEP_FORWARD)
        self.assertEqual(kept.stored, [A_START + 1])
        field.enter()
        self.assertEqual(kept.asked, (A_LABEL, A_START, LOWEST, HIGHEST))

    def test_zero_is_a_number_and_not_a_missing_one(self):
        kept = Kept()
        field = NumberField(page=kept, label=A_LABEL, number=0, start=A_START, set=kept.set)
        self.assertEqual(field.value(), 0)
        field.adjust(STEP_FORWARD)
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
        self.field(kept=kept).adjust(STEP_FORWARD)
        self.field(kept=kept).adjust(STEP_BACK)
        self.field(kept=kept, current=CHOICES[-1]).adjust(STEP_FORWARD)
        self.field(kept=kept, current=CHOICES[0]).adjust(STEP_BACK)
        self.assertEqual(kept.stored, [CHOICES[2], CHOICES[0], CHOICES[-1], CHOICES[0]])

    def test_enter_opens_a_picker_on_the_current_choice_and_stores_the_one_picked(self):
        kept = Kept()
        field = self.field(kept=kept, current=CHOICES[2])
        self.assertEqual(field.enter_what, What.CHOOSE)
        field.enter()
        self.assertIsInstance(kept.dialog, ChoiceDialog)
        self.assertEqual(kept.dialog.place, 2)
        kept.answer(0)
        self.assertEqual(kept.stored, [CHOICES[0]])

    def test_the_picker_can_name_the_choices_and_open_on_another(self):
        kept = Kept()
        field = self.field(kept=kept, current=None, names=CHOICE_NAMES, shown=SHOWN, picked=CHOICES[1])
        self.assertEqual(field.value(), SHOWN)
        field.enter()
        self.assertEqual(kept.dialog.options, CHOICE_NAMES)
        self.assertEqual(kept.dialog.place, 1)

    def test_a_value_outside_the_list_opens_the_picker_on_the_first_choice(self):
        kept = Kept()
        self.field(kept=kept, current=NOT_A_CHOICE).enter()
        self.assertEqual(kept.dialog.place, 0)


AN_INSTRUMENT = 'synth'


class TestFieldsOnThePages(UITest):
    """The number fields and toggles of the real settings pages."""

    def pages(self):
        holder = self.app.screen.holder
        if not self.document.setlist().has_instrument(AN_INSTRUMENT):
            self.document.add_instrument(AN_INSTRUMENT)
        return [
            SongPage(holder), ScenePage(holder=holder, index=FIRST_SCENE), ClipPage(holder=holder, index=FIRST_SCENE, track=LEAD), ArpEditor(holder=holder, name=UP_ARP),
            TrackEditor(holder=holder, name=LEAD), RegistersPage(holder), FilePage(holder), AutoRatchetEditor(holder=holder, name=ROLLS), DriftEditor(holder=holder, name=SWAY),
            ProgressionEditor(holder=holder, name=POP), VoiceLeadingEditor(holder=holder, name=SMOOTH), HocketEditor(holder=holder, name=TRADE), StrumEditor(holder=holder, name=FOLK), EuclidEditor(holder=holder, name=CLAVE), GlideEditor(holder=holder, name=SLIDES), ShortenEditor(holder=holder, name=CLIPS),
            RushEditor(holder=holder, name=PUSH), DragEditor(holder=holder, name=LAZY),
            DensityEditor(holder=holder, name=THIN), SwellEditor(holder=holder, name=FADE), ArticulateEditor(holder=holder, name=CLIPPED),
            ScalePage(holder=holder, name=DEFAULT_SCALE), InstrumentEditor(holder=holder, name=AN_INSTRUMENT),
        ]

    async def show(self, page):
        self.app.screen.show_page(page)
        await self.pilot.pause()

    async def test_every_page_of_fields_is_toured(self):
        every = sorted(page.__name__ for page in leaf_pages() if issubclass(page, FieldPage))
        self.assertEqual(sorted(type(page).__name__ for page in self.pages()), every)

    async def test_every_number_with_ends_stops_at_them_however_long_an_arrow_is_held(self):
        for page in self.pages():
            await self.show(page)
            for place, field in enumerate(page.fields()):
                if not isinstance(field, NumberField) or field.lowest is None or field.highest is None:
                    continue
                page.place = place
                for direction in (STEP_FORWARD, STEP_BACK):
                    for _ in range(MORE_THAN_ANY_RANGE):
                        before = page.fields()[place].number
                        page.fields()[place].adjust(direction)
                        if page.fields()[place].number == before:
                            break
                    for _ in range(STEPS_PAST_THE_END):
                        page.fields()[place].adjust(direction)
                    now = page.fields()[place]
                    self.assertGreaterEqual(now.counted_from(), now.lowest, (type(page).__name__, now.label))
                    self.assertLessEqual(now.counted_from(), now.highest, (type(page).__name__, now.label))
            self.app.pop_screen()
            await self.pilot.pause()

    async def test_every_toggle_answers_to_space_and_to_enter(self):
        found = 0
        for page in self.pages():
            await self.show(page)
            for place, field in enumerate(page.shown_fields()):
                # A section's heading answers to the same keys, opening and closing, which its own test checks.
                if not field.is_toggle() or isinstance(field, Heading):
                    continue
                found += 1
                page.place = place
                before = page.shown_fields()[place].on
                await self.press(Key.SPACE)
                if self.app.screen is not page:
                    await self.press(Key.ENTER)
                self.assertEqual(page.shown_fields()[place].on, not before, (type(page).__name__, field.label))
                await self.press(Key.ENTER)
                if self.app.screen is not page:
                    await self.press(Key.ENTER)
                self.assertEqual(page.fields()[place].on, before, (type(page).__name__, field.label))
            self.app.pop_screen()
            await self.pilot.pause()
        self.assertGreater(found, 0)

    async def test_the_songs_tempo_stops_at_both_ends_and_a_typed_one_past_an_end_is_refused(self):
        await self.press(keybindings.MainPage.SONGS, Key.ENTER)
        await self.select_field(MSG_TEMPO_LABEL)
        self.document.set_tempo(MAX_TEMPO)
        await self.press(Key.RIGHT)
        self.assertEqual(self.document.song().get_tempo(), MAX_TEMPO)
        self.document.set_tempo(MIN_TEMPO)
        await self.press(Key.LEFT)
        self.assertEqual(self.document.song().get_tempo(), MIN_TEMPO)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.app.screen.value = str(MAX_TEMPO + 1)
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_tempo(), MIN_TEMPO)
        self.assertIn(ERR_OUT_OF_RANGE.format(number=MAX_TEMPO + 1, low=MIN_TEMPO, high=MAX_TEMPO), self.text())

    async def test_the_seed_has_no_ends_and_starts_from_nothing(self):
        await self.press(keybindings.MainPage.SONGS, Key.ENTER)
        await self.select_field(MSG_SEED_LABEL)
        self.assertIsNone(self.document.song().get_seed())
        await self.press(Key.RIGHT, Key.RIGHT)
        self.assertEqual(self.document.song().get_seed(), 2)
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.document.song().get_seed())

    async def test_a_scenes_and_a_clips_repeat_stop_where_typing_stops(self):
        await self.show(ScenePage(holder=self.app.screen.holder, index=FIRST_SCENE))
        await self.select_field(MSG_REPEAT_LABEL)
        self.document.set_scene_repeat(index=FIRST_SCENE, repeat=MAX_SCENE_REPEAT)
        await self.press(Key.RIGHT)
        self.assertEqual(self.document.song().get_scene(FIRST_SCENE).get_repeat(), MAX_SCENE_REPEAT)
        await self.press(Key.ESCAPE)
        await self.show(ClipPage(holder=self.app.screen.holder, index=FIRST_SCENE, track=LEAD))
        await self.select_field(MSG_REPEAT_LABEL)
        self.document.set_clip_slot_repeat(index=FIRST_SCENE, track=LEAD, repeat=MAX_CLIP_REPEAT)
        await self.press(Key.RIGHT)
        self.assertEqual(self.document.clip_slot(index=FIRST_SCENE, track=LEAD).get_repeat(), MAX_CLIP_REPEAT)
        self.document.set_clip_slot_repeat(index=FIRST_SCENE, track=LEAD, repeat=MIN_REPEAT)
        await self.press(Key.LEFT)
        self.assertEqual(self.document.clip_slot(index=FIRST_SCENE, track=LEAD).get_repeat(), MIN_REPEAT)


if __name__ == '__main__':
    unittest.main()
