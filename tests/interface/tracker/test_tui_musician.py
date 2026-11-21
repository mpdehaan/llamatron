# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The musician's editor: its fields, the instrument's own habits, and a heading for each kind of section the song has."""

from llamatron.engine.generators import musician as musician_plugin
from llamatron.engine.generators.musician import generator as musician, schema, strings as musician_strings
from llamatron.engine.generators.musician.model import MusicianSetting
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.generators.musician_editor import MusicianEditor
from llamatron.interface.tracker.screens.shared.field import gauge_shown
from llamatron.model.schema.file_format import SectionKind
from llamatron.user_strings import labels, marks
from tests.support import ui_testing
from tests.support.ui_testing import UITest

FIRST_SCENE = 0
VERSE_HEADING = labels.MSG_MUSICIAN_SECTION_HEADING.format(section=SectionKind.VERSE)
CHORUS_HEADING = labels.MSG_MUSICIAN_SECTION_HEADING.format(section=SectionKind.CHORUS)


class TestMusicianAdded(UITest):

    async def test_a_new_one_is_found_under_band_generators_and_starts_as_a_rhythm_guitarist(self):
        name = await self.add_generator(musician_plugin.SECTION)
        settings = self.document.song().get_setlist().get_generator_settings(kind=musician_plugin.NAME, name=name)
        self.assertEqual(settings.to_data(), {})
        self.assertEqual(settings.get_own(MusicianSetting.INSTRUMENT), schema.RHYTHM_GUITARIST)
        self.assertIsInstance(self.app.screen, MusicianEditor)
        self.assertIn(musician_strings.MSG_LABEL.upper(), self.text().upper())


class TestMusicianEditor(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.document.change_set(self.document.song().get_scene(FIRST_SCENE).set_section, SectionKind.VERSE)
        await self.open_generator(section=musician_plugin.SECTION)
        self.assertIsInstance(self.app.screen, MusicianEditor)

    def musician(self):
        return self.document.song().get_setlist().get_generator_settings(kind=musician_plugin.NAME, name=ui_testing.STRUMMER)

    async def choose(self, *, label, choice):
        await self.select_field(label)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        await self.pick(choice)

    async def test_the_page_shows_every_field_of_a_pitched_player(self):
        await self.choose(label=labels.MSG_TUNE_FROM_LABEL, choice=ui_testing.LEAD)
        shown = self.text()
        for label in (
            labels.MSG_MUSICIAN_INSTRUMENT_LABEL, labels.MSG_CHORDS_FROM_LABEL, labels.MSG_TUNE_FROM_LABEL, labels.MSG_MUSICIAN_ACTIVITY_LABEL, labels.MSG_MUSICIAN_LOUDNESS_LABEL,
            labels.MSG_MUSICIAN_LOOSENESS_LABEL, labels.MSG_MUSICIAN_GIVES_WAY_LABEL, labels.MSG_MUSICIAN_ACCENTS_LABEL, labels.MSG_MUSICIAN_NOTES_LABEL, labels.MSG_MUSICIAN_RANGE_LABEL,
        ):
            self.assertIn(label, shown)
        self.assertIn(schema.RHYTHM_GUITARIST, shown)

    async def test_the_instruments_are_offered_in_their_order_and_one_is_chosen(self):
        await self.select_field(labels.MSG_MUSICIAN_INSTRUMENT_LABEL)
        await self.press(Key.ENTER)
        self.assertEqual(list(self.app.screen.options), list(schema.INSTRUMENTS))
        await self.pick(schema.BACKING_ORGAN)
        self.assertEqual(self.musician().to_data(), {MusicianSetting.INSTRUMENT: schema.BACKING_ORGAN})

    async def test_an_instruments_own_habits_show_where_from_and_are_left_out_of_the_file(self):
        await self.choose(label=labels.MSG_TUNE_FROM_LABEL, choice=ui_testing.LEAD)
        await self.choose(label=labels.MSG_MUSICIAN_INSTRUMENT_LABEL, choice=schema.LEAD_ORGAN)
        self.assertEqual(self.musician().get_own(MusicianSetting.GIVES_WAY), schema.IN_THE_GAPS)
        self.assertEqual(self.musician().get_own(MusicianSetting.NOTES), schema.HELD_NOTES)
        self.assertIn(marks.MSG_FROM_INSTRUMENT_SHOWN.format(value=schema.IN_THE_GAPS), self.text())
        self.assertIn(marks.MSG_FROM_INSTRUMENT_SHOWN.format(value=schema.HELD_NOTES), self.text())
        await self.choose(label=labels.MSG_MUSICIAN_NOTES_LABEL, choice=schema.SHORT_NOTES)
        self.assertEqual(self.musician().to_data()[MusicianSetting.NOTES], schema.SHORT_NOTES)
        self.assertNotIn(marks.MSG_FROM_INSTRUMENT_SHOWN.format(value=schema.SHORT_NOTES), self.text())

    async def test_a_habit_chosen_by_hand_is_kept_through_a_change_of_instrument_and_given_back(self):
        await self.choose(label=labels.MSG_MUSICIAN_INSTRUMENT_LABEL, choice=schema.LEAD_ORGAN)
        await self.choose(label=labels.MSG_MUSICIAN_NOTES_LABEL, choice=schema.HELD_NOTES)
        self.assertEqual(self.musician().to_data()[MusicianSetting.NOTES], schema.HELD_NOTES)
        await self.choose(label=labels.MSG_MUSICIAN_INSTRUMENT_LABEL, choice=schema.BASSIST)
        self.assertEqual(self.musician().get_own(MusicianSetting.NOTES), schema.HELD_NOTES)
        await self.choose(label=labels.MSG_MUSICIAN_NOTES_LABEL, choice=labels.MSG_MUSICIAN_INSTRUMENT_CHOICE)
        self.assertNotIn(MusicianSetting.NOTES, self.musician().to_data())
        await self.choose(label=labels.MSG_TUNE_FROM_LABEL, choice=ui_testing.LEAD)
        await self.choose(label=labels.MSG_MUSICIAN_GIVES_WAY_LABEL, choice=schema.GIVES_WAY_OFTEN)
        await self.select_field(labels.MSG_MUSICIAN_GIVES_WAY_LABEL)
        await self.press(keybindings.MusicianEditor.CLEAR)
        self.assertNotIn(MusicianSetting.GIVES_WAY, self.musician().to_data())

    async def test_giving_way_shows_only_once_the_melodys_track_is_named(self):
        self.assertNotIn(labels.MSG_MUSICIAN_GIVES_WAY_LABEL, self.text())
        await self.choose(label=labels.MSG_TUNE_FROM_LABEL, choice=ui_testing.LEAD)
        self.assertIn(labels.MSG_MUSICIAN_GIVES_WAY_LABEL, self.text())
        await self.select_field(labels.MSG_TUNE_FROM_LABEL)
        await self.press(keybindings.MusicianEditor.CLEAR)
        self.assertNotIn(labels.MSG_MUSICIAN_GIVES_WAY_LABEL, self.text())

    async def test_the_habits_lists_start_with_the_instruments_own(self):
        await self.choose(label=labels.MSG_TUNE_FROM_LABEL, choice=ui_testing.LEAD)
        for label, choices in ((labels.MSG_MUSICIAN_GIVES_WAY_LABEL, schema.GIVES_WAY), (labels.MSG_MUSICIAN_NOTES_LABEL, schema.NOTE_LENGTHS)):
            await self.select_field(label)
            await self.press(Key.ENTER)
            self.assertEqual(list(self.app.screen.options), [labels.MSG_MUSICIAN_INSTRUMENT_CHOICE, *choices])
            await self.press(Key.ESCAPE)

    async def test_loudness_and_looseness_are_drawn_as_gauges(self):
        self.assertIn(gauge_shown(place=musician.USUAL_LOUDNESS, lowest=schema.QUIETEST + 1, highest=schema.LOUDEST), self.text())
        self.assertIn(gauge_shown(place=schema.TIGHT, lowest=schema.TIGHT + 1, highest=schema.LOOSEST), self.text())
        await self.select_field(labels.MSG_MUSICIAN_LOUDNESS_LABEL)
        await self.press(keybindings.MusicianEditor.MORE)
        self.assertIn(gauge_shown(place=musician.USUAL_LOUDNESS + 1, lowest=schema.QUIETEST + 1, highest=schema.LOUDEST), self.text())

    async def test_a_drummer_has_no_chords_and_no_range(self):
        await self.choose(label=labels.MSG_MUSICIAN_INSTRUMENT_LABEL, choice=schema.DRUMMER)
        shown = self.text()
        self.assertNotIn(labels.MSG_CHORDS_FROM_LABEL, shown)
        self.assertNotIn(labels.MSG_MUSICIAN_RANGE_LABEL, shown)
        self.assertIn(labels.MSG_TUNE_FROM_LABEL, shown)

    async def test_the_tracks_are_chosen_and_cleared(self):
        await self.choose(label=labels.MSG_TUNE_FROM_LABEL, choice=ui_testing.LEAD)
        self.assertEqual(self.musician().get_tune_from(), ui_testing.LEAD)
        await self.choose(label=labels.MSG_CHORDS_FROM_LABEL, choice=ui_testing.LEAD)
        self.assertEqual(self.musician().get_chords_from(), ui_testing.LEAD)
        await self.select_field(labels.MSG_TUNE_FROM_LABEL)
        await self.press(keybindings.MusicianEditor.CLEAR)
        self.assertIsNone(self.musician().get_tune_from())
        self.assertIn(marks.MSG_NONE_SHOWN, self.text())

    async def test_loudness_and_looseness_step_and_stop_at_their_ends(self):
        await self.select_field(labels.MSG_MUSICIAN_LOUDNESS_LABEL)
        await self.press(*[keybindings.MusicianEditor.MORE] * (schema.LOUDEST + 2))
        self.assertEqual(self.musician().get_own(MusicianSetting.LOUDNESS), schema.LOUDEST)
        await self.press(*[keybindings.MusicianEditor.LESS] * schema.LOUDEST)
        self.assertNotIn(MusicianSetting.LOUDNESS, self.musician().to_data())
        await self.select_field(labels.MSG_MUSICIAN_LOOSENESS_LABEL)
        await self.press(keybindings.MusicianEditor.LESS, keybindings.MusicianEditor.MORE)
        self.assertEqual(self.musician().get_own(MusicianSetting.LOOSENESS), schema.TIGHT + 1)

    async def test_the_touch_is_chosen_from_lists_in_their_own_order(self):
        for label, setting, choices in (
            (labels.MSG_MUSICIAN_ACTIVITY_LABEL, MusicianSetting.ACTIVITY, schema.ACTIVITIES),
            (labels.MSG_MUSICIAN_ACCENTS_LABEL, MusicianSetting.ACCENTS, schema.ACCENTS), (labels.MSG_MUSICIAN_RANGE_LABEL, MusicianSetting.RANGE, schema.RANGES),
        ):
            await self.select_field(label)
            await self.press(Key.ENTER)
            self.assertEqual(list(self.app.screen.options), list(choices))
            await self.pick(choices[-1])
            self.assertEqual(self.musician().get_own(setting), choices[-1])

    async def test_a_heading_shows_for_each_kind_of_section_the_song_has_and_no_other(self):
        shown = self.text()
        self.assertIn(VERSE_HEADING, shown)
        self.assertNotIn(CHORUS_HEADING, shown)

    async def test_under_a_sections_heading_the_musician_is_told_how_to_play_or_to_sit_out(self):
        await self.select_field(VERSE_HEADING)
        await self.press(Key.ENTER)
        await self.choose(label=labels.MSG_MUSICIAN_PLAYED_LABEL, choice=schema.HITS)
        self.assertEqual(self.musician().to_data(), {MusicianSetting.BY_SECTION: {SectionKind.VERSE: {schema.PLAYED: schema.HITS}}})
        await self.select_field(labels.MSG_MUSICIAN_PLAYS_LABEL)
        await self.press(Key.SPACE)
        self.assertFalse(self.musician().get_for(section=SectionKind.VERSE, name=schema.PLAYS))
        self.assertNotIn(labels.MSG_MUSICIAN_PLAYED_LABEL, self.text())
        await self.press(Key.SPACE)
        await self.choose(label=labels.MSG_MUSICIAN_PLAYED_LABEL, choice=schema.WHOLE)
        self.assertEqual(self.musician().to_data(), {})
