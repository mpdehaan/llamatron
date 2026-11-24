# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Exporting from the tracker."""

import os

from llamatron.exporters import exports
from llamatron.exporters.exports import earlier_export, ExportKind, PacketPage, pdf_options, pdf_path, PdfKind, PrintedPart, shown_export_path
from llamatron.interface.pages import uses
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.dialogs import export_dialog
from llamatron.interface.tracker.dialogs.confirm_dialog import ConfirmDialog
from llamatron.interface.tracker.dialogs.export_dialog import ExportDialog
from llamatron.interface.tracker.dialogs.message_dialog import MessageDialog
from llamatron.interface.tracker.dialogs.prompt_dialog import PromptDialog
from llamatron.interface.tracker.document import Document
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.pattern.pattern_editor import PatternEditor
from llamatron.interface.tracker.screens.set.main_page import MainPage
from llamatron.interface.tracker.screens.set.pdf_export_page import PdfExportPage
from llamatron.model.objects.setlist import Setlist
from llamatron.model.schema.file_format import ClipSlotSetting
from llamatron.user_strings import errors, labels, messages, names
from tests.support import ui_testing
from tests.support.ui_testing import fixed_text, UITest

SET_FILE = 'my_set.yml'
# A set file name a test saves to when SET_FILE is taken already, and what its untitled song's Live set is then called.
OTHER_SET_FILE = 'other_set.yml'
OTHER_LIVE_SET = 'other_set_untitled.als'
EXPORT = 'my_set_untitled'
LIVE_SET = EXPORT + '.als'
TUNE = 'tune'
LEAD = 'lead'
OVERWRITE = 'overwrite'
SECOND_SONG = 'second'
# Scenes named for the loop errors dialog, and how many scenes make it say 'and 1 more'.
VERSE = 'verse'
CHORUS = 'chorus'
ONE_MORE_THAN_SHOWN = uses.LOOP_ERRORS_SHOWN + 1
TEMPO = 'Tempo'
# The PDF page's test set, found before the test moves into its own folder.
PRINTED_SET = os.path.abspath(os.path.join('tests', 'data', 'pdf_export', 'printed.yml'))
PRINTED_LEAD = 'lead'
PRINTED_KICK = 'kick'


def export_keys(kind):
    """Return the keys that choose a kind of export in the Export dialog: its category, and for MIDI its place in the flyout."""
    if kind in export_dialog.MIDI_KINDS:
        return [*[Key.DOWN] * export_dialog.CATEGORIES.index(export_dialog.MIDI), Key.ENTER, *[Key.DOWN] * export_dialog.MIDI_KINDS.index(kind), Key.ENTER]
    return [*[Key.DOWN] * export_dialog.CATEGORIES.index(kind), Key.ENTER]


class TestExporting(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.document.save(path=SET_FILE)

    async def export(self, kind):
        """Press X, pick a kind of export, from MIDI's flyout for a MIDI kind, and check the status line says where it went."""
        await self.press(Key.CTRL_X)
        self.assertIsInstance(self.app.screen, ExportDialog)
        self.assertEqual(self.app.screen.options, labels.MSG_EXPORT_CATEGORIES)
        await self.press(*export_keys(kind))
        self.assertNotIsInstance(self.app.screen, MessageDialog)
        self.assertIn(fixed_text(messages.MSG_EXPORTED), self.text())

    async def test_the_live_set_is_first_and_says_where_it_went_on_the_status_line(self):
        await self.press(Key.CTRL_X, Key.ENTER)
        self.assertNotIsInstance(self.app.screen, MessageDialog)
        self.assertIn(messages.MSG_EXPORTED.format(name=exports.EXPORT_LABELS[ExportKind.ABLETON], path=LIVE_SET), self.text())
        self.assertTrue(os.path.exists(LIVE_SET))

    async def test_an_unsaved_set_is_saved_first_and_then_exported(self):
        self.app.set_document(Document())
        await self.press(Key.CTRL_X)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn(messages.MSG_SAVE_BEFORE_EXPORT_TITLE, self.text())
        await self.press(*ui_testing.ANSWER_YES)
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.app.screen.value = ''
        await self.type(OTHER_SET_FILE)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ExportDialog)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, MainPage)
        self.assertIn(OTHER_LIVE_SET, self.text())
        self.assertTrue(os.path.exists(OTHER_LIVE_SET))

    async def test_declining_to_save_exports_nothing(self):
        self.app.set_document(Document())
        await self.press(Key.CTRL_X, ui_testing.ANSWER_NO)
        self.assertIsInstance(self.app.screen, MainPage)
        self.assertEqual(os.listdir(self.folder), [SET_FILE])

    async def test_writing_over_a_live_set_asks_only_the_first_time(self):
        await self.export(ExportKind.ABLETON)
        await self.press(Key.CTRL_X, Key.ENTER)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn(OVERWRITE, self.text().lower())
        self.assertIn(LIVE_SET, self.text())
        await self.press(*ui_testing.ANSWER_YES)
        self.assertIsInstance(self.app.screen, MainPage)
        self.assertIn(fixed_text(messages.MSG_EXPORTED), self.text())
        await self.export(ExportKind.ABLETON)
        self.assertIsInstance(self.app.screen, MainPage)

    async def test_midi_exports_never_ask(self):
        await self.export(ExportKind.MIDI_FILE)
        await self.export(ExportKind.MIDI_FILE)
        self.assertTrue(os.path.exists(shown_export_path(kind=ExportKind.MIDI_FILE, directory=self.folder, name=EXPORT)))

    async def test_stems_and_clips_too(self):
        await self.export(ExportKind.STEMS)
        self.assertTrue(earlier_export(kind=ExportKind.STEMS, directory=self.folder, name=EXPORT))
        await self.export(ExportKind.CLIP_TREE)
        self.assertTrue(earlier_export(kind=ExportKind.CLIP_TREE, directory=self.folder, name=EXPORT))
        self.assertEqual(earlier_export(kind=ExportKind.MIDI_FILE, directory=self.folder, name=EXPORT), [])

    async def test_x_can_be_cancelled_and_works_from_any_page(self):
        await self.press(Key.CTRL_X, Key.ESCAPE)
        self.assertEqual(os.listdir(self.folder), [SET_FILE])
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, Key.CTRL_X)
        self.assertIsInstance(self.app.screen, ExportDialog)
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, PatternEditor)

    async def test_exports_the_current_song_under_its_own_name(self):
        self.document.add_song(SECOND_SONG)
        self.document.add_track(LEAD)
        self.document.add_scene(index=0, name=VERSE)
        self.document.add_clip_slot(index=0, track=LEAD, pattern=TUNE)
        await self.export(ExportKind.ABLETON)
        self.assertTrue(os.path.exists(f'my_set_{SECOND_SONG}.als'))
        self.assertFalse(os.path.exists(LIVE_SET))

    async def test_changes_do_not_export_or_save_by_themselves(self):
        tempo = self.document.song().get_tempo()
        with open(SET_FILE) as file:
            saved = file.read()
        await self.press(keybindings.MainPage.SONGS, Key.ENTER)
        await self.select_field(TEMPO)
        await self.press(keybindings.SongPage.MORE, keybindings.SongPage.MORE)
        self.assertGreater(self.document.song().get_tempo(), tempo)
        self.assertTrue(self.document.is_dirty())
        self.assertEqual(os.listdir(self.folder), [SET_FILE])
        with open(SET_FILE) as file:
            self.assertEqual(file.read(), saved)

    def loop_every_clip_in_scene(self, *, index, name):
        """Name a scene and set its one clip to loop, so that the scene would never end."""
        self.document.change_set(self.document.song().get_scene(index).set_name, name)
        self.document.set_clip_slot_setting(index=index, track=LEAD, setting=ClipSlotSetting.LOOP, value=True)

    def dialog_words(self):
        """Return the dialog's own text as one line of words, since the page behind it shows through beside it."""
        return ' '.join(str(self.app.screen.query_one('#dialog-view').render()).replace('┃', ' ').split())

    async def test_every_clip_looping_is_a_popup_at_export_that_names_the_scenes(self):
        self.loop_every_clip_in_scene(index=0, name=VERSE)
        self.document.add_scene(index=1, name=CHORUS)
        self.document.add_clip_slot(index=1, track=LEAD, pattern=TUNE)
        self.loop_every_clip_in_scene(index=1, name=CHORUS)
        await self.press(Key.CTRL_X)
        self.assertIsInstance(self.app.screen, MessageDialog)
        words = self.dialog_words()
        self.assertIn(errors.ERR_LOOP_SCENES_TITLE, words)
        self.assertIn(errors.ERR_LOOP_SCENES_INTRO, words)
        self.assertIn(VERSE, words)
        self.assertIn(CHORUS, words)
        self.assertNotIn(errors.ERR_AND_MORE.format(count=1), words)
        await self.press(Key.ENTER)
        self.assertFalse(os.path.exists(LIVE_SET))

    async def test_the_loop_errors_dialog_lists_ten_scenes_and_counts_the_rest(self):
        for index in range(ONE_MORE_THAN_SHOWN):
            if index:
                self.document.add_scene(index=index, name=names.MSG_NUMBERED_NAME.format(base=VERSE, number=index))
                self.document.add_clip_slot(index=index, track=LEAD, pattern=TUNE)
            self.loop_every_clip_in_scene(index=index, name=names.MSG_NUMBERED_NAME.format(base=VERSE, number=index))
        await self.press(Key.CTRL_X)
        self.assertIsInstance(self.app.screen, MessageDialog)
        words = self.dialog_words()
        self.assertIn(names.MSG_NUMBERED_NAME.format(base=VERSE, number=uses.LOOP_ERRORS_SHOWN - 1), words)
        self.assertNotIn(names.MSG_NUMBERED_NAME.format(base=VERSE, number=uses.LOOP_ERRORS_SHOWN), words)
        self.assertIn(errors.ERR_AND_MORE.format(count=1), words)


class TestExportDialog(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.document.save(path=SET_FILE)

    async def test_midi_opens_a_flyout_of_its_kinds_that_esc_closes_alone(self):
        await self.press(Key.CTRL_X, *[Key.DOWN] * export_dialog.CATEGORIES.index(export_dialog.MIDI), Key.ENTER)
        self.assertTrue(self.app.screen.flyout_open)
        self.assertIn(labels.MSG_MIDI_EXPORT_CHOICES[0], self.text())
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, ExportDialog)
        self.assertFalse(self.app.screen.flyout_open)

    async def test_pdf_opens_the_pdf_page(self):
        await self.press(Key.CTRL_X, *export_keys(export_dialog.PDF))
        self.assertIsInstance(self.app.screen, PdfExportPage)


class TestPdfExportPage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        setlist = Setlist.read_file(PRINTED_SET)
        self.app.set_document(Document(setlist=setlist))
        self.document = self.app.get_document()
        self.document.save(path=SET_FILE)
        await self.press(Key.CTRL_X, *export_keys(export_dialog.PDF))

    async def test_each_track_starts_in_the_part_its_role_gives_and_export_writes_the_packet(self):
        page = self.app.screen
        self.assertEqual(page.parts[PRINTED_LEAD], PrintedPart.MELODY)
        self.assertEqual(page.parts[PRINTED_KICK], PrintedPart.LEFT_OUT)
        page.place = page.first_button_place()
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, MainPage)
        self.assertTrue(os.path.exists(pdf_path(directory=self.folder, name=self.document.export_name(), kind=PdfKind.PACKET)))

    async def test_nothing_ticked_says_why_above_the_dim_export_button_and_refuses(self):
        page = self.app.screen
        for place in range(len(pdf_options().packet_pages)):
            page.place = place
            await self.press(Key.SPACE)
        # The line above the dim Export button says why before it is pressed, and pressing it refuses.
        self.assertIn(errors.ERR_PDF_NOTHING_TICKED, self.text())
        page.place = page.first_button_place()
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, PdfExportPage)

    async def test_a_track_takes_the_column_under_the_cursor_and_the_choices_are_remembered(self):
        page = self.app.screen
        page.place = page.first_track_place()
        await self.press(Key.RIGHT, Key.RIGHT, Key.SPACE)
        self.assertEqual(page.parts[page.tracks[0].name], PrintedPart.LEFT_OUT)
        await self.press(Key.ESCAPE, Key.CTRL_X, *export_keys(export_dialog.PDF))
        self.assertEqual(self.app.screen.parts[page.tracks[0].name], PrintedPart.LEFT_OUT)

    async def test_the_chords_level_steps_with_the_brackets(self):
        page = self.app.screen
        page.place = page.level_place()
        await self.press(keybindings.PdfExportPage.LESS)
        self.assertEqual(page.level, pdf_options().chord_levels[0])

    async def test_with_no_chords_track_the_chord_pages_dim_and_the_piano_roll_alone_exports(self):
        page = self.app.screen
        for track in page.tracks:
            if page.parts[track.name] == PrintedPart.CHORDS:
                page.parts[track.name] = PrintedPart.LEFT_OUT
        chart = pdf_options().packet_pages.index(PacketPage.CHORD_CHART)
        page.place = chart
        await self.press(Key.SPACE)
        self.assertIn(errors.ERR_PDF_NEEDS_CHORDS, self.text())
        self.assertEqual(page.choices().packet_pages, (PacketPage.PIANO_ROLL,))
        page.place = page.first_button_place()
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, MainPage)
        self.assertTrue(os.path.exists(pdf_path(directory=self.folder, name=self.document.export_name(), kind=PdfKind.PACKET)))
