# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Every key of every page is shown in its legend or in the F1 dialog, on a large console and a usual one."""

from llamatron.engine.generators import arp as arp_plugin
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.dialogs.dialog import Dialog
from llamatron.interface.tracker.dialogs.help_dialog import HelpDialog
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.set.main_page import MainPage
from llamatron.model.schema.file_format import ClipSlotSetting, Direction, Section, SetlistSetting
from llamatron.user_strings import labels
from tests.support import ui_testing
from tests.support.ui_testing import UITest

MAIN = 'main'
FILE = 'file'
SONGS = 'songs'
SONG = 'song'
NOTES_EDITING = 'notes editing'
PATTERN_EDITOR = 'pattern editor'
PATTERN_ROWS = 'pattern rows'
CHAIN_EDITOR = 'chain editor'
GENERATORS = 'generators'
ARRANGE = 'arrange'
ARRANGE_CELL = 'arrange cell'
ARRANGE_TRACK = 'arrange track'
ARRANGE_CORNER = 'arrange corner'
ARRANGE_TRACK_PLUS = 'arrange track plus'
TRACK_EDITOR = 'track editor'
CLIP = 'clip'
SCENE = 'scene'
SONG_FIELD = 'song field'
FILE_FIELD = 'file field'
PATTERN_ROW = 'pattern row'
LEAD = 'lead'
DRUMS = 'drums'
OTHER = 'other'
UNBOUND_LETTERS = ('j', 'k')
SCALE = 'SCALE'
GROOVE_EDITOR = 'GROOVE_EDITOR'
INSTRUMENT_EDITOR = 'INSTRUMENT_EDITOR'


class EveryKeyIsShownTests:
    """The checks of every page's keys, run by two classes that each walk half of the pages, so that the walk is split between two processes."""

    async def visit(self):
        raise NotImplementedError

    async def test_every_key_in_the_table_is_on_screen_or_in_the_help_dialog(self):
        async for where in self.visit():
            page = self.app.screen
            text = self.text()
            for item in page.shown_keys():
                with self.subTest(where=where, label=item.shown_label()):
                    self.assertIn(f'« {item.shown_label()} »', text)
            if not any(item.binding is keybindings.Page.HELP for item in page.key_table()):
                continue
            await self.press(keybindings.Page.HELP)
            self.assertIsInstance(self.app.screen, HelpDialog, where)
            text = self.text()
            for item in page.key_table():
                # F1 is the one key its own dialog doesn't list: whoever reads the dialog pressed it.
                if item.binding is keybindings.Page.HELP:
                    continue
                with self.subTest(where=where, label=item.shown_label()):
                    self.assertIn(f'« {item.shown_label()} »', text)
            # The dialog fits: its bottom edge is on the screen, on both panels.
            self.assertIn('┗', text, where)
            await self.press(Key.TAB)
            self.assertIn('┗', self.text(), where)
            await self.press(Key.ESCAPE)
            self.assertIs(self.app.screen, page, where)

    async def test_a_key_that_is_not_shown_does_nothing(self):
        await self.press(keybindings.MainPage.PATTERNS)
        before = self.text()
        await self.press(*UNBOUND_LETTERS, Key.F4)
        self.assertEqual(self.text(), before)

    async def test_no_key_table_is_empty(self):
        async for where in self.visit():
            with self.subTest(where=where):
                self.assertTrue(self.app.screen.keys())

    async def test_every_legend_starts_with_esc_and_a_hidden_key_is_listed_only_by_f1(self):
        async for where in self.visit():
            page = self.app.screen
            # The main screen has nowhere to go back to, and a dialog's legend is its own.
            if isinstance(page, (Dialog, MainPage)):
                continue
            with self.subTest(where=where):
                self.assertEqual(page.shown_keys()[0].keys, (Key.ESCAPE,))
                hidden = [item for item in page.keys() if not item.shown]
                for item in hidden:
                    self.assertNotIn(f'« {item.shown_label()} »', self.text(), item.shown_label())
                self.assertEqual([item for item in page.shown_keys() if not item.shown], [])


class TestEveryKeyIsShownOnTheSetPages(EveryKeyIsShownTests, UITest):
    """The main screen, File, Description, Songs, Song, Patterns and the pattern editor."""

    async def visit(self):
        yield MAIN
        await self.press(keybindings.MainPage.FILE)
        yield FILE
        for _ in range(5):
            await self.press(Key.DOWN)
            yield FILE_FIELD
        await self.select_field(labels.MSG_NOTES_LABEL)
        await self.press(Key.ENTER)
        yield NOTES_EDITING
        await self.press(Key.ESCAPE)
        yield SetlistSetting.NOTES
        await self.press(Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.SONGS)
        yield SONGS
        await self.press(Key.ENTER)
        yield SONG
        for _ in range(2):
            await self.press(Key.DOWN)
            yield SONG_FIELD
        await self.press(Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.PATTERNS)
        yield Section.PATTERNS
        await self.press(Key.ENTER)
        yield PATTERN_EDITOR
        await self.press(keybindings.PatternEditor.TO_EDITOR)
        yield PATTERN_ROWS
        for _ in range(8):
            await self.press(Key.DOWN)
            yield PATTERN_ROW


class TestEveryKeyIsShownOnTheSongPages(EveryKeyIsShownTests, UITest):
    """Generators, a chain's editor, Scales, Grooves, Arrange and the pages under them."""

    async def visit(self):
        await self.open_chain(ui_testing.NAMED)
        yield CHAIN_EDITOR
        await self.press(Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.GENERATORS)
        yield GENERATORS
        await self.press(Key.ENTER)
        yield arp_plugin.NAME
        await self.press(Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.SCALES)
        yield Section.SCALES
        await self.press(Key.ENTER)
        yield SCALE
        await self.press(Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.GROOVES)
        yield Section.GROOVES
        await self.press(Key.ENTER)
        yield GROOVE_EDITOR
        await self.press(Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.INSTRUMENTS, keybindings.InstrumentsPage.ADD)
        yield INSTRUMENT_EDITOR
        await self.press(Key.ESCAPE)
        yield Section.INSTRUMENTS
        await self.press(Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.ARRANGE)
        yield ARRANGE
        # The instrument added above turned Real Time on, so the corner over the scene names is there, and Up from the first scene's name reaches it.
        await self.press(Key.UP)
        yield ARRANGE_CORNER
        await self.press(Key.RIGHT)
        yield ARRANGE_TRACK
        await self.press(Key.RIGHT, Key.RIGHT)
        yield ARRANGE_TRACK_PLUS
        await self.press(Key.ENTER, Key.LEFT, Key.LEFT, Key.ENTER)
        yield TRACK_EDITOR
        await self.press(Key.ESCAPE, Key.DOWN, Key.RIGHT)
        yield ARRANGE_CELL
        await self.press(Key.ENTER)
        yield CLIP
        await self.press(Key.ESCAPE, Key.LEFT, Key.ENTER)
        yield SCENE


class TestEveryKeyIsShownOnTheSetPagesOnAUsualConsole(TestEveryKeyIsShownOnTheSetPages):
    SIZE = (80, 24)


class TestEveryKeyIsShownOnTheSongPagesOnAUsualConsole(TestEveryKeyIsShownOnTheSongPages):
    SIZE = (80, 24)

    async def test_a_long_line_cannot_push_the_keys_off_the_screen(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.LOOP, value=True)
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.GRAB_TRACK, value=DRUMS)
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.DIRECTION, value=Direction.EITHERWAY)
        self.document.set_clip_slot_setting(index=0, track=DRUMS, setting=ClipSlotSetting.LOOP, value=None)
        self.document.set_clip_slot_setting(index=0, track=DRUMS, setting=ClipSlotSetting.PATTERN, value=OTHER)
        await self.press(keybindings.MainPage.ARRANGE, Key.RIGHT, Key.ENTER)
        self.assertIn('« ESC »', self.text())
        self.assertEqual(self.text().count('\n'), 23)
