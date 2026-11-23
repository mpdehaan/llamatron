# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Song page and the Songs page."""

from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.dialogs import dialog
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.dialogs.confirm_dialog import ConfirmDialog
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.set.song_page import SongPage
from llamatron.interface.tracker.screens.set.songs_page import SongsPage
from llamatron.model.schema import defaults, file_format, genres
from llamatron.model.schema.file_format import LiveResponsiveness, Section, SongSetting
from llamatron.model.schema.genres import subgenres_of, variants_of
from llamatron.model.values import time_signature
from llamatron.user_strings import errors, labels as labels_text, legends, marks, names as names_text
from tests.support import ui_testing
from tests.support.ui_testing import key_name, key_of, UITest

# The label a seed field had, before every play and export became a new take.
SEED_LABEL = 'Seed'

A_GENRE_WITH_VARIANTS = 'Rock'
A_SUBGENRE_WITH_VARIANTS = 'hard rock'
# Two instruments a test adds, in the order a picker lists them, and what the first is renamed to.
NEW_LINE = '\n'
KEYS_INSTRUMENT = 'keys'
ORGAN_INSTRUMENT = 'organ'
RENAMED_INSTRUMENT = 'piano'
SET_FILE = 'my_set.yml'
TUNE = 'tune'
LEAD = 'lead'
DRUMS = 'drums'
FIRST_TRACK = names_text.MSG_NEW_TRACK_NAME.format(number=1)
OTHER = 'other'
NOT_AN_INTEGER = 'is not an integer'
SECOND_SONG = 'second'
# A time signature the Song page's list doesn't offer, and text that isn't one.
SEVEN_EIGHT = '7/8'
NOT_A_SIGNATURE = '4/5'
TEMPO = 'Tempo'


class TestSongPage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        # ENTER on the Songs page opens the current song's settings, starting on Name.
        await self.press(keybindings.MainPage.SONGS, Key.ENTER)

    async def test_it_holds_the_song_settings_and_names_the_song(self):
        self.assertIsInstance(self.app.screen, SongPage)
        labels = [field.label for field in self.app.screen.fields()]
        self.assertEqual(labels, [labels_text.MSG_NAME_LABEL, TEMPO, labels_text.MSG_TIME_SIGNATURE_LABEL, labels_text.MSG_ENTRY_SIZE_LABEL, labels_text.MSG_SCALE_LABEL, labels_text.MSG_GROOVE_LABEL, labels_text.MSG_GENRE_LABEL, labels_text.MSG_SUBGENRE_LABEL, labels_text.MSG_VARIANT_LABEL, labels_text.MSG_LIVE_RESPONSIVENESS_LABEL, labels_text.MSG_PREVIEW_INSTRUMENT_LABEL, labels_text.MSG_VISUALIZER_LABEL, labels_text.PageName.EXPORT])
        self.assertIn(names_text.MSG_DEFAULT_SONG_NAME, self.text())
        self.assert_buttons_come_last_after_a_blank_line()

    async def test_the_preview_instrument_is_one_of_the_sets_and_follows_a_rename_and_bksp_clears_it(self):
        song = self.document.song()
        self.assertIsNone(song.get_preview_instrument_name())
        self.assertIn(labels_text.MSG_PREVIEW_INSTRUMENT_UNSET, self.text())
        self.document.add_instrument(ORGAN_INSTRUMENT)
        self.document.add_instrument(KEYS_INSTRUMENT)
        await self.select_field(labels_text.MSG_PREVIEW_INSTRUMENT_LABEL)
        # ] steps through the instruments by name and stops at the last, and [ goes back to none and stops there.
        await self.press(keybindings.SongPage.MORE)
        self.assertEqual(song.get_preview_instrument_name(), KEYS_INSTRUMENT)
        await self.press(keybindings.SongPage.MORE, keybindings.SongPage.MORE)
        self.assertEqual(song.get_preview_instrument_name(), ORGAN_INSTRUMENT)
        await self.press(*[keybindings.SongPage.LESS] * 3)
        self.assertIsNone(song.get_preview_instrument_name())
        # ENTER picks from the list, where the pattern's own track comes first.
        await self.press(Key.ENTER)
        self.assertIn(labels_text.MSG_PREVIEW_INSTRUMENT_UNSET, str(self.app.screen.query_one(dialog.DIALOG_VIEW_SELECTOR).render()))
        await self.press(Key.DOWN, Key.ENTER)
        self.assertEqual(song.get_preview_instrument_name(), KEYS_INSTRUMENT)
        # The song is a use of the instrument, and a rename is followed.
        self.assertTrue(self.document.uses(section=Section.INSTRUMENTS, name=KEYS_INSTRUMENT))
        self.document.rename_named(section=Section.INSTRUMENTS, old=KEYS_INSTRUMENT, new=RENAMED_INSTRUMENT)
        self.assertEqual(song.get_preview_instrument_name(), RENAMED_INSTRUMENT)
        await self.press(keybindings.FieldPage.CLEAR)
        self.assertIsNone(song.get_preview_instrument_name())

    def shown_on(self, label):
        """The line of the page that shows a field, by the field's label."""
        return next(line for line in self.text().split(NEW_LINE) if label in line.split())

    async def test_the_genre_is_undefined_until_chosen_from_the_genres_and_bksp_clears_it(self):
        song = self.document.song()
        for label in (labels_text.MSG_GENRE_LABEL, labels_text.MSG_SUBGENRE_LABEL, labels_text.MSG_VARIANT_LABEL):
            self.assertIn(marks.MSG_UNDEFINED_SHOWN, self.shown_on(label))
        await self.select_field(labels_text.MSG_GENRE_LABEL)
        await self.press(key_of(binding=keybindings.FieldPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(song.get_genre(), genres.GENRES[0])
        await self.press(Key.ENTER)
        await self.type(genres.MASHUP)
        await self.press(Key.ENTER)
        self.assertEqual(song.get_genre(), genres.MASHUP)
        self.assertIn(genres.MASHUP, self.shown_on(labels_text.MSG_GENRE_LABEL))
        await self.press(keybindings.FieldPage.CLEAR)
        self.assertIsNone(song.get_genre())

    async def test_the_subgenre_is_one_of_the_genres_and_the_variant_one_of_the_subgenres(self):
        song = self.document.song()
        await self.select_field(labels_text.MSG_SUBGENRE_LABEL)
        await self.press(key_of(binding=keybindings.FieldPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertIsNone(song.get_subgenre())
        self.document.change_set(self.document.song().set_genre, A_GENRE_WITH_VARIANTS)
        await self.press(Key.ENTER)
        await self.type(A_SUBGENRE_WITH_VARIANTS)
        await self.press(Key.ENTER)
        self.assertEqual(song.get_subgenre(), A_SUBGENRE_WITH_VARIANTS)
        await self.select_field(labels_text.MSG_VARIANT_LABEL)
        await self.press(key_of(binding=keybindings.FieldPage.MORE, key=Key.RIGHT_BRACKET))
        variants = variants_of(genre=A_GENRE_WITH_VARIANTS, subgenre=A_SUBGENRE_WITH_VARIANTS)
        self.assertEqual(song.get_variant(), variants[0])
        self.assertIn(variants[0], self.shown_on(labels_text.MSG_VARIANT_LABEL))
        await self.select_field(labels_text.MSG_GENRE_LABEL)
        await self.press(Key.ENTER)
        await self.type(genres.MASHUP)
        await self.press(Key.ENTER)
        self.assertEqual((song.get_subgenre(), song.get_variant()), (None, None))
        await self.select_field(labels_text.MSG_SUBGENRE_LABEL)
        await self.press(Key.ENTER)
        for subgenre in subgenres_of(genres.MASHUP):
            self.assertIn(subgenre, self.text())

    async def test_live_response_steps_through_its_three_choices_from_next_bar(self):
        await self.select_field(labels_text.MSG_LIVE_RESPONSIVENESS_LABEL)
        self.assertEqual(self.document.song().get_live_responsiveness(), LiveResponsiveness.NEXT_BAR)
        self.assertIn(labels_text.MSG_LIVE_RESPONSIVENESS_NAMES[LiveResponsiveness.NEXT_BAR], self.text())
        await self.press(keybindings.FieldPage.MORE)
        self.assertEqual(self.document.song().get_live_responsiveness(), LiveResponsiveness.CLIP_RESTART)
        await self.press(keybindings.FieldPage.MORE)
        self.assertEqual(self.document.song().get_live_responsiveness(), LiveResponsiveness.ASAP)
        self.assertEqual(self.document.song().to_data()[SongSetting.LIVE_RESPONSIVENESS], LiveResponsiveness.ASAP)

    async def test_enter_on_the_name_renames_the_song_and_the_crumb_follows(self):
        await self.press(Key.ENTER)
        self.app.screen.value = SECOND_SONG
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song_names(), [SECOND_SONG])
        self.assertEqual(self.document.get_current_song_name(), SECOND_SONG)
        self.assertEqual(self.app.screen.crumbs, (labels_text.Crumb.SONGS, SECOND_SONG))
        self.assertTrue(self.document.is_dirty())

    async def test_a_name_another_song_has_is_refused(self):
        self.document.add_song(SECOND_SONG)
        self.document.select_song(names_text.MSG_DEFAULT_SONG_NAME)
        await self.press(Key.ENTER)
        self.app.screen.value = SECOND_SONG
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song_names(), [names_text.MSG_DEFAULT_SONG_NAME, SECOND_SONG])
        self.assertIn(errors.ERR_NAME_IN_USE.format(name=SECOND_SONG), self.text())

    async def test_the_export_row_asks_which_kind_like_control_x(self):
        self.document.save(path=SET_FILE)
        await self.select_field(labels_text.PageName.EXPORT)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, labels_text.MSG_EXPORT_CHOICES)
        self.assertIn(names_text.MSG_DEFAULT_SONG_NAME, self.text())

    async def test_the_time_signature_steps_through_common_ones_and_enter_types_any(self):
        await self.select_field(labels_text.MSG_TIME_SIGNATURE_LABEL)
        self.assertEqual(self.document.song().get_time_signature().to_text(), defaults.DEFAULT_TIME_SIGNATURE)
        await self.press(key_of(binding=keybindings.SongPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.document.song().get_time_signature().to_text(), file_format.TIME_SIGNATURE_CHOICES[file_format.TIME_SIGNATURE_CHOICES.index(defaults.DEFAULT_TIME_SIGNATURE) + 1])
        await self.press(keybindings.FieldPage.LESS, keybindings.FieldPage.LESS)
        self.assertEqual(self.document.song().get_time_signature().to_text(), file_format.TIME_SIGNATURE_CHOICES[file_format.TIME_SIGNATURE_CHOICES.index(defaults.DEFAULT_TIME_SIGNATURE) - 1])
        await self.press(Key.ENTER)
        self.app.screen.value = SEVEN_EIGHT
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_time_signature().to_text(), SEVEN_EIGHT)
        self.assertIn(SEVEN_EIGHT, self.text())
        self.assertTrue(self.document.is_dirty())

    async def test_the_entry_size_steps_through_the_step_sizes_and_backspace_means_one_step(self):
        await self.select_field(labels_text.MSG_ENTRY_SIZE_LABEL)
        self.assertIsNone(self.document.song().get_entry_size())
        self.assertIn(marks.MSG_ONE_STEP_SHOWN, self.text())
        await self.press(key_of(binding=keybindings.SongPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.document.song().get_written_entry_size(), file_format.STEP_SIZE_CHOICES[0])
        await self.press(keybindings.FieldPage.LESS)
        self.assertIsNone(self.document.song().get_written_entry_size())
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, [marks.MSG_ONE_STEP_SHOWN, *file_format.STEP_SIZE_CHOICES])
        await self.press(Key.DOWN, Key.DOWN, Key.DOWN, Key.ENTER)
        self.assertEqual(self.document.song().get_written_entry_size(), file_format.STEP_SIZE_CHOICES[2])
        self.assertIn(file_format.STEP_SIZE_CHOICES[2], self.text())
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.document.song().get_written_entry_size())
        self.assertTrue(self.document.is_dirty())

    async def test_a_time_signature_that_is_not_one_is_refused(self):
        await self.select_field(labels_text.MSG_TIME_SIGNATURE_LABEL)
        await self.press(Key.ENTER)
        self.app.screen.value = NOT_A_SIGNATURE
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_time_signature().to_text(), defaults.DEFAULT_TIME_SIGNATURE)
        self.assertIn(errors.ERR_TYPED_NOT_A_TIME_SIGNATURE.format(text=NOT_A_SIGNATURE, lowest=time_signature.MIN_BEATS, highest=time_signature.MAX_BEATS, units=time_signature.UNITS_LISTED), self.text())

    async def test_plus_and_minus_change_the_tempo(self):
        await self.select_field(TEMPO)
        await self.press(key_of(binding=keybindings.SongPage.MORE, key=Key.PLUS), key_of(binding=keybindings.SongPage.MORE, key=Key.PLUS), key_of(binding=keybindings.SongPage.LESS, key=Key.MINUS))
        self.assertEqual(self.document.song().get_tempo(), 121)
        self.assertTrue(self.document.is_dirty())

    async def test_the_brackets_change_the_tempo_the_legend_names_them_and_left_and_right_step_nothing(self):
        """A setting's legend says [ and ], with the older + and - working beside them; Left and Right only ever move."""
        await self.select_field(TEMPO)
        before = self.document.song().get_tempo()
        await self.press(key_of(binding=keybindings.SongPage.MORE, key=Key.RIGHT_BRACKET), key_of(binding=keybindings.SongPage.MORE, key=Key.RIGHT_BRACKET), key_of(binding=keybindings.SongPage.LESS, key=Key.LEFT_BRACKET))
        self.assertEqual(self.document.song().get_tempo(), before + 1)
        await self.press(Key.RIGHT, Key.LEFT, Key.LEFT)
        self.assertEqual(self.document.song().get_tempo(), before + 1)
        self.assertIn(ui_testing.KEY_SHOWN.format(label=key_name(keybindings.FieldPage.MORE)) + legends.MSG_LEGEND_WHAT.format(what=legends.What.MORE), self.text())
        self.assertIn(ui_testing.KEY_SHOWN.format(label=key_name(keybindings.FieldPage.LESS)) + legends.MSG_LEGEND_WHAT.format(what=legends.What.LESS), self.text())
        # The legend names [ dec and ] inc, as everywhere a value steps.
        self.assertEqual((legends.KeyName.RIGHT_BRACKET, legends.KeyName.LEFT_BRACKET), (key_name(keybindings.FieldPage.MORE), key_name(keybindings.FieldPage.LESS)))

    async def test_typing_a_tempo(self):
        await self.select_field(TEMPO)
        await self.press(Key.ENTER, Key.BACKSPACE, Key.BACKSPACE, Key.BACKSPACE)
        await self.type('90')
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_tempo(), 90)

    async def test_nonsense_is_refused(self):
        await self.select_field(TEMPO)
        await self.press(Key.ENTER, Key.BACKSPACE, Key.BACKSPACE, Key.BACKSPACE)
        await self.type('xx')
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_tempo(), 120)
        self.assertIn(NOT_AN_INTEGER, self.text())

    async def test_a_song_has_no_seed_since_every_play_and_export_is_a_new_take(self):
        self.assertNotIn(SEED_LABEL, self.text())

    async def test_scale_can_be_none(self):
        await self.select_field(labels_text.MSG_SCALE_LABEL)
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.document.song().get_scale_name())


class TestSongsPage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.SONGS)

    def names(self):
        return [row[0] for row in self.app.screen.rows()]

    async def test_lists_the_songs_with_the_current_one_marked(self):
        self.assertIsInstance(self.app.screen, SongsPage)
        self.assertEqual(self.names(), [names_text.MSG_DEFAULT_SONG_NAME])
        self.assertIn('●', self.text())

    async def test_adding_a_song_makes_it_current_and_the_header_says_so(self):
        await self.press(keybindings.SongsPage.ADD)
        await self.type(SECOND_SONG)
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song_names(), [names_text.MSG_DEFAULT_SONG_NAME, SECOND_SONG])
        self.assertEqual(self.document.get_current_song_name(), SECOND_SONG)
        self.assertEqual(self.document.song().get_track_names(), [FIRST_TRACK])
        await self.press(Key.ESCAPE, keybindings.MainPage.PATTERNS)
        self.assertIn(labels_text.MSG_SONG_CRUMB.format(song=SECOND_SONG), self.song_line())

    async def test_space_makes_a_song_current_and_enter_opens_its_settings(self):
        self.document.add_song(SECOND_SONG)
        self.document.select_song(names_text.MSG_DEFAULT_SONG_NAME)
        await self.press(Key.DOWN, Key.SPACE)
        self.assertEqual(self.document.get_current_song_name(), SECOND_SONG)
        await self.press(Key.UP, Key.ENTER)
        self.assertIsInstance(self.app.screen, SongPage)
        self.assertEqual(self.document.get_current_song_name(), names_text.MSG_DEFAULT_SONG_NAME)

    async def test_copying_and_renaming(self):
        await self.press(keybindings.SongsPage.COPY)
        self.assertEqual(len(self.document.song_names()), 2)
        copy = self.document.song_names()[1]
        self.assertEqual(self.document.get_setlist().get_song(copy).get_track_names(), [LEAD, DRUMS])
        await self.press(keybindings.SongsPage.RENAME)
        self.app.screen.value = SECOND_SONG
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song_names(), [names_text.MSG_DEFAULT_SONG_NAME, SECOND_SONG])

    async def test_the_last_song_cannot_be_deleted(self):
        await self.press(Key.BACKSPACE)
        self.assertEqual(self.document.song_names(), [names_text.MSG_DEFAULT_SONG_NAME])
        self.assertIn('at least one song', self.text())

    async def test_deleting_the_current_song_moves_to_another(self):
        self.document.add_song(SECOND_SONG)
        await self.press(Key.DOWN, Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertEqual(self.document.song_names(), [names_text.MSG_DEFAULT_SONG_NAME])
        self.assertEqual(self.document.get_current_song_name(), names_text.MSG_DEFAULT_SONG_NAME)

    async def test_songs_share_the_patterns_and_have_their_own_tracks(self):
        self.document.add_song(SECOND_SONG)
        self.assertEqual(self.document.get_setlist().get_pattern_names(), [TUNE, ui_testing.BEAT, OTHER])
        self.assertEqual(self.document.song().get_track_names(), [FIRST_TRACK])
        self.document.select_song(names_text.MSG_DEFAULT_SONG_NAME)
        self.assertEqual(self.document.song().get_track_names(), [LEAD, DRUMS])
