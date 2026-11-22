# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Undo and redo on every page: one test class per page, named Test<Page>Undo, and the rule that keeps it so.

Each class makes an edit on its page by pressing keys, undoes it with Ctrl+Z and redoes it with
Ctrl+Y, checking the set, the cursor and the status line, and where an undo can take away what
the page shows, checks that the tracker goes back to the page it came from. The last class checks
that every page has a test class of its own and an undo class here, so that a new page can't
arrive without either. The history itself is tested in test_tui_history.py.
"""

import importlib
import inspect
import os
import unittest

from llamatron.engine.generators import arp as arp_plugin
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.arrange.arrange_page import ArrangePage
from llamatron.interface.tracker.screens.arrange.scene_page import ScenePage
from llamatron.interface.tracker.screens.generators.generators_page import GeneratorsPage
from llamatron.interface.tracker.screens.pattern.pattern_editor import Munge, PatternEditor, Reconfigure
from llamatron.interface.tracker.screens.pattern.patterns_page import PatternsPage
from llamatron.interface.tracker.screens.set.instruments_page import InstrumentsPage
from llamatron.interface.tracker.screens.set.main_page import MainPage
from llamatron.interface.tracker.screens.set.notes_page import NotesPage
from llamatron.interface.tracker.screens.set.scale_page import ScalePage
from llamatron.interface.tracker.screens.set.song_page import SongPage
from llamatron.interface.tracker.screens.shared.offsets_editor import OffsetsEditor
from llamatron.interface.tracker.screens.shared.plugin_editor import PluginEditor
from llamatron.model.objects.named_scale import scale_type_name
from llamatron.model.objects.naming import default_scale_name, new_name
from llamatron.model.schema import defaults
from llamatron.model.schema.file_format import Row, Section, SongSetting
from llamatron.model.values.note import NoteName
from llamatron.model.values.scale import ScaleType
from llamatron.user_strings import labels, messages, names as names_text
from tests.support import ui_testing
from tests.support.pattern_editor_testing import munge
from tests.support.ui_testing import a_song, fixed_text, key_of, leaf_pages, UITest

# Names the tests give to what they add, and what they type.
SECOND_SONG = 'second'
RENAMED = 'renamed'
# Entry sizes the roll's picker offers, longer than the tune's 1/8 steps.
QUARTER = '1/4'
HALF = '1/2'
A_LINE = 'hi there'
ANOTHER_LINE = 'ok'
TWO_LETTERS = 'ab'
OTHER_FILE = 'other.yml'
# The pattern editor's Velocity row is this many rows below Degree, in the normal rows.
# Velocity's place among the editor's rows: the two pinned rows, then the Basics heading, #/b and Velocity.
VELOCITY_ROW = 4
# What typing these digits in turn makes, in one cell.
ONE_HUNDRED = ('1', '0', '0')
TWELVE = ('1', '2')
SEVEN = '7'
# How test classes are named after pages: TestSongPage tests it, and TestSongPageUndo tests undo on it.
TEST_PREFIX = 'Test'
TEST_MODULE_PREFIX = 'test_tui_'
# The package the text UI's test modules are in, this one.
TUI_TESTS_PACKAGE = 'tests.interface.tracker.'
PYTHON_SUFFIX = '.py'


class UndoTest(UITest):
    """Makes an edit on a page by pressing keys, then checks Ctrl+Z and Ctrl+Y against the set, the cursor and the status line."""

    def data(self):
        return self.document.get_setlist().to_data()

    async def undo(self):
        await self.press(keybindings.Page.UNDO)

    async def redo(self):
        await self.press(keybindings.Page.REDO)

    async def check_undo_and_redo(self, *, before, after):
        """Undo the edit that took the set from before to after, then redo it, staying on the page with the cursor where it was."""
        self.assertNotEqual(before, after)
        self.assertEqual(self.data(), after)
        screen = self.app.screen
        place = screen.remember_place()
        await self.undo()
        self.assertIs(self.app.screen, screen)
        self.assertEqual(self.data(), before)
        # The cursor stays on what it was on, unless that was the very thing the undo took away.
        self.assertIn(screen.remember_place(), (place, None))
        self.assertIn(fixed_text(messages.MSG_UNDONE), self.text())
        await self.redo()
        self.assertIs(self.app.screen, screen)
        self.assertEqual(self.data(), after)
        self.assertEqual(screen.remember_place(), place)
        self.assertIn(fixed_text(messages.MSG_RESTORED), self.text())
        await self.redo()
        self.assertIn(messages.MSG_NOTHING_TO_REDO, self.text())

    async def check_undo_goes_back_to(self, page_class):
        """Undo an edit that made what the open page shows, and check the tracker went back to the page under it and said so."""
        gone = self.app.screen
        await self.undo()
        self.assertIsNot(self.app.screen, gone)
        self.assertIsInstance(self.app.screen, page_class)
        self.assertIn(fixed_text(messages.MSG_BACK_FROM), self.text())
        self.assertIn(fixed_text(messages.MSG_UNDONE), self.text())

    async def check_rename_follows(self, *, old, new):
        """Undo the rename just made on the open page, and check that the page stays and shows the old name, and the new one again after redo."""
        screen = self.app.screen
        self.assertEqual(screen.item, new)
        self.assertIn(new, self.crumbs_line())
        await self.undo()
        self.assertIs(self.app.screen, screen)
        self.assertEqual(screen.item, old)
        self.assertIn(old, self.crumbs_line())
        self.assertNotIn(fixed_text(messages.MSG_BACK_FROM), self.text())
        await self.redo()
        self.assertIs(self.app.screen, screen)
        self.assertEqual(screen.item, new)

    def in_song(self, what):
        return messages.MSG_CHANGED_IN_SONG.format(song=self.document.get_current_song_name(), what=what)

    def named(self, *, section, name):
        return messages.MSG_CHANGED_NAMED.format(kind=messages.MSG_CHANGED_WORDS[section], name=name)


class TestMainPageUndo(UndoTest):

    async def test_with_nothing_to_undo_or_redo_the_status_line_says_so(self):
        await self.undo()
        self.assertIn(messages.MSG_NOTHING_TO_UNDO, self.text())
        await self.redo()
        self.assertIn(messages.MSG_NOTHING_TO_REDO, self.text())

    async def test_an_edit_made_on_another_page_is_undone_from_here_and_named(self):
        before = self.data()
        await self.press(keybindings.MainPage.SONGS, Key.ENTER)
        await self.select_field(labels.MSG_TEMPO_LABEL)
        await self.press(key_of(binding=keybindings.SongPage.MORE, key=Key.RIGHT_BRACKET), Key.ESCAPE, Key.ESCAPE)
        self.assertIsInstance(self.app.screen, MainPage)
        await self.check_undo_and_redo(before=before, after=self.data())
        await self.undo()
        self.assertIn(messages.MSG_UNDONE.format(what=self.in_song(messages.MSG_CHANGED_WORDS[SongSetting.TEMPO])), self.text())


class TestNotesPageUndo(UndoTest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.FILE)
        await self.select_field(labels.MSG_NOTES_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, NotesPage)

    async def test_everything_typed_until_save_is_one_step(self):
        before = self.data()
        await self.type(A_LINE)
        await self.press(Key.ENTER)
        await self.type(ANOTHER_LINE)
        # Tab reaches the buttons, and Enter presses Save, the first of them.
        await self.press(Key.TAB, Key.ENTER)
        self.assertEqual(self.document.get_setlist().get_notes(), f'{A_LINE}\n{ANOTHER_LINE}\n')
        await self.check_undo_and_redo(before=before, after=self.data())

    async def test_undo_waits_while_editing(self):
        await self.type(TWO_LETTERS)
        await self.undo()
        self.assertTrue(self.app.screen.editing)
        await self.press(Key.TAB, Key.ENTER)
        self.assertEqual(self.document.get_setlist().get_notes(), TWO_LETTERS + '\n')
        await self.undo()
        self.assertFalse(self.document.get_setlist().has_notes())


class TestOpenPageUndo(UndoTest):

    async def test_opening_a_set_starts_its_history_afresh(self):
        a_song().save(path=OTHER_FILE)
        await self.press(keybindings.MainPage.FILE)
        await self.select_field(labels.MSG_PROTECTED_LABEL)
        await self.press(Key.ENTER)
        self.assertTrue(self.app.get_document().can_undo())
        await self.press(Key.CTRL_O, keybindings.ConfirmDialog.YES)
        rows = [row[0] for row in self.app.screen.rows()]
        self.app.screen.cursor.set_place(rows.index(OTHER_FILE))
        await self.press(Key.ENTER)
        self.assertEqual(self.app.get_document().get_path(), OTHER_FILE)
        self.assertFalse(self.app.get_document().can_undo())
        await self.undo()
        self.assertIn(messages.MSG_NOTHING_TO_UNDO, self.text())


class TestSongsPageUndo(UndoTest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.SONGS)

    async def add_second_song(self):
        await self.press(keybindings.SongsPage.ADD)
        await self.type(SECOND_SONG)
        await self.press(Key.ENTER)

    async def test_undoing_the_deletion_of_the_current_song_makes_it_current_again(self):
        await self.add_second_song()
        await self.press(keybindings.SongsPage.CURRENT)
        self.assertEqual(self.document.get_current_song_name(), SECOND_SONG)
        await self.press(Key.BACKSPACE, keybindings.ConfirmDialog.YES)
        self.assertEqual(self.document.get_current_song_name(), names_text.MSG_DEFAULT_SONG_NAME)
        await self.undo()
        self.assertEqual(self.document.get_current_song_name(), SECOND_SONG)
        self.assertEqual(self.app.screen.current(), SECOND_SONG)
        self.assertIn(messages.MSG_UNDONE.format(what=messages.MSG_CHANGED_IN_SONG.format(song=SECOND_SONG, what=messages.MSG_CHANGED_WORDS[Section.SONGS])), self.text())


class TestSongPageUndo(UndoTest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.SONGS, Key.ENTER)
        self.assertIsInstance(self.app.screen, SongPage)

    async def test_the_crumb_follows_an_undone_rename_of_the_song(self):
        await self.select_field(labels.MSG_NAME_LABEL)
        await self.press(Key.ENTER)
        self.app.screen.value = RENAMED
        await self.press(Key.ENTER)
        self.assertIn(RENAMED, self.crumbs_line())
        await self.undo()
        self.assertIsInstance(self.app.screen, SongPage)
        self.assertEqual(self.document.get_current_song_name(), names_text.MSG_DEFAULT_SONG_NAME)
        self.assertNotIn(RENAMED, self.crumbs_line())


class TestPatternsPageUndo(UndoTest):

    def next_pattern_name(self):
        """Return the name the Patterns page offers for a new pattern: one more than the highest number there."""
        return new_name(word=names_text.MSG_NEW_PATTERN_WORD, taken=self.document.get_setlist().get_pattern_names())

    async def test_undoing_the_add_while_its_editor_is_open_goes_back_to_the_list(self):
        added = self.next_pattern_name()
        await self.press(keybindings.MainPage.PATTERNS, keybindings.PatternsPage.ADD, keybindings.NewPatternDialog.OK, Key.ENTER)
        self.assertIsInstance(self.app.screen, PatternEditor)
        await self.check_undo_goes_back_to(PatternsPage)
        self.assertNotIn(added, self.document.get_setlist().get_pattern_names())
        self.assertIn(messages.MSG_UNDONE.format(what=self.named(section=Section.PATTERNS, name=added)), self.text())


class TestPatternEditorUndo(UndoTest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        self.assertIsInstance(self.app.screen, PatternEditor)

    def velocities(self):
        return self.document.get_setlist().get_pattern(ui_testing.TUNE).get_row(Row.VELOCITY)

    async def test_undoing_a_rename_keeps_the_editor_on_the_pattern_under_its_old_name(self):
        await self.reconfigure(Reconfigure.RENAME)
        self.app.screen.value = RENAMED
        await self.press(Key.ENTER)
        self.assertEqual(self.app.screen.item, RENAMED)
        await self.check_rename_follows(old=ui_testing.TUNE, new=RENAMED)

    async def test_digits_typed_into_one_cell_are_one_step(self):
        before = self.data()
        await self.press(*[Key.DOWN] * VELOCITY_ROW, *ONE_HUNDRED)
        self.assertEqual(self.velocities()[0], int(''.join(ONE_HUNDRED)))
        await self.check_undo_and_redo(before=before, after=self.data())

    async def test_moving_the_cursor_ends_the_step(self):
        # After the cursor moves and comes back, the next digit starts a new number and a new step.
        await self.press(*[Key.DOWN] * VELOCITY_ROW, TWELVE[0], Key.RIGHT, Key.LEFT, TWELVE[1])
        self.assertEqual(self.velocities()[0], int(TWELVE[1]))
        await self.undo()
        self.assertEqual(self.velocities()[0], int(TWELVE[0]))

    async def test_a_munge_is_one_step(self):
        before = self.data()
        await self.press(Key.RIGHT)
        await munge(test=self, choice=Munge.REVERSE)
        self.assertNotEqual(self.data(), before)
        await self.check_undo_and_redo(before=before, after=self.data())

    async def test_placing_a_note_on_the_roll_is_one_step_whatever_it_writes(self):
        # A quarter-note entry writes a degree, an octave and a tie, and takes out what the steps held, in one step.
        before = self.data()
        await self.press(keybindings.PatternEditor.TO_ROLL)
        await self.pick_entry_size(QUARTER)
        entry_set = self.data()
        self.assertNotEqual(entry_set, before)
        await self.press(Key.RIGHT, Key.UP, keybindings.PianoRoll.PLACE)
        self.assertEqual(self.document.get_setlist().get_pattern(ui_testing.TUNE).get_row(Row.TIE), [False, False, True, False])
        await self.check_undo_and_redo(before=entry_set, after=self.data())
        self.assertTrue(self.app.screen.on_roll())
        self.assertEqual((self.app.screen.step, self.app.screen.roll.pitch), (1, self.app.screen.roll.pitch))

    async def test_the_knife_and_erasing_on_the_roll_undo(self):
        await self.press(keybindings.PatternEditor.TO_ROLL, keybindings.PianoRoll.ERASE)
        await self.pick_entry_size(HALF)
        await self.press(keybindings.PianoRoll.PLACE)
        before = self.data()
        await self.press(Key.RIGHT, Key.RIGHT, keybindings.PianoRoll.KNIFE)
        await self.check_undo_and_redo(before=before, after=self.data())
        before = self.data()
        await self.press(keybindings.PianoRoll.ERASE)
        self.assertEqual(self.document.get_setlist().get_pattern(ui_testing.TUNE).get_row(Row.DEGREE), [1, None, None, None])
        await self.check_undo_and_redo(before=before, after=self.data())


class TestChainEditorUndo(UndoTest):

    async def test_undoing_a_rename_keeps_the_editor_on_the_chain_under_its_old_name(self):
        await self.open_chain(ui_testing.NAMED)
        name = self.app.screen.item
        await self.press(keybindings.ChainEditor.RENAME)
        self.app.screen.value = RENAMED
        await self.press(Key.ENTER)
        await self.check_rename_follows(old=name, new=RENAMED)

class TestOffsetsEditorUndo(UndoTest):

    async def open_offsets(self):
        await self.select_field(labels.MSG_OFFSETS_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, OffsetsEditor)

    def offsets(self):
        return self.document.get_setlist().get_generator_settings(kind=arp_plugin.NAME, name=ui_testing.UP_ARP).get_offsets()

    async def test_typing_an_offset_is_one_step_and_two_digits_are_still_one(self):
        await self.open_generator(section=arp_plugin.SECTION)
        await self.open_offsets()
        before = self.data()
        await self.press(Key.RIGHT, SEVEN)
        self.assertEqual(self.offsets()[1], int(SEVEN))
        await self.check_undo_and_redo(before=before, after=self.data())
        await self.press(Key.RIGHT, *TWELVE)
        self.assertEqual(self.offsets()[2], int(''.join(TWELVE)))
        await self.undo()
        self.assertEqual(self.offsets()[2], 0)

    async def test_undoing_the_offsets_and_then_the_arp_closes_this_editor_and_then_the_arps(self):
        name = await self.add_generator(arp_plugin.SECTION)
        self.assertIsInstance(self.app.screen, PluginEditor)
        # Opening the offsets editor gives a new arp its row of offsets, which is the first thing to undo.
        await self.open_offsets()
        await self.check_undo_goes_back_to(PluginEditor)
        self.assertIsNone(self.document.get_setlist().get_generator_settings(kind=arp_plugin.NAME, name=name).get_offsets())
        await self.check_undo_goes_back_to(GeneratorsPage)


class TestScalePageUndo(UndoTest):

    async def test_changing_the_root_is_one_step_and_the_crumb_follows(self):
        self.document.rename_named(section=Section.SCALES, old=self.document.get_setlist().get_scale_names()[0], new=default_scale_name(root=NoteName.C, kind=scale_type_name(ScaleType.MAJOR)))
        await self.press(keybindings.MainPage.SCALES, Key.ENTER)
        self.assertIsInstance(self.app.screen, ScalePage)
        before = self.data()
        name = self.app.screen.item
        await self.select_field(labels.MSG_ROOT_LABEL)
        await self.press(Key.RIGHT)
        renamed = self.app.screen.item
        self.assertNotEqual(renamed, name)
        # A scale still named after its root is renamed as the root changes, and the page follows the name both ways.
        await self.check_rename_follows(old=name, new=renamed)
        await self.undo()
        self.assertEqual(self.data(), before)


class TestGrooveEditorUndo(UndoTest):

    async def test_digits_typed_into_one_cell_are_one_step(self):
        await self.press(keybindings.MainPage.GROOVES, keybindings.GroovesPage.ADD)
        name = names_text.MSG_NUMBERED_NAME.format(base=names_text.MSG_NEW_GROOVE_WORD, number=defaults.FIRST_NUMBER)
        before = self.data()
        await self.press(Key.RIGHT, *TWELVE)
        self.assertEqual(self.document.get_setlist().get_groove(name).get_cells()[1], int(''.join(TWELVE)))
        await self.check_undo_and_redo(before=before, after=self.data())


class TestInstrumentsPageUndo(UndoTest):

    async def test_adding_the_first_instrument_turns_real_time_on_and_is_one_step(self):
        before = self.data()
        self.assertFalse(self.document.get_setlist().is_real_time())
        await self.press(keybindings.MainPage.INSTRUMENTS, keybindings.InstrumentsPage.ADD, Key.ESCAPE)
        self.assertIsInstance(self.app.screen, InstrumentsPage)
        self.assertTrue(self.document.get_setlist().is_real_time())
        await self.check_undo_and_redo(before=before, after=self.data())

class TestArrangePageUndo(UndoTest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.ARRANGE)
        self.assertIsInstance(self.app.screen, ArrangePage)

    async def test_deleting_a_scene_with_its_clips_is_one_step(self):
        before = self.data()
        await self.press(Key.BACKSPACE, keybindings.ConfirmDialog.YES)
        self.assertEqual(len(self.document.song().get_scenes()), 1)
        await self.check_undo_and_redo(before=before, after=self.data())

    async def test_copying_a_track_with_its_clips_is_one_step(self):
        before = self.data()
        await self.press(Key.UP, keybindings.ArrangePage.COPY_TRACK, Key.ENTER)
        self.assertEqual(len(self.document.song().get_track_names()), 3)
        await self.check_undo_and_redo(before=before, after=self.data())


class TestScenePageUndo(UndoTest):

    async def test_undoing_a_rename_keeps_the_page_on_the_scene_under_its_old_name(self):
        await self.press(keybindings.MainPage.ARRANGE, Key.ENTER)
        name = self.app.screen.scene().get_name()
        await self.select_field(labels.MSG_NAME_LABEL)
        await self.press(Key.ENTER)
        self.app.screen.value = RENAMED
        await self.press(Key.ENTER)
        self.assertEqual(self.app.screen.shown_name, RENAMED)
        screen = self.app.screen
        await self.undo()
        self.assertIs(self.app.screen, screen)
        self.assertEqual(screen.shown_name, name)
        await self.redo()
        self.assertIs(self.app.screen, screen)
        self.assertEqual(screen.shown_name, RENAMED)

    async def test_undoing_the_copy_while_the_copys_page_is_open_goes_back_to_arrange(self):
        await self.press(keybindings.MainPage.ARRANGE, keybindings.ArrangePage.COPY_SCENE, Key.ENTER, Key.ENTER)
        self.assertIsInstance(self.app.screen, ScenePage)
        await self.check_undo_goes_back_to(ArrangePage)


class TestEveryPageHasTestClasses(unittest.TestCase):
    """Every page has a test class named after it, so that a new page gets one. Undo needs no class a page: the base page records
    an undo step after every key and every dialog's answer, so every page has it, and only a page whose undo does something of
    its own has tests of it here."""

    def ui_test_class_names(self):
        """Return the names of every test class in the text UI test modules."""
        here = os.path.dirname(os.path.abspath(__file__))
        names = set()
        for file_name in os.listdir(here):
            if file_name.startswith(TEST_MODULE_PREFIX) and file_name.endswith(PYTHON_SUFFIX):
                module = importlib.import_module(TUI_TESTS_PACKAGE + file_name[:-len(PYTHON_SUFFIX)])
                names.update(name for name, member in inspect.getmembers(module, inspect.isclass) if issubclass(member, unittest.TestCase))
        return names

    def test_every_page_has_a_test_class(self):
        names = self.ui_test_class_names()
        pages = leaf_pages()
        self.assertTrue(pages)
        for page in pages:
            with self.subTest(page=page.__name__):
                self.assertIn(TEST_PREFIX + page.__name__, names)


if __name__ == '__main__':
    unittest.main()
