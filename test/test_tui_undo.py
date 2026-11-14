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

from llamatron.strings.labels import (
    MSG_CHORDS_LABEL, MSG_EVERY_LABEL, MSG_ROOT_IN_BASS_LABEL, MSG_DRAG_AMOUNT_LABEL, MSG_EUCLID_PART_LABELS, MSG_GLIDE_AMOUNT_LABEL, MSG_RUSH_AMOUNT_LABEL, MSG_SHAPE_PART_LABELS, MSG_SHORTEN_LABEL,
    MSG_STEPS_LABEL, MSG_STRUM_PART_LABELS, MSG_SOURCE_TRACK_LABEL,
)
from llamatron.composition.file_format import EuclidPart, ShapePart, StrumPart
from llamatron.composition.generator_settings import DEFAULT_DRAG, DEFAULT_RUSH, DEFAULT_SHORTEN
from ui_testing import TRADE, CLIPS, LAZY, PUSH, SLIDES, CLAVE, CLIPPED, FOLK, POP, SMOOTH, FADE, THIN
from llamatron.composition.defaults import DEFAULT_CHANNEL, FIRST_NUMBER
from llamatron.composition.file_format import DriftValue, DriftVersion, GeneratorKind, RegisterName, RegisterSetting, Row, Section, SongSetting
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.arrange_page import ArrangePage
from llamatron.tui.screens.chains_page import ChainsPage
from llamatron.tui.screens.clip_page import ClipPage
from llamatron.tui.screens.grooves_page import GroovesPage
from llamatron.tui.screens.instruments_page import InstrumentsPage
from llamatron.tui.screens.main_page import MainPage
from llamatron.tui.screens.offsets_editor import OffsetsEditor
from llamatron.tui.screens.pattern_editor import Munge, PatternEditor, Reconfigure
from llamatron.tui.screens.patterns_page import PatternsPage
from llamatron.tui.screens.scale_page import ScalePage
from llamatron.tui.screens.scales_page import ScalesPage
from llamatron.tui.screens.scene_page import ScenePage
from llamatron.tui.screens.track_editor import TrackEditor
from llamatron.tui.screens.groove_editor import GrooveEditor
from llamatron.tui.screens.instrument_editor import InstrumentEditor
from llamatron.tui.screens.arp_editor import ArpEditor
from llamatron.tui.screens.chords_editor import QUALITY_ROW
from llamatron.tui.screens.chain_editor import ChainEditor
from llamatron.tui.screens.notes_page import NotesPage
from llamatron.tui.screens.generators_page import GeneratorsPage
from llamatron.tui.screens.song_page import SongPage
from llamatron.strings.labels import (
    MSG_CHAINS_LABEL, MSG_DRIFT_VALUE_LABELS,
    MSG_CHANNEL_LABEL, MSG_COUNTS_LABEL, MSG_NOTES_LABEL, MSG_NAME_LABEL, MSG_OCTAVE_RANGE_LABEL, MSG_OFFSETS_LABEL, MSG_PROTECTED_LABEL,
    MSG_REGISTER_FIELD_LABEL, MSG_REPEAT_LABEL, MSG_ROOT_LABEL, MSG_TEMPO_LABEL, MSG_TITLE_LABEL, MSG_TRANSPOSE_LABEL,
)
from llamatron.strings.messages import (
    MSG_BACK_FROM, MSG_CHANGED_IN_SONG, MSG_CHANGED_NAMED, MSG_CHANGED_WORDS, MSG_NOTHING_TO_REDO, MSG_NOTHING_TO_UNDO, MSG_RESTORED,
    MSG_UNDONE,
)
from llamatron.strings.names import MSG_DEFAULT_SONG_NAME, MSG_NEW_GROOVE_NAME, MSG_NEW_INSTRUMENT_NAME, MSG_NEW_PATTERN_NAME
from llamatron.tui import keybindings
from llamatron.tui.screens.generator_pages import GENERATOR_PAGES
from ui_testing import SWAY, a_song, fixed_text, LEAD, leaf_pages, ROLLS, TUNE, UITest, UP_ARP, key_of

# Names the tests give to what they add, and what they type.
SECOND_SONG = 'second'
RENAMED = 'renamed'
NEW_CHAIN = 'lift'
# A shape's end left blank plays as 100, and one press of [ (dec) takes it down to 99.
SHAPE_NUDGED_DOWN = 99
NEW_ARP = 'fast'
# Entry sizes the roll's picker offers, longer than the tune's 1/8 steps.
QUARTER = '1/4'
HALF = '1/2'
A_TITLE = 'A title'
A_LINE = 'hi there'
ANOTHER_LINE = 'ok'
TWO_LETTERS = 'ab'
COUNTS_TYPED = '1 1 4'
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
UNDO_SUFFIX = 'Undo'
TEST_MODULE_PREFIX = 'test_tui_'
PYTHON_SUFFIX = '.py'


class UndoTest(UITest):
    """Makes an edit on a page by pressing keys, then checks Ctrl+Z and Ctrl+Y against the set, the cursor and the status line."""

    def data(self):
        return self.document.setlist().to_data()

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
        self.assertIn(fixed_text(MSG_UNDONE), self.text())
        await self.redo()
        self.assertIs(self.app.screen, screen)
        self.assertEqual(self.data(), after)
        self.assertEqual(screen.remember_place(), place)
        self.assertIn(fixed_text(MSG_RESTORED), self.text())
        await self.redo()
        self.assertIn(MSG_NOTHING_TO_REDO, self.text())

    async def check_undo_goes_back_to(self, page_class):
        """Undo an edit that made what the open page shows, and check the tracker went back to the page under it and said so."""
        gone = self.app.screen
        await self.undo()
        self.assertIsNot(self.app.screen, gone)
        self.assertIsInstance(self.app.screen, page_class)
        self.assertIn(fixed_text(MSG_BACK_FROM), self.text())
        self.assertIn(fixed_text(MSG_UNDONE), self.text())

    async def check_rename_follows(self, *, old, new):
        """Undo the rename just made on the open page, and check that the page stays and shows the old name, and the new one again after redo."""
        screen = self.app.screen
        self.assertEqual(screen.item, new)
        self.assertIn(new, self.crumbs_line())
        await self.undo()
        self.assertIs(self.app.screen, screen)
        self.assertEqual(screen.item, old)
        self.assertIn(old, self.crumbs_line())
        self.assertNotIn(fixed_text(MSG_BACK_FROM), self.text())
        await self.redo()
        self.assertIs(self.app.screen, screen)
        self.assertEqual(screen.item, new)

    def in_song(self, what):
        return MSG_CHANGED_IN_SONG.format(song=self.document.current_song_name(), what=what)

    def named(self, *, section, name):
        return MSG_CHANGED_NAMED.format(kind=MSG_CHANGED_WORDS[section], name=name)


class TestMainPageUndo(UndoTest):

    async def test_with_nothing_to_undo_or_redo_the_status_line_says_so(self):
        await self.undo()
        self.assertIn(MSG_NOTHING_TO_UNDO, self.text())
        await self.redo()
        self.assertIn(MSG_NOTHING_TO_REDO, self.text())

    async def test_an_edit_made_on_another_page_is_undone_from_here_and_named(self):
        before = self.data()
        await self.press(keybindings.MainPage.SONGS, Key.ENTER)
        await self.select_field(MSG_TEMPO_LABEL)
        await self.press(key_of(binding=keybindings.SongPage.MORE, key=Key.RIGHT_BRACKET), Key.ESCAPE, Key.ESCAPE)
        self.assertIsInstance(self.app.screen, MainPage)
        await self.check_undo_and_redo(before=before, after=self.data())
        await self.undo()
        self.assertIn(MSG_UNDONE.format(what=self.in_song(MSG_CHANGED_WORDS[SongSetting.TEMPO])), self.text())


class TestFilePageUndo(UndoTest):

    async def test_a_toggle_is_one_step(self):
        before = self.data()
        await self.press(keybindings.MainPage.FILE)
        await self.select_field(MSG_PROTECTED_LABEL)
        await self.press(Key.ENTER)
        self.assertTrue(self.document.setlist().is_protected())
        await self.check_undo_and_redo(before=before, after=self.data())

    async def test_a_prompt_answered_is_one_step(self):
        before = self.data()
        await self.press(keybindings.MainPage.FILE)
        await self.select_field(MSG_TITLE_LABEL)
        await self.press(Key.ENTER)
        await self.type(A_TITLE)
        await self.press(Key.ENTER)
        self.assertEqual(self.document.setlist().get_title(), A_TITLE)
        await self.check_undo_and_redo(before=before, after=self.data())


class TestNotesPageUndo(UndoTest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.FILE)
        await self.select_field(MSG_NOTES_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, NotesPage)

    async def test_everything_typed_until_save_is_one_step(self):
        before = self.data()
        await self.type(A_LINE)
        await self.press(Key.ENTER)
        await self.type(ANOTHER_LINE)
        # Tab reaches the buttons, and Enter presses Save, the first of them.
        await self.press(Key.TAB, Key.ENTER)
        self.assertEqual(self.document.setlist().get_notes(), f'{A_LINE}\n{ANOTHER_LINE}\n')
        await self.check_undo_and_redo(before=before, after=self.data())

    async def test_undo_waits_while_editing(self):
        await self.type(TWO_LETTERS)
        await self.undo()
        self.assertTrue(self.app.screen.editing)
        await self.press(Key.TAB, Key.ENTER)
        self.assertEqual(self.document.setlist().get_notes(), TWO_LETTERS + '\n')
        await self.undo()
        self.assertFalse(self.document.setlist().has_notes())


class TestOpenPageUndo(UndoTest):

    async def test_opening_a_set_starts_its_history_afresh(self):
        a_song().save(path=OTHER_FILE)
        await self.press(keybindings.MainPage.FILE)
        await self.select_field(MSG_PROTECTED_LABEL)
        await self.press(Key.ENTER)
        self.assertTrue(self.app.get_document().can_undo())
        await self.press(Key.CTRL_O, keybindings.ConfirmDialog.YES)
        rows = [row[0] for row in self.app.screen.rows()]
        self.app.screen.place = rows.index(OTHER_FILE)
        await self.press(Key.ENTER)
        self.assertEqual(self.app.get_document().get_path(), OTHER_FILE)
        self.assertFalse(self.app.get_document().can_undo())
        await self.undo()
        self.assertIn(MSG_NOTHING_TO_UNDO, self.text())


class TestSongsPageUndo(UndoTest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.SONGS)

    async def add_second_song(self):
        await self.press(keybindings.SongsPage.ADD)
        await self.type(SECOND_SONG)
        await self.press(Key.ENTER)

    async def test_adding_a_song_is_one_step(self):
        before = self.data()
        await self.add_second_song()
        self.assertEqual(self.document.song_names(), [MSG_DEFAULT_SONG_NAME, SECOND_SONG])
        await self.check_undo_and_redo(before=before, after=self.data())

    async def test_undoing_the_deletion_of_the_current_song_makes_it_current_again(self):
        await self.add_second_song()
        await self.press(keybindings.SongsPage.CURRENT)
        self.assertEqual(self.document.current_song_name(), SECOND_SONG)
        await self.press(Key.BACKSPACE, keybindings.ConfirmDialog.YES)
        self.assertEqual(self.document.current_song_name(), MSG_DEFAULT_SONG_NAME)
        await self.undo()
        self.assertEqual(self.document.current_song_name(), SECOND_SONG)
        self.assertEqual(self.app.screen.current(), SECOND_SONG)
        self.assertIn(MSG_UNDONE.format(what=MSG_CHANGED_IN_SONG.format(song=SECOND_SONG, what=MSG_CHANGED_WORDS[Section.SONGS])), self.text())


class TestSongPageUndo(UndoTest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.SONGS, Key.ENTER)
        self.assertIsInstance(self.app.screen, SongPage)

    async def test_a_setting_is_one_step_and_the_cursor_stays(self):
        before = self.data()
        await self.select_field(MSG_TEMPO_LABEL)
        await self.press(key_of(binding=keybindings.SongPage.MORE, key=Key.RIGHT_BRACKET))
        await self.check_undo_and_redo(before=before, after=self.data())

    async def test_the_crumb_follows_an_undone_rename_of_the_song(self):
        await self.select_field(MSG_NAME_LABEL)
        await self.press(Key.ENTER)
        self.app.screen.value = RENAMED
        await self.press(Key.ENTER)
        self.assertIn(RENAMED, self.crumbs_line())
        await self.undo()
        self.assertIsInstance(self.app.screen, SongPage)
        self.assertEqual(self.document.current_song_name(), MSG_DEFAULT_SONG_NAME)
        self.assertNotIn(RENAMED, self.crumbs_line())


class TestPatternsPageUndo(UndoTest):

    def next_pattern_name(self):
        """Return the name the Patterns page offers for a new pattern: the first free number after the ones there."""
        return MSG_NEW_PATTERN_NAME.format(number=len(self.document.song().get_pattern_names()) + 1)

    async def test_adding_a_pattern_is_one_step(self):
        before = self.data()
        added = self.next_pattern_name()
        await self.press(keybindings.MainPage.PATTERNS, keybindings.PatternsPage.ADD, Key.ENTER, Key.ESCAPE)
        self.assertIsInstance(self.app.screen, PatternsPage)
        self.assertIn(added, self.document.song().get_pattern_names())
        await self.check_undo_and_redo(before=before, after=self.data())

    async def test_undoing_the_add_while_its_editor_is_open_goes_back_to_the_list(self):
        added = self.next_pattern_name()
        await self.press(keybindings.MainPage.PATTERNS, keybindings.PatternsPage.ADD, Key.ENTER)
        self.assertIsInstance(self.app.screen, PatternEditor)
        await self.check_undo_goes_back_to(PatternsPage)
        self.assertNotIn(added, self.document.song().get_pattern_names())
        self.assertIn(MSG_UNDONE.format(what=self.named(section=Section.PATTERNS, name=added)), self.text())


class TestPatternEditorUndo(UndoTest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        self.assertIsInstance(self.app.screen, PatternEditor)

    def velocities(self):
        return self.document.song().get_pattern(TUNE).get_row(Row.VELOCITY)

    async def test_undoing_a_rename_keeps_the_editor_on_the_pattern_under_its_old_name(self):
        await self.reconfigure(Reconfigure.RENAME)
        self.app.screen.value = RENAMED
        await self.press(Key.ENTER)
        self.assertEqual(self.app.screen.item, RENAMED)
        await self.check_rename_follows(old=TUNE, new=RENAMED)

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
        await self.reconfigure(Reconfigure.MUNGE)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        await self.press(*[Key.DOWN] * Munge.REVERSE, Key.ENTER)
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
        self.assertEqual(self.document.song().get_pattern(TUNE).get_row(Row.TIE), [False, False, True, False])
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
        self.assertEqual(self.document.song().get_pattern(TUNE).get_row(Row.DEGREE), [1, None, None, None])
        await self.check_undo_and_redo(before=before, after=self.data())


class TestChainsPageUndo(UndoTest):

    async def test_adding_a_chain_is_one_step(self):
        before = self.data()
        await self.press(keybindings.MainPage.CHAINS, keybindings.ChainsPage.ADD)
        await self.type(NEW_CHAIN)
        await self.press(Key.ENTER)
        self.assertIn(NEW_CHAIN, self.document.song().get_chain_names())
        await self.check_undo_and_redo(before=before, after=self.data())


class TestChainEditorUndo(UndoTest):

    async def test_copying_a_step_is_one_step(self):
        await self.press(keybindings.MainPage.CHAINS, Key.ENTER)
        self.assertIsInstance(self.app.screen, ChainEditor)
        before = self.data()
        await self.press(keybindings.ChainEditor.COPY)
        await self.check_undo_and_redo(before=before, after=self.data())

    async def test_undoing_a_rename_keeps_the_editor_on_the_chain_under_its_old_name(self):
        await self.press(keybindings.MainPage.CHAINS, Key.ENTER)
        name = self.app.screen.item
        await self.press(keybindings.ChainEditor.RENAME)
        self.app.screen.value = RENAMED
        await self.press(Key.ENTER)
        await self.check_rename_follows(old=name, new=RENAMED)

    async def test_undoing_the_add_while_the_editor_is_open_goes_back_to_the_list(self):
        await self.press(keybindings.MainPage.CHAINS, keybindings.ChainsPage.ADD)
        await self.type(NEW_CHAIN)
        await self.press(Key.ENTER, Key.ENTER)
        self.assertIsInstance(self.app.screen, ChainEditor)
        await self.check_undo_goes_back_to(ChainsPage)


class TestGeneratorsPageUndo(UndoTest):

    async def test_adding_a_generator_and_moving_one_are_each_one_step(self):
        await self.press(keybindings.MainPage.GENERATORS)
        self.assertIsInstance(self.app.screen, GeneratorsPage)
        await self.undo()
        self.assertIn(MSG_NOTHING_TO_UNDO, self.text())
        before = self.data()
        await self.press(keybindings.GeneratorsPage.ADD)
        await self.pick(GENERATOR_PAGES[Section.ARPS].label)
        # The new arpeggiator sits after the set's other one; the cursor goes back up to that one, which the undo leaves.
        await self.press(Key.ESCAPE, Key.UP)
        self.assertIsInstance(self.app.screen, GeneratorsPage)
        await self.check_undo_and_redo(before=before, after=self.data())

    async def test_moving_one_is_one_step(self):
        await self.press(keybindings.MainPage.GENERATORS)
        before = self.data()
        await self.press(keybindings.GeneratorsPage.MOVE, Key.DOWN, Key.ENTER)
        await self.check_undo_and_redo(before=before, after=self.data())

class TestArpEditorUndo(UndoTest):

    async def test_a_setting_is_one_step(self):
        await self.open_generator(section=Section.ARPS)
        self.assertIsInstance(self.app.screen, ArpEditor)
        before = self.data()
        await self.select_field(MSG_OCTAVE_RANGE_LABEL)
        await self.press(key_of(binding=keybindings.ArpEditor.MORE, key=Key.RIGHT_BRACKET))
        await self.check_undo_and_redo(before=before, after=self.data())

    async def test_undoing_the_add_while_the_editor_is_open_goes_back_to_the_list(self):
        await self.add_generator(Section.ARPS)
        self.assertIsInstance(self.app.screen, ArpEditor)
        await self.check_undo_goes_back_to(GeneratorsPage)


class TestOffsetsEditorUndo(UndoTest):

    async def open_offsets(self):
        await self.select_field(MSG_OFFSETS_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, OffsetsEditor)

    def offsets(self):
        return self.document.song().get_generator_settings(kind=GeneratorKind.ARP, name=UP_ARP).get_offsets()

    async def test_typing_an_offset_is_one_step_and_two_digits_are_still_one(self):
        await self.open_generator(section=Section.ARPS)
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
        name = await self.add_generator(Section.ARPS)
        self.assertIsInstance(self.app.screen, ArpEditor)
        # Opening the offsets editor gives a new arp its row of offsets, which is the first thing to undo.
        await self.open_offsets()
        await self.check_undo_goes_back_to(ArpEditor)
        self.assertIsNone(self.document.song().get_generator_settings(kind=GeneratorKind.ARP, name=name).get_offsets())
        await self.check_undo_goes_back_to(GeneratorsPage)


class TestAutoRatchetEditorUndo(UndoTest):

    async def test_typing_counts_is_one_step(self):
        await self.open_generator(section=Section.AUTO_RATCHETS)
        before = self.data()
        await self.select_field(MSG_COUNTS_LABEL)
        await self.press(Key.ENTER)
        self.app.screen.value = COUNTS_TYPED
        await self.press(Key.ENTER)
        self.assertEqual(self.auto_ratchet(ROLLS).get_counts(), [int(count) for count in COUNTS_TYPED.split()])
        await self.check_undo_and_redo(before=before, after=self.data())


class TestDriftEditorUndo(UndoTest):

    async def test_changing_a_versions_value_is_one_step(self):
        await self.open_generator(section=Section.DRIFTS)
        before = self.data()
        await self.select_field(MSG_DRIFT_VALUE_LABELS[DriftValue.VELOCITY])
        await self.press(Key.RIGHT, keybindings.DriftEditor.MORE)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.DRIFT, name=SWAY).get_value(version=DriftVersion.B, value=DriftValue.VELOCITY), None)
        await self.check_undo_and_redo(before=before, after=self.data())


class TestProgressionEditorUndo(UndoTest):

    async def test_changing_every_is_one_step(self):
        await self.open_generator(section=Section.PROGRESSIONS)
        before = self.data()
        await self.select_field(MSG_EVERY_LABEL)
        await self.press(keybindings.ProgressionEditor.MORE)
        self.assertIsNotNone(self.document.song().get_generator_settings(kind=GeneratorKind.PROGRESSION, name=POP).get_every())
        await self.check_undo_and_redo(before=before, after=self.data())


class TestChordsEditorUndo(UndoTest):

    async def test_picking_a_named_progression_is_one_step(self):
        await self.open_generator(section=Section.PROGRESSIONS)
        await self.select_field(MSG_CHORDS_LABEL)
        await self.press(Key.ENTER)
        before = self.data()
        # The picker opens on Pop, which the test song already holds, so Down picks Fifties.
        await self.press(keybindings.ChordsEditor.PICK, Key.DOWN, Key.ENTER)
        self.assertNotEqual(self.data(), before)
        await self.check_undo_and_redo(before=before, after=self.data())


    async def test_a_chord_chosen_in_the_chord_dialog_is_one_step(self):
        await self.open_generator(section=Section.PROGRESSIONS)
        await self.select_field(MSG_CHORDS_LABEL)
        await self.press(Key.ENTER, *[Key.DOWN] * QUALITY_ROW)
        before = self.data()
        # A quality, a tension and a scale together: Down picks the first quality, Tab reaches the tensions, Space turns the first on, Tab reaches the scales, where Down
        # and Enter open the first category's flyout and Enter picks its first scale, and the last Enter takes the chord.
        await self.press(
            keybindings.ChordsEditor.CHOOSE, Key.DOWN, keybindings.ChordDialog.NEXT_LIST, keybindings.ChordDialog.FLIP, keybindings.ChordDialog.NEXT_LIST, Key.DOWN,
            keybindings.ChordDialog.OPEN, keybindings.ChordDialog.CHOOSE, keybindings.ChordDialog.CHOOSE,
        )
        self.assertIsNotNone(self.document.song().get_generator_settings(kind=GeneratorKind.PROGRESSION, name=POP).get_scales()[0])
        self.assertNotEqual(self.data(), before)
        await self.check_undo_and_redo(before=before, after=self.data())


class TestVoiceLeadingEditorUndo(UndoTest):

    async def test_keeping_the_root_in_the_bass_is_one_step(self):
        await self.open_generator(section=Section.VOICE_LEADINGS)
        before = self.data()
        await self.select_field(MSG_ROOT_IN_BASS_LABEL)
        await self.press(keybindings.VoiceLeadingEditor.TOGGLE)
        self.assertTrue(self.document.song().get_generator_settings(kind=GeneratorKind.VOICE_LEADING, name=SMOOTH).keeps_root_in_bass())
        await self.check_undo_and_redo(before=before, after=self.data())


class TestHocketEditorUndo(UndoTest):

    async def test_clearing_the_source_is_one_step(self):
        await self.open_generator(section=Section.HOCKETS)
        before = self.data()
        await self.select_field(MSG_SOURCE_TRACK_LABEL)
        await self.press(keybindings.HocketEditor.CLEAR)
        self.assertIsNone(self.document.song().get_generator_settings(kind=GeneratorKind.HOCKET, name=TRADE).get_source())
        await self.check_undo_and_redo(before=before, after=self.data())


class TestStrumEditorUndo(UndoTest):

    async def test_changing_the_spread_is_one_step(self):
        await self.open_generator(section=Section.STRUMS)
        before = self.data()
        await self.select_field(MSG_STRUM_PART_LABELS[StrumPart.SPREAD])
        await self.press(keybindings.StrumEditor.MORE)
        self.assertIsNotNone(self.document.song().get_generator_settings(kind=GeneratorKind.STRUM, name=FOLK).get_strum_setting(StrumPart.SPREAD))
        await self.check_undo_and_redo(before=before, after=self.data())


class TestEuclidEditorUndo(UndoTest):

    async def test_picking_a_named_rhythm_is_one_step(self):
        await self.open_generator(section=Section.EUCLIDS)
        before = self.data()
        await self.select_field(MSG_EUCLID_PART_LABELS[EuclidPart.HITS])
        # The picker opens on the tresillo, which the test song's clave already plays, so Down picks the cinquillo.
        await self.press(keybindings.EuclidEditor.PICK_RHYTHM, Key.DOWN, Key.ENTER)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.EUCLID, name=CLAVE).get_euclid().hits, 5)
        await self.check_undo_and_redo(before=before, after=self.data())


class TestGlideEditorUndo(UndoTest):

    async def test_changing_the_glide_amount_is_one_step(self):
        await self.open_generator(section=Section.GLIDES)
        before = self.data()
        await self.select_field(MSG_GLIDE_AMOUNT_LABEL)
        await self.press(keybindings.GlideEditor.MORE)
        self.assertIsNotNone(self.document.song().get_generator_settings(kind=GeneratorKind.GLIDE, name=SLIDES).get_written_glide_amount())
        await self.check_undo_and_redo(before=before, after=self.data())


class TestGlideStepsEditorUndo(UndoTest):

    async def test_turning_a_step_on_or_off_is_one_step(self):
        await self.open_generator(section=Section.GLIDES)
        await self.select_field(MSG_STEPS_LABEL)
        await self.press(Key.ENTER)
        before = self.data()
        await self.press(keybindings.GlideStepsEditor.TOGGLE)
        self.assertNotEqual(self.data(), before)
        await self.check_undo_and_redo(before=before, after=self.data())


class TestShortenEditorUndo(UndoTest):

    async def test_changing_the_amount_is_one_step(self):
        await self.open_generator(section=Section.SHORTENS)
        before = self.data()
        await self.select_field(MSG_SHORTEN_LABEL)
        await self.press(keybindings.ShortenEditor.MORE)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.SHORTEN, name=CLIPS).get_shorten(), DEFAULT_SHORTEN + 1)
        await self.check_undo_and_redo(before=before, after=self.data())


class TestShortenStepsEditorUndo(UndoTest):

    async def test_turning_a_step_on_or_off_is_one_step(self):
        await self.open_generator(section=Section.SHORTENS)
        await self.select_field(MSG_STEPS_LABEL)
        await self.press(Key.ENTER)
        before = self.data()
        await self.press(keybindings.ShortenStepsEditor.TOGGLE)
        self.assertNotEqual(self.data(), before)
        await self.check_undo_and_redo(before=before, after=self.data())


class TestRushEditorUndo(UndoTest):

    async def test_changing_the_amount_is_one_step(self):
        await self.open_generator(section=Section.RUSHES)
        before = self.data()
        await self.select_field(MSG_RUSH_AMOUNT_LABEL)
        await self.press(keybindings.RushEditor.MORE)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.RUSH, name=PUSH).get_amount(), DEFAULT_RUSH + 1)
        await self.check_undo_and_redo(before=before, after=self.data())


class TestRushStepsEditorUndo(UndoTest):

    async def test_turning_a_step_on_or_off_is_one_step(self):
        await self.open_generator(section=Section.RUSHES)
        await self.select_field(MSG_STEPS_LABEL)
        await self.press(Key.ENTER)
        before = self.data()
        await self.press(keybindings.RushStepsEditor.TOGGLE)
        self.assertNotEqual(self.data(), before)
        await self.check_undo_and_redo(before=before, after=self.data())


class TestDragEditorUndo(UndoTest):

    async def test_changing_the_amount_is_one_step(self):
        await self.open_generator(section=Section.DRAGS)
        before = self.data()
        await self.select_field(MSG_DRAG_AMOUNT_LABEL)
        await self.press(keybindings.DragEditor.MORE)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.DRAG, name=LAZY).get_amount(), DEFAULT_DRAG + 1)
        await self.check_undo_and_redo(before=before, after=self.data())


class TestDragStepsEditorUndo(UndoTest):

    async def test_turning_a_step_on_or_off_is_one_step(self):
        await self.open_generator(section=Section.DRAGS)
        await self.select_field(MSG_STEPS_LABEL)
        await self.press(Key.ENTER)
        before = self.data()
        await self.press(keybindings.DragStepsEditor.TOGGLE)
        self.assertNotEqual(self.data(), before)
        await self.check_undo_and_redo(before=before, after=self.data())


class TestDensityEditorUndo(UndoTest):

    async def test_changing_its_end_is_one_step(self):
        await self.open_generator(section=Section.DENSITIES)
        before = self.data()
        await self.select_field(MSG_SHAPE_PART_LABELS[ShapePart.END])
        await self.press(keybindings.DensityEditor.LESS)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.DENSITY, name=THIN).get_shape().end, SHAPE_NUDGED_DOWN)
        await self.check_undo_and_redo(before=before, after=self.data())


class TestSwellEditorUndo(UndoTest):

    async def test_changing_its_end_is_one_step(self):
        await self.open_generator(section=Section.SWELLS)
        before = self.data()
        await self.select_field(MSG_SHAPE_PART_LABELS[ShapePart.END])
        await self.press(keybindings.SwellEditor.LESS)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.SWELL, name=FADE).get_shape().end, SHAPE_NUDGED_DOWN)
        await self.check_undo_and_redo(before=before, after=self.data())


class TestArticulateEditorUndo(UndoTest):

    async def test_changing_its_end_is_one_step(self):
        await self.open_generator(section=Section.ARTICULATES)
        before = self.data()
        await self.select_field(MSG_SHAPE_PART_LABELS[ShapePart.END])
        await self.press(keybindings.ArticulateEditor.LESS)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.ARTICULATE, name=CLIPPED).get_shape().end, SHAPE_NUDGED_DOWN)
        await self.check_undo_and_redo(before=before, after=self.data())


class TestChainListPageUndo(UndoTest):

    async def test_adding_a_chain_to_a_track_is_one_step(self):
        await self.press(keybindings.MainPage.ARRANGE, Key.UP, Key.ENTER)
        await self.select_field(MSG_CHAINS_LABEL)
        await self.press(Key.ENTER)
        before = self.data()
        await self.press(keybindings.ChainListPage.ADD, Key.ENTER)
        self.assertEqual(len(self.document.song().get_track(LEAD).get_chain_names()), 1)
        await self.check_undo_and_redo(before=before, after=self.data())


class TestScalesPageUndo(UndoTest):

    async def test_adding_a_scale_is_one_step(self):
        before = self.data()
        await self.press(keybindings.MainPage.SCALES, keybindings.ScalesPage.ADD, Key.ESCAPE)
        self.assertIsInstance(self.app.screen, ScalesPage)
        await self.check_undo_and_redo(before=before, after=self.data())

    async def test_undoing_the_add_while_its_page_is_open_goes_back_to_the_list(self):
        await self.press(keybindings.MainPage.SCALES, keybindings.ScalesPage.ADD)
        self.assertIsInstance(self.app.screen, ScalePage)
        await self.check_undo_goes_back_to(ScalesPage)


class TestScalePageUndo(UndoTest):

    async def test_changing_the_root_is_one_step_and_the_crumb_follows(self):
        await self.press(keybindings.MainPage.SCALES, Key.ENTER)
        self.assertIsInstance(self.app.screen, ScalePage)
        before = self.data()
        name = self.app.screen.item
        await self.select_field(MSG_ROOT_LABEL)
        await self.press(Key.RIGHT)
        renamed = self.app.screen.item
        self.assertNotEqual(renamed, name)
        # A scale still named after its root is renamed as the root changes, and the page follows the name both ways.
        await self.check_rename_follows(old=name, new=renamed)
        await self.undo()
        self.assertEqual(self.data(), before)


class TestGroovesPageUndo(UndoTest):

    async def test_adding_a_groove_is_one_step(self):
        before = self.data()
        await self.press(keybindings.MainPage.GROOVES, keybindings.GroovesPage.ADD, Key.ESCAPE)
        self.assertIsInstance(self.app.screen, GroovesPage)
        await self.check_undo_and_redo(before=before, after=self.data())

    async def test_undoing_the_add_while_the_editor_is_open_goes_back_to_the_list(self):
        await self.press(keybindings.MainPage.GROOVES, keybindings.GroovesPage.ADD)
        self.assertIsInstance(self.app.screen, GrooveEditor)
        await self.check_undo_goes_back_to(GroovesPage)
        self.assertIn(MSG_UNDONE.format(what=self.named(section=Section.GROOVES, name=MSG_NEW_GROOVE_NAME.format(number=FIRST_NUMBER))), self.text())


class TestGrooveEditorUndo(UndoTest):

    async def test_digits_typed_into_one_cell_are_one_step(self):
        await self.press(keybindings.MainPage.GROOVES, keybindings.GroovesPage.ADD)
        name = MSG_NEW_GROOVE_NAME.format(number=FIRST_NUMBER)
        before = self.data()
        await self.press(Key.RIGHT, *TWELVE)
        self.assertEqual(self.document.song().get_groove(name).get_cells()[1], int(''.join(TWELVE)))
        await self.check_undo_and_redo(before=before, after=self.data())


class TestInstrumentsPageUndo(UndoTest):

    async def test_adding_the_first_instrument_turns_real_time_on_and_is_one_step(self):
        before = self.data()
        self.assertFalse(self.document.setlist().is_real_time())
        await self.press(keybindings.MainPage.INSTRUMENTS, keybindings.InstrumentsPage.ADD, Key.ESCAPE)
        self.assertIsInstance(self.app.screen, InstrumentsPage)
        self.assertTrue(self.document.setlist().is_real_time())
        await self.check_undo_and_redo(before=before, after=self.data())

    async def test_undoing_the_add_while_the_editor_is_open_goes_back_to_the_list(self):
        await self.press(keybindings.MainPage.INSTRUMENTS, keybindings.InstrumentsPage.ADD)
        self.assertIsInstance(self.app.screen, InstrumentEditor)
        await self.check_undo_goes_back_to(InstrumentsPage)
        self.assertIn(MSG_UNDONE.format(what=self.named(section=Section.INSTRUMENTS, name=MSG_NEW_INSTRUMENT_NAME.format(number=FIRST_NUMBER))), self.text())


class TestInstrumentEditorUndo(UndoTest):

    async def test_stepping_the_channel_is_one_step(self):
        await self.press(keybindings.MainPage.INSTRUMENTS, keybindings.InstrumentsPage.ADD)
        name = MSG_NEW_INSTRUMENT_NAME.format(number=FIRST_NUMBER)
        before = self.data()
        await self.select_field(MSG_CHANNEL_LABEL)
        await self.press(keybindings.FieldPage.MORE)
        self.assertEqual(self.document.setlist().get_instrument(name).get_channel(), DEFAULT_CHANNEL + 1)
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
        await self.press(Key.UP, keybindings.ArrangePage.COPY_TRACK)
        self.assertEqual(len(self.document.song().get_track_names()), 3)
        await self.check_undo_and_redo(before=before, after=self.data())


class TestScenePageUndo(UndoTest):

    async def test_a_setting_is_one_step(self):
        await self.press(keybindings.MainPage.ARRANGE, Key.ENTER)
        self.assertIsInstance(self.app.screen, ScenePage)
        before = self.data()
        await self.select_field(MSG_REPEAT_LABEL)
        await self.press(key_of(binding=keybindings.ScenePage.MORE, key=Key.RIGHT_BRACKET))
        await self.check_undo_and_redo(before=before, after=self.data())

    async def test_undoing_a_rename_keeps_the_page_on_the_scene_under_its_old_name(self):
        await self.press(keybindings.MainPage.ARRANGE, Key.ENTER)
        name = self.app.screen.scene().get_name()
        await self.select_field(MSG_NAME_LABEL)
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
        await self.press(keybindings.MainPage.ARRANGE, keybindings.ArrangePage.COPY_SCENE, Key.ENTER)
        self.assertIsInstance(self.app.screen, ScenePage)
        await self.check_undo_goes_back_to(ArrangePage)


class TestClipPageUndo(UndoTest):

    async def test_a_setting_is_one_step(self):
        await self.press(keybindings.MainPage.ARRANGE, Key.RIGHT, Key.ENTER)
        self.assertIsInstance(self.app.screen, ClipPage)
        before = self.data()
        await self.select_field(MSG_REPEAT_LABEL)
        await self.press(key_of(binding=keybindings.ClipPage.MORE, key=Key.RIGHT_BRACKET))
        await self.check_undo_and_redo(before=before, after=self.data())

    async def test_undoing_the_tracks_rename_keeps_the_page_on_the_clip(self):
        await self.press(keybindings.MainPage.ARRANGE, Key.UP, Key.ENTER)
        self.assertIsInstance(self.app.screen, TrackEditor)
        await self.select_field(MSG_NAME_LABEL)
        await self.press(Key.ENTER)
        self.app.screen.value = RENAMED
        await self.press(Key.ENTER, Key.ESCAPE, Key.DOWN, Key.ENTER)
        self.assertIsInstance(self.app.screen, ClipPage)
        self.assertEqual(self.app.screen.track, RENAMED)
        screen = self.app.screen
        await self.undo()
        self.assertIs(self.app.screen, screen)
        self.assertEqual(screen.track, LEAD)
        self.assertIn(LEAD, self.crumbs_line())
        await self.redo()
        self.assertEqual(screen.track, RENAMED)

    async def test_undoing_the_clips_adding_while_its_page_is_open_goes_back_to_arrange(self):
        await self.press(keybindings.MainPage.ARRANGE, Key.DOWN, Key.RIGHT, Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        await self.press(Key.ENTER)
        if not isinstance(self.app.screen, ClipPage):
            await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ClipPage)
        await self.check_undo_goes_back_to(ArrangePage)
        self.assertIsNone(self.document.clip_slot(index=1, track=LEAD))


class TestTrackEditorUndo(UndoTest):

    async def test_a_setting_is_one_step(self):
        await self.press(keybindings.MainPage.ARRANGE, Key.UP, Key.ENTER)
        self.assertIsInstance(self.app.screen, TrackEditor)
        before = self.data()
        await self.select_field(MSG_TRANSPOSE_LABEL)
        await self.press(key_of(binding=keybindings.TrackEditor.MORE, key=Key.RIGHT_BRACKET))
        await self.check_undo_and_redo(before=before, after=self.data())
        await self.undo()
        self.assertIn(MSG_UNDONE.format(what=self.in_song(self.named(section=Section.TRACKS, name=LEAD))), self.text())

    async def test_undoing_a_rename_keeps_the_editor_on_the_track_under_its_old_name(self):
        await self.press(keybindings.MainPage.ARRANGE, Key.UP, Key.ENTER)
        await self.select_field(MSG_NAME_LABEL)
        await self.press(Key.ENTER)
        self.app.screen.value = RENAMED
        await self.press(Key.ENTER)
        await self.check_rename_follows(old=LEAD, new=RENAMED)

    async def test_undoing_the_copy_while_the_copys_editor_is_open_goes_back_to_arrange(self):
        await self.press(keybindings.MainPage.ARRANGE, Key.UP, keybindings.ArrangePage.COPY_TRACK, Key.ENTER)
        self.assertIsInstance(self.app.screen, TrackEditor)
        await self.check_undo_goes_back_to(ArrangePage)


class TestRegistersPageUndo(UndoTest):

    async def test_a_setting_is_one_step_and_the_cursor_stays(self):
        await self.press(keybindings.MainPage.REGISTERS)
        before = self.data()
        await self.select_field(MSG_REGISTER_FIELD_LABEL.format(name=RegisterName.BX, what=RegisterSetting.MAXIMUM))
        await self.press(key_of(binding=keybindings.RegistersPage.MORE, key=Key.RIGHT_BRACKET))
        await self.check_undo_and_redo(before=before, after=self.data())
        await self.undo()
        self.assertIn(MSG_UNDONE.format(what=self.in_song(self.named(section=Section.REGISTERS, name=RegisterName.BX))), self.text())


class TestEveryPageHasTestClasses(unittest.TestCase):
    """Every page has a test class named after it, and an undo test class here, so that a new page gets both."""

    def ui_test_class_names(self):
        """Return the names of every test class in the text UI test modules."""
        here = os.path.dirname(os.path.abspath(__file__))
        names = set()
        for file_name in os.listdir(here):
            if file_name.startswith(TEST_MODULE_PREFIX) and file_name.endswith(PYTHON_SUFFIX):
                module = importlib.import_module(file_name[:-len(PYTHON_SUFFIX)])
                names.update(name for name, member in inspect.getmembers(module, inspect.isclass) if issubclass(member, unittest.TestCase))
        return names

    def test_every_page_has_a_test_class_and_an_undo_test_class(self):
        names = self.ui_test_class_names()
        pages = leaf_pages()
        self.assertTrue(pages)
        for page in pages:
            with self.subTest(page=page.__name__):
                self.assertIn(TEST_PREFIX + page.__name__, names)
                self.assertIn(TEST_PREFIX + page.__name__ + UNDO_SUFFIX, names)


if __name__ == '__main__':
    unittest.main()
