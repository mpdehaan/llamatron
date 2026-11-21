# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The File/Global page: the set's settings, saving, protection, and a new set."""

from fractions import Fraction
import os
from unittest import mock

from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.dialogs.confirm_dialog import ConfirmDialog
from llamatron.interface.tracker.dialogs.message_dialog import MessageDialog
from llamatron.interface.tracker.dialogs.prompt_dialog import PromptDialog
from llamatron.interface.tracker.document import Document
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.pattern.pattern_editor import PatternEditor
from llamatron.interface.tracker.screens.set.open_page import OpenPage
from llamatron.model.file import version
from llamatron.model.objects import setlist as setlist_values
from llamatron.model.schema import defaults, file_format
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import errors, labels as labels_text, legends, marks, messages, names
from tests.support import ui_testing
from tests.support.ui_testing import key_name, key_of, UITest

SET_FILE = 'my_set.yml'
# A file name the prompt test changes into another by moving the cursor.
FOO_YML = 'foo.yml'
FOO2_YML = 'foo2.yml'
YML_SUFFIX = '.yml'
EXPORT = 'my_set_untitled'
OTHER_TEMPO = 99
RAIN_ON_THE_BRIDGE = 'Rain on the Bridge'
TITLE = 'Title'
AUTHOR = 'Author'
SOMEONE = 'Someone'
STEP_SIZE = 'Step size'
WRITE_TEXT = 'w'
KEEP = 'keep'
EXIT = 'exit'


class TestFilePage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.FILE)

    async def test_save_and_open_buttons_come_after_a_blank_line_and_do_what_their_keys_do(self):
        labels = [field.label for field in self.app.screen.fields()]
        self.assertEqual(labels[-2:], [labels_text.PageName.SAVE, labels_text.PageName.OPEN])
        self.assert_buttons_come_last_after_a_blank_line()
        await self.select_field(labels_text.PageName.SAVE)
        self.assertIn(key_name(keybindings.Page.SAVE), self.text())
        self.assertIn(key_name(keybindings.Page.OPEN_SET), self.text())
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, PromptDialog)
        await self.press(Key.ESCAPE)
        await self.select_field(labels_text.PageName.OPEN)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, OpenPage)

    async def test_the_loose_settings_come_alphabetically_and_title_and_author_start_blank(self):
        # The loose settings alphabetically, then the Notes & Octaves and Visualizers sections.
        labels = [field.label for field in self.app.screen.fields()]
        self.assertEqual(labels[:6], [AUTHOR, labels_text.MSG_DEFAULT_FOLLOW_ACTION_LABEL, labels_text.MSG_DESCRIPTION_LABEL, labels_text.MSG_NOTES_LABEL, labels_text.MSG_PROTECTED_LABEL, TITLE])
        self.assertEqual(self.document.get_setlist().get_title(), setlist_values.NO_TEXT)
        await self.select_field(TITLE)
        await self.press(Key.ENTER)
        await self.type('Rain on the Bridge')
        await self.press(Key.ENTER)
        await self.select_field(AUTHOR)
        await self.press(Key.ENTER)
        await self.type('Someone')
        await self.press(Key.ENTER)
        setlist = self.document.get_setlist()
        self.assertEqual((setlist.get_title(), setlist.get_author()), (RAIN_ON_THE_BRIDGE, SOMEONE))
        self.document.save(path='song.yml')
        with open('song.yml') as file:
            self.assertTrue(file.read().startswith(f'version: {version.VERSION}\ntitle: Rain on the Bridge\nauthor: Someone\n'))
        self.assertEqual(Document.load('song.yml').get_setlist().get_title(), RAIN_ON_THE_BRIDGE)
        await self.press(Key.BACKSPACE)
        self.assertEqual(self.document.get_setlist().get_author(), setlist_values.NO_TEXT)

    async def test_step_size_offers_only_the_allowed_values(self):
        await self.select_field(STEP_SIZE)
        await self.press(key_of(binding=keybindings.FilePage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.document.get_setlist().get_step_size(), Fraction(1, 8))
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, file_format.STEP_SIZE_CHOICES)

    async def test_the_notes_say_where_the_file_and_the_exports_are(self):
        text = self.text()
        self.assertIn('not saved yet', text)
        self.assertIn(marks.MSG_EXPORTS_AFTER_SAVING, text)
        self.assertIn(marks.MSG_NOT_SET, text)
        self.document.save(path=SET_FILE)
        await self.press(Key.ESCAPE, keybindings.MainPage.FILE)
        self.assertIn(EXPORT, self.text())

    async def test_the_prompt_cursor_moves_with_the_arrows_and_types_and_erases_where_it_is(self):
        await self.press(keybindings.FilePage.SAVE_AS)
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.app.screen.value = ''
        await self.type(FOO_YML)
        # Back over .yml, type the 2, erase the o before it and type it again: foo.yml becomes foo2.yml.
        await self.press(*([Key.LEFT] * len(YML_SUFFIX)))
        await self.type('2')
        await self.press(Key.BACKSPACE, Key.BACKSPACE)
        self.assertEqual(self.app.screen.value, 'fo.yml')
        await self.type('o2')
        self.assertEqual(self.app.screen.value, FOO2_YML)
        # Moving past either end stops there, and erasing at the start erases nothing.
        await self.press(*([Key.RIGHT] * (len(FOO2_YML) + 1)))
        self.assertEqual(self.app.screen.cursor(), len(FOO2_YML))
        await self.press(*([Key.LEFT] * (len(FOO2_YML) + 1)))
        self.assertEqual(self.app.screen.cursor(), 0)
        await self.press(Key.BACKSPACE)
        self.assertEqual(self.app.screen.value, FOO2_YML)
        await self.press(Key.ENTER)
        self.assertEqual(self.document.get_path(), FOO2_YML)

    async def test_save_as_then_save(self):
        await self.press(keybindings.FilePage.SAVE_AS)
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.app.screen.value = ''
        await self.type('tune')
        await self.press(Key.ENTER)
        self.assertTrue(os.path.exists('tune.yml'))
        self.assertEqual(self.document.get_path(), 'tune.yml')
        self.assertFalse(self.document.is_dirty())
        await self.select_field(STEP_SIZE)
        await self.press(key_of(binding=keybindings.FilePage.MORE, key=Key.RIGHT_BRACKET))
        self.assertTrue(self.document.is_dirty())
        with open('tune.yml') as file:
            before = file.read()
        await self.press(Key.CTRL_S)
        with open('tune.yml') as file:
            self.assertNotEqual(file.read(), before)
        self.assertFalse(self.document.is_dirty())

    async def test_a_protected_set_offers_a_copy_and_the_file_page_turns_protection_off(self):
        self.assertFalse(self.document.get_setlist().is_protected())
        await self.select_field(labels_text.MSG_PROTECTED_LABEL)
        self.assertIn(ui_testing.KEY_SHOWN.format(label=legends.KeyName.SPACE_ENTER), self.text())
        await self.press(Key.ENTER)
        self.assertTrue(self.document.get_setlist().is_protected())
        # Space toggles too, like ENTER.
        await self.press(Key.SPACE)
        self.assertFalse(self.document.get_setlist().is_protected())
        await self.press(Key.SPACE)
        self.assertTrue(self.document.get_setlist().is_protected())
        self.document.save(path='demo.yml')
        self.document.change_set(self.document.song().set_tempo, OTHER_TEMPO)
        await self.press(Key.CTRL_S)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn(messages.MSG_PROTECTED_TITLE, self.text())
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.app.screen.value = 'copy.yml'
        await self.press(Key.ENTER)
        self.assertNotEqual(Document.load('demo.yml').song().get_tempo(), OTHER_TEMPO)
        self.assertEqual(Document.load('copy.yml').song().get_tempo(), OTHER_TEMPO)
        self.assertFalse(Document.load('copy.yml').get_setlist().is_protected())
        self.assertEqual(self.document.get_path(), 'copy.yml')
        self.assertFalse(self.document.is_dirty())
        # Saying no leaves everything as it was. Protecting a set is kept by saving it to a new file.
        self.document.change_set(self.document.get_setlist().set_protected, True)
        self.document.save(path='second.yml')
        self.document.change_set(self.document.song().set_tempo, OTHER_TEMPO + 1)
        await self.press(Key.CTRL_S, keybindings.ConfirmDialog.NO)
        self.assertTrue(self.document.is_dirty())
        self.assertEqual(Document.load('second.yml').song().get_tempo(), OTHER_TEMPO)
        # Turning protection off on the File page lets Ctrl+S write the file again.
        await self.select_field(labels_text.MSG_PROTECTED_LABEL)
        await self.press(Key.ENTER, Key.CTRL_S)
        self.assertFalse(self.document.is_dirty())
        self.assertEqual(Document.load('second.yml').song().get_tempo(), OTHER_TEMPO + 1)

    async def test_saving_a_protected_set_under_its_own_name_is_refused_in_a_dialog(self):
        self.document.change_set(self.document.get_setlist().set_protected, True)
        self.document.save(path='demo.yml')
        # Unchanged, a protected set still gets the dialog rather than the status line.
        await self.press(Key.CTRL_S)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn(messages.MSG_PROTECTED_TITLE, self.text())
        await self.press(keybindings.ConfirmDialog.NO)
        before = os.stat('demo.yml').st_mtime_ns
        await self.press(keybindings.FilePage.SAVE_AS)
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.assertEqual(self.app.screen.value, 'demo.yml')
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(messages.MSG_PROTECTED_TITLE, self.text())
        await self.press(Key.ENTER)
        self.assertEqual(os.stat('demo.yml').st_mtime_ns, before)
        self.assertEqual(self.document.get_path(), 'demo.yml')

    async def test_saving_an_unchanged_set_writes_nothing_and_says_so(self):
        await self.press(keybindings.FilePage.SAVE_AS)
        self.app.screen.value = 'tune.yml'
        await self.press(Key.ENTER)
        before = os.stat('tune.yml').st_mtime_ns
        self.document.changed()
        await self.press(Key.CTRL_S)
        self.assertEqual(os.stat('tune.yml').st_mtime_ns, before)
        self.assertIn(messages.MSG_FILE_UNCHANGED.format(path='tune.yml'), self.text())
        self.assertFalse(self.document.is_dirty())

    async def test_saving_over_a_file_changed_elsewhere_asks_first(self):
        await self.press(keybindings.FilePage.SAVE_AS)
        self.app.screen.value = 'tune.yml'
        await self.press(Key.ENTER)
        other = Document.load('tune.yml')
        other.change_set(other.song().set_tempo, OTHER_TEMPO)
        other.save()
        await self.select_field(STEP_SIZE)
        await self.press(keybindings.FilePage.MORE)
        self.assertTrue(self.document.is_dirty())
        await self.press(Key.CTRL_S)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn(messages.MSG_FILE_CHANGED_ELSEWHERE_TITLE, self.text())
        await self.press(keybindings.ConfirmDialog.NO)
        self.assertEqual(Document.load('tune.yml').song().get_tempo(), OTHER_TEMPO)
        await self.press(Key.CTRL_S, keybindings.ConfirmDialog.YES)
        self.assertNotEqual(Document.load('tune.yml').song().get_tempo(), OTHER_TEMPO)
        self.assertFalse(self.document.is_dirty())

    async def test_save_works_from_any_page(self):
        await self.press(Key.ESCAPE, keybindings.MainPage.PATTERNS, Key.ENTER, Key.CTRL_S)
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.app.screen.value = ''
        await self.type('tune')
        await self.press(Key.ENTER)
        self.assertTrue(os.path.exists('tune.yml'))
        self.assertIsInstance(self.app.screen, PatternEditor)

    async def test_save_as_asks_before_replacing_another_file(self):
        with open('taken.yml', WRITE_TEXT) as file:
            file.write(KEEP)
        await self.press(keybindings.FilePage.SAVE_AS)
        self.app.screen.value = 'taken.yml'
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.NO)
        with open('taken.yml') as file:
            self.assertEqual(file.read(), KEEP)

    async def test_new_asks_if_there_are_unsaved_changes(self):
        self.document.changed()
        await self.press(keybindings.FilePage.NEW)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertEqual(self.app.get_document().song().get_pattern_names(), [names.MSG_NEW_PATTERN_NAME.format(number=defaults.FIRST_NUMBER)])
        self.assertEqual(self.app.get_document().song().get_scale_name(), setlist_values.DEFAULT_SCALE)
        self.assertEqual(self.app.get_document().song_names(), [names.MSG_DEFAULT_SONG_NAME])


class TestFilePageEdges(UITest):

    async def test_saving_a_new_set_asks_for_a_name_and_an_empty_one_does_nothing(self):
        await self.press(Key.CTRL_S)
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.app.screen.value = '  '
        await self.press(Key.ENTER)
        self.assertIsNone(self.document.get_path())

    async def test_quitting_can_save_first_and_asks_where(self):
        self.document.changed()
        with mock.patch.object(self.app, EXIT) as leave:
            await self.press(keybindings.MainPage.QUIT, keybindings.QuitDialog.SAVE)
            self.assertIsInstance(self.app.screen, PromptDialog)
            self.app.screen.value = 'tune.yml'
            await self.press(Key.ENTER)
            self.assertTrue(os.path.exists('tune.yml'))
            leave.assert_called_once()

    async def test_a_save_that_fails_is_explained(self):
        os.mkdir('taken.yml')
        await self.press(keybindings.MainPage.FILE, keybindings.FilePage.SAVE_AS)
        self.app.screen.value = 'taken.yml'
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(errors.ERR_CANT_SAVE_TITLE, self.text())

    async def test_new_and_load_ask_first_with_unsaved_changes(self):
        self.document.changed()
        await self.press(keybindings.MainPage.FILE, keybindings.FilePage.NEW)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(Key.ESCAPE, Key.CTRL_O)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertIsInstance(self.app.screen, OpenPage)

    async def test_choosing_a_scale_needs_one_first(self):
        self.document.change_set(self.document.song().set_scale_name, None)
        for name in self.document.song().get_scale_names():
            self.document.delete_named(section=Section.SCALES, name=name)
        await self.press(keybindings.MainPage.SONGS, Key.ENTER)
        await self.select_field(labels_text.MSG_SCALE_LABEL)
        await self.press(Key.ENTER)
        self.assertIn(errors.ERR_ADD_A_SCALE_FIRST, self.text())
