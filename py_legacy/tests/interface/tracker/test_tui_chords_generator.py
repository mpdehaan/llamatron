# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The tracker's Chords generator: its page, its Mode first and then the Progression column in Progression mode, the Follow
column in Follow Progression mode, and the Voicing column in every mode."""

from llamatron.engine.generators import chords as chords_plugin
from llamatron.engine.generators.chords import model as chords_model, strings as chords_strings, view as chords_view
from llamatron.engine.generators.chords.model import ChordsSetting
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.shared.chords_editor import ChordsEditor
from llamatron.interface.tracker.screens.shared.plugin_editor import PluginEditor
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import labels, marks
from tests.support import ui_testing
from tests.support.ui_testing import UITest

# The test song's progression, pop, shown as numerals in C major.
POP_NUMERALS = 'I V vi IV'
NEW_ONE = 'harmony'
GONE = 'nobody'


class TestChordsAdded(UITest):

    async def test_a_new_one_voices_chords_and_sets_nothing(self):
        name = await self.add_generator(chords_plugin.SECTION)
        settings = self.document.get_setlist().get_generator_settings(kind=chords_plugin.NAME, name=name)
        self.assertEqual(settings.to_data(), {})
        self.assertEqual(settings.get_mode(), chords_model.VOICING)
        self.assertTrue(settings.voices())


class ChordsPageTest(UITest):
    """A Chords generator's page, open on one of the test song's Chords generators, named by NAME."""

    NAME = None

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_generator(section=chords_plugin.SECTION, name=self.NAME)
        self.assertIsInstance(self.app.screen, PluginEditor)

    def settings(self):
        return self.document.get_setlist().get_generator_settings(kind=chords_plugin.NAME, name=self.NAME)

    def labels(self):
        return [field.label for field in self.app.screen.shown_fields()]


class TestModes(ChordsPageTest):
    """The Mode comes first and decides which column shows; the Voicing column shows in every mode, its Voice leading on by
    default in Voicing mode alone."""

    NAME = ui_testing.SMOOTH

    async def test_enabled_and_mode_come_first_and_each_mode_shows_its_own_column_and_the_voicing_column(self):
        self.assertEqual(self.labels()[1:3], [labels.MSG_ENABLED_LABEL, chords_strings.MSG_MODE_LABEL])
        self.assertIn(chords_view.MODE_NAMES[chords_model.VOICING], self.text())
        self.assertNotIn(labels.MSG_EVERY_LABEL, self.labels())
        self.assertNotIn(labels.MSG_CHORDS_FROM_LABEL, self.labels())
        await self.select_field(chords_strings.MSG_MODE_LABEL)
        await self.press(keybindings.PluginEditor.MORE)
        self.assertEqual(self.settings().get_mode(), chords_model.PROGRESSION)
        self.assertIn(labels.MSG_EVERY_LABEL, self.labels())
        self.assertIn(labels.MSG_LOWEST_OCTAVE_LABEL, self.labels())
        await self.press(keybindings.PluginEditor.MORE)
        self.assertEqual(self.settings().get_mode(), chords_model.FOLLOW_PROGRESSION)
        self.assertIn(labels.MSG_CHORDS_FROM_LABEL, self.labels())
        self.assertNotIn(labels.MSG_EVERY_LABEL, self.labels())
        await self.press(keybindings.PluginEditor.LESS, keybindings.PluginEditor.LESS)
        self.assertIsNone(self.settings().get_written(ChordsSetting.MODE))

    async def test_voice_leading_is_on_in_voicing_mode_and_off_in_the_others_unless_set(self):
        self.assertTrue(self.settings().voices())
        await self.select_field(chords_strings.MSG_MODE_LABEL)
        await self.press(keybindings.PluginEditor.MORE)
        self.assertFalse(self.settings().voices())
        await self.select_field(chords_strings.MSG_VOICE_LEADING_LABEL)
        await self.press(keybindings.PluginEditor.TOGGLE)
        self.assertTrue(self.settings().voices())
        self.assertTrue(self.settings().get_written(ChordsSetting.VOICE_LEADING))
        await self.press(keybindings.PluginEditor.TOGGLE)
        self.assertIsNone(self.settings().get_written(ChordsSetting.VOICE_LEADING))


class TestVoicing(ChordsPageTest):
    """The Voicing column's octaves, shown in the set's octave labels, never cross, and its root stays in the bass when asked."""

    NAME = ui_testing.SMOOTH

    async def test_the_lowest_octave_never_passes_the_highest(self):
        steps = chords_model.DEFAULT_VOICING_HIGHEST_OCTAVE - chords_model.DEFAULT_VOICING_LOWEST_OCTAVE + 1
        await self.select_field(labels.MSG_LOWEST_OCTAVE_LABEL)
        await self.press(*[keybindings.PluginEditor.MORE] * steps)
        self.assertEqual(self.settings().get_lowest_octave(), chords_model.DEFAULT_VOICING_HIGHEST_OCTAVE)

    async def test_the_highest_octave_steps_down_and_bksp_puts_it_back(self):
        await self.select_field(labels.MSG_HIGHEST_OCTAVE_LABEL)
        await self.press(keybindings.PluginEditor.LESS)
        self.assertEqual(self.settings().get_highest_octave(), chords_model.DEFAULT_VOICING_HIGHEST_OCTAVE - 1)
        await self.press(Key.BACKSPACE)
        self.assertEqual(self.settings().get_highest_octave(), chords_model.DEFAULT_VOICING_HIGHEST_OCTAVE)
        self.assertIsNone(self.settings().get_written(ChordsSetting.HIGHEST_OCTAVE))

    async def test_keep_the_root_in_the_bass_turns_on_and_off(self):
        await self.select_field(labels.MSG_ROOT_IN_BASS_LABEL)
        await self.press(keybindings.PluginEditor.TOGGLE)
        self.assertTrue(self.settings().keeps_root_in_bass())
        await self.press(keybindings.PluginEditor.TOGGLE)
        self.assertFalse(self.settings().keeps_root_in_bass())


class TestProgressionMode(ChordsPageTest):
    """In Progression mode: Every from the one list of times, a bar unless set, and Chords, shown as numerals, opening the chord editor."""

    NAME = ui_testing.POP

    async def test_every_starts_at_a_bar_and_steps_through_the_list(self):
        self.assertIn(file_format.ONE_BAR_WRITTEN, self.text())
        await self.select_field(labels.MSG_EVERY_LABEL)
        await self.press(keybindings.PluginEditor.MORE)
        self.assertEqual(self.settings().get_every(), [time for time in file_format.TIME_CHOICES if time != file_format.ONE_BAR_WRITTEN][0])

    async def test_the_chords_field_shows_the_numerals_and_opens_the_chord_editor(self):
        self.assertIn(POP_NUMERALS, self.text())
        await self.select_field(labels.MSG_CHORDS_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChordsEditor)

    async def test_a_progression_with_no_chords_written_has_one_chord_that_moves_nothing(self):
        await self.select_field(chords_strings.MSG_MODE_LABEL)
        await self.press(keybindings.PluginEditor.LESS)
        self.assertEqual(self.settings().get_chords(), [1, 5, 6, 4])
        fresh = chords_model.ChordsSettings.new()
        self.assertEqual(fresh.get_chords(), [limits.MIN_PROGRESSION_DEGREE])


class TestFollowProgressionMode(ChordsPageTest):
    """In Follow Progression mode, Chords from picks a track of the current song, (none) first, and follows its renames."""

    NAME = ui_testing.FOLLOWS

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.select_field(labels.MSG_CHORDS_FROM_LABEL)

    def followed(self):
        return self.settings().get_chords_from()

    async def test_the_track_is_picked_from_the_songs_tracks_with_none_first(self):
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, [marks.MSG_NONE_SHOWN, ui_testing.DRUMS, ui_testing.LEAD])
        await self.press(Key.UP, Key.ENTER)
        self.assertEqual(self.followed(), ui_testing.DRUMS)
        await self.press(keybindings.PluginEditor.CLEAR)
        self.assertIsNone(self.followed())

    async def test_renaming_the_track_followed_renames_it_here(self):
        self.document.rename_named(section=Section.TRACKS, old=ui_testing.LEAD, new=NEW_ONE)
        self.assertEqual(self.followed(), NEW_ONE)

    async def test_a_track_the_song_lacks_is_still_offered_so_that_it_is_kept(self):
        generator = self.document.generator(section=chords_plugin.SECTION, name=ui_testing.FOLLOWS)
        self.document.change_set(generator.set_setting, name=ChordsSetting.CHORDS_FROM, value=GONE)
        self.app.screen.draw()
        await self.press(Key.ENTER)
        self.assertIn(GONE, self.app.screen.options)
