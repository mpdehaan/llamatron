# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Capture every page as the key tour draws it, at two sizes, and compare two captures, so that a change meant to leave the
screens alone, such as moving pages to declarative forms, is proved to leave every page's spacing, text and styles as they were.

Run from the top folder:

    .venv/bin/python internal_tools/compare_screens.py capture DIRECTORY   # every stop of the tour, at each size, into DIRECTORY
    .venv/bin/python internal_tools/compare_screens.py compare DIRECTORY   # capture again, and say where anything differs
    .venv/bin/python internal_tools/compare_screens.py capture-dialogs DIRECTORY   # the dialogs alone, for a change to dialogs
    .venv/bin/python internal_tools/compare_screens.py compare-dialogs DIRECTORY   # the dialogs alone again, and what differs

The key tour (tests/interface/tracker/test_tui_help_keys.py) opens every page and walks its cursor to every place it can stand.
At each stop the screen is recorded as Textual composed it, dialogs over pages included: every line's text, cut where its style
changes, with the style beside each piece, so that a lost blank line, a column moved by one, or a word no longer dim is found.
The tour is run at 80 by 24, the smallest console a page must be good at, and at 160 by 50, a large one.

The dialogs are captured too, since the tour opens few of them: the UI tests that open dialogs are run, and the screen is
recorded the first time each test shows a dialog of each kind and title after a key, the dialog's own drawing alone, since a
page behind it may differ from run to run, so that moving a dialog to declarative forms is proved the same way.
"""

import functools
import hashlib
import json
import os
import random
import shutil
from rich.console import Console
import sys
from textual.screen import ModalScreen
from textual.widgets import Static
import unittest
from unittest import mock

from llamatron.interface.tracker.dialogs import dialog as dialog_values
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.dialogs.dialog import Dialog
from llamatron.interface.pages import generators as generators_values
from llamatron.interface.tracker.screens.arrange.arrange_page import ArrangePage
from llamatron.interface.tracker.screens.generators.generators_page import GeneratorsPage
from llamatron.interface.forms.nodes import Button, Toggle
from llamatron.user_strings import legends
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.interface.tracker.screens.shared.page import Page
from llamatron.wizards.create_song.wizard_choices import WizardChoices
from tests.interface.tracker import test_tui_help_keys
from tests.interface.tracker.test_tui_help_keys import KeyTour
from tests.support.key_map import place_of
from tests.support import key_map, ui_testing
from tests.support.ui_testing import UITest

CAPTURE = 'capture'
COMPARE = 'compare'
CAPTURE_DIALOGS = 'capture-dialogs'
COMPARE_DIALOGS = 'compare-dialogs'
USAGE = 'usage: compare_screens.py capture|compare|capture-dialogs|compare-dialogs DIRECTORY'
# The sizes the tour is run at: the smallest console a page must be good at, and a large one.
SIZES = ((80, 24), (160, 50))
FILE_NAME = 'screens_{columns}x{rows}.json'
# The dialogs' capture: the test modules that open dialogs, what each dialog's screen is kept by, the method of the tests that
# presses keys, after which a dialog on top is recorded, and what a comparison says of them.
DIALOGS_FILE = 'dialogs.json'
DIALOG_MODULES = (
    'tests.interface.tracker.test_tui_notes_page', 'tests.interface.tracker.test_tui_quitting', 'tests.interface.tracker.test_tui_settings_rows',
    'tests.interface.tracker.test_tui_progressions', 'tests.interface.visualizers.test_visualizer_choices', 'tests.interface.tracker.test_tui_piano_roll',
    'tests.interface.tracker.test_tui_keyswitches', 'tests.interface.tracker.test_tui_import', 'tests.interface.tracker.test_tui_corrections',
    'tests.interface.tracker.test_tui_lists', 'tests.interface.tracker.test_tui_arrange', 'tests.interface.tracker.test_tui_wizard',
    'tests.interface.tracker.test_tui_wizard_composition', 'tests.interface.tracker.test_tui_generator_type_picker', 'tests.interface.tracker.test_tui_patterns_page',
    'tests.interface.tracker.test_tui_file_page', 'tests.interface.tracker.test_tui_munge', 'tests.interface.tracker.test_tui_exporting',
)
DIALOG_KEY = '{test} | {dialog} | {title}'
PRESS = 'press'
MSG_DIALOGS_SAME = 'every dialog both captures hold is the same: {count} dialogs'
MSG_DIALOGS_DIFFERENT = '{count} dialogs differ; the first are:'
MSG_DIALOGS_KEPT = 'the dialogs captured differ: {before} before and {after} after, and only in one: {only}'
MSG_DIALOG = 'dialog {key}'
# What the test's folder is written as.
FOLDER = 'FOLDER'
# What each stop of the tour records.
PAGE = 'page'
PLACE = 'place'
SCREEN = 'screen'
KEYS = 'keys'
# The pages open at a stop, from the main screen up.
STACK = 'stack'
# The pages open as each key of a stop was pressed.
STACKS_BEFORE = 'stacks_before'
SETS_BEFORE = 'sets_before'
# The dialog trial waiting for the cursor's next move, and which fields' ENTER is tried: those that choose or edit.
WAITING_TRIAL = 'waiting_trial'
# The kinds of page whose help the tour has looked at.
HELPED = 'helped_pages'
WAITING_HELP = 'waiting_help'
# The page and place whose keys the tour tries at the next move, and the pages and places tried.
WAITING_KEYS = 'waiting_keys'
TRIED_KEYS = 'tried_keys'
# The keys the key trials leave alone: those that move, leave, play or open what the tour visits by itself.
UNTRIED_KEYS = ('up', 'down', 'left', 'right', 'tab', 'shift+tab', 'pageup', 'pagedown', 'home', 'end', 'escape', 'enter', 'space', 'q', 'f1', 'f2', 'f3')
CONTROL_PREFIX = 'ctrl+'
# What a key that plays or stops sound, or shows a visualizer, says it does, which the trials leave alone, since nothing plays
# in the tour and the visualizers come later.
PLAYING_WHATS = (legends.MSG_PLAY_WHAT, legends.MSG_PLAY_SONG_WHAT, legends.MSG_PLAY_SCENE_WHAT, legends.MSG_PLAY_CLIP_WHAT, legends.MSG_STOP_WHAT,
                 legends.MSG_STOP_CLIP_WHAT, legends.MSG_LISTEN_WHAT, legends.MSG_STOP_LISTENING_WHAT, legends.MSG_VISUALIZER_WHAT,
                 legends.MSG_STEP_VISUALIZER_WHAT)
UNTOGGLED = 'the key trial cannot take back {key} on {page} at {place}: leave it out of the trials'
OPENING_WHATS = (legends.What.CHOOSE, legends.What.EDIT)
MOST_ESCAPES = 4
# The file the set is written to at a stop where it changed, whether it holds unsaved changes, and the current song.
SET_FILE = 'set'
DIRTY = 'dirty'
SONG = 'song'
PATH = 'path'
SET_AT_STOP = '{tour}_set_{number}.yml'
# The set as a key left it, within a stop.
SET_AT_KEY = '{stop}_key_{key}.yml'
LAST_DIGEST = 'last_digest'
# The set the tour saves before its first stop and starts from.
TOUR_SET = test_tui_help_keys.TOUR_SET_FILE
# The most keys the tour presses to reach a generator on the Generators page, and the method it reaches one by.
MOST_KEYS_TO_A_GENERATOR = 100
PUT_CURSOR_ON = 'put_cursor_on'
# Arrange's cursor, by the attribute the tour sets and the arrows that move it back and forward, and what catches a setting.
ARRANGE_CURSOR = {'row': (Key.UP, Key.DOWN), 'column': (Key.LEFT, Key.RIGHT)}
SETATTR = '__setattr__'
TOUR_MODULE = 'test_tui_help_keys.py'
# What makes every key the tests press, which the tour notes.
KEY_EVENT = 'key_event'
WRITE = 'w'
ENCODING = 'utf-8'
# The name of the screen tour at a size, and the class attribute that holds a test's size.
TOUR_NAME = 'ScreenTour{columns}x{rows}'
SIZE_ATTRIBUTE = 'SIZE'
SLOTS = '__slots__'
# Where a comparison's new capture is made, beside the one before.
AGAIN = '_again'
# The environment variable the tour's stops are written through, since unittest makes the test object itself.
OUTPUT_SETTING = 'LLAMATRON_SCREENS_OUTPUT'
# How many differences are shown in full before the rest are only counted.
MOST_SHOWN = 10
MSG_SAME = 'every screen is the same: {stops} stops at {sizes} sizes'
MSG_DIFFERENT = '{count} stops differ; the first are:'
MSG_STOP = '{size} stop {number}: {page}, {place}'
MSG_LINE = '  line {line}:\n    before: {before}\n    after:  {after}'
MSG_STOPS_DIFFER = 'the tour stopped {before} times before and {after} times after at {size}: a page was added, removed or walked differently'
MSG_TOUR_FAILED = 'the tour failed at {size}, so the screens were not captured'
SUCCESS = 0
FAILURE = 1


def without_blanks(data):
    """Return a set's data without the settings it holds as nothing, which its file leaves out, so that an edit that changes
    only those counts as no change."""
    if isinstance(data, dict):
        return {key: without_blanks(value) for key, value in data.items() if value not in (None, {}, [])}
    if isinstance(data, list):
        return [without_blanks(item) for item in data]
    return data


class ScreenTour(KeyTour):
    """The key tour, recording the whole screen at every stop as well as the keys, and the keys pressed since the stop before,
    so that another program can press the same keys and be held to the same screens (internal_tools/compare_llamatron2.py)."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.stops = []
        self.pressed = []
        self.stacks_before = []
        self.sets_before = []
        original = ui_testing.key_event
        tour = self

        def noted(name):
            event = original(name)
            # The pages open as the key is pressed, so that another program can follow them where its pages that the key
            # reaches are not ported yet.
            self.pressed.append(event.key)
            self.stacks_before.append(tour.open_now())
            # The set as the last key left it, where that key changed it, so that another program that pressed the key on
            # a page or dialog not ported yet takes it up before the next.
            document = self.app.get_document()
            self.sets_before.append((self.set_kept(document, key=len(self.pressed)), document.is_dirty(), document.get_current_song_name()))
            return event

        patcher = mock.patch.object(ui_testing, KEY_EVENT, noted)
        patcher.start()
        self.addCleanup(patcher.stop)
        # The tour puts the Generators page's cursor on a generator without keys; here it goes there by keys, so that another
        # program pressing the same keys reaches it too.

        def by_keys(page, *, kind, name):
            tour.walk_to_generator(page=page, kind=kind, name=name)

        patcher = mock.patch.object(GeneratorsPage, PUT_CURSOR_ON, by_keys)
        patcher.start()
        self.addCleanup(patcher.stop)
        # The tour puts Arrange's cursor on a cell by setting its row and column; here the arrows take it there.
        original_setattr = ArrangePage.__setattr__

        def by_arrows(page, name, value):
            if name in ARRANGE_CURSOR and sys._getframe(1).f_code.co_filename.endswith(TOUR_MODULE):
                tour.arrows_to(page=page, name=name, value=value)
                return
            original_setattr(page, name, value)

        patcher = mock.patch.object(ArrangePage, SETATTR, by_arrows)
        patcher.start()
        self.addCleanup(patcher.stop)

    def arrows_to(self, *, page, name, value):
        """Move Arrange's cursor by arrows until its row or its column is the value the tour set."""
        back, forward = ARRANGE_CURSOR[name]
        for _ in range(MOST_KEYS_TO_A_GENERATOR):
            here = getattr(page, name)
            if here == value:
                return
            self.press_at_once(back if value < here else forward)

    def walk_to_generator(self, *, page, kind, name):
        """Move the Generators page's cursor to a generator by keys, as a person would: PgUp or PgDn to its kind's heading,
        Space to open the kind where it is closed, then Down to the generator."""
        kinds = page.kinds()
        for _ in range(MOST_KEYS_TO_A_GENERATOR):
            listed = page.listed()
            if listed.row == generators_values.GENERATOR and listed.kind == kind and listed.name == name:
                return
            if listed.kind == kind and listed.row == generators_values.HEADING and page.is_closed(kind):
                self.press_at_once(Key.SPACE)
            elif listed.kind == kind:
                self.press_at_once(Key.DOWN)
            elif listed.kind is None or kinds.index(listed.kind) > kinds.index(kind):
                self.press_at_once(Key.PAGE_UP)
            else:
                self.press_at_once(Key.PAGE_DOWN)

    def note(self):
        super().note()
        self.record_stop()
        self.try_an_edit()
        page = self.app.screen
        if isinstance(page, Page):
            self.waiting_help = page
        if isinstance(page, Page) and not isinstance(page, FieldPage):
            self.waiting_keys = (page, key_map.place_of(page))
        self.waiting_trial = (page, page.cell_field()) if isinstance(page, FieldPage) else None

    async def go(self, name):
        await self.try_the_help()
        await self.try_the_keys()
        await self.try_a_dialog()
        return await super().go(name)

    async def try_a_dialog(self):
        """At the field noted last, while the cursor is still on it, press ENTER where the field chooses or edits and stop
        on the dialog or page it opens, then press ESC until the page is back, so that another program is held to every
        picker and prompt a field opens."""
        waiting = getattr(self, WAITING_TRIAL, None)
        self.waiting_trial = None
        if waiting is None:
            return
        page, field = waiting
        if self.app.screen is not page or page.takes_text() or page.cell_field() is not field or field is None:
            return
        if getattr(field, 'enter', None) is None or field.enter_what not in OPENING_WHATS or isinstance(field, Button):
            return
        document = self.app.get_document()
        before = without_blanks(document.get_setlist().to_data())
        await self.press(Key.ENTER)
        if self.app.screen is page:
            if without_blanks(document.get_setlist().to_data()) != before:
                self.record_stop()
                await self.press(Key.CTRL_Z)
                self.record_stop()
            return
        self.record_stop()
        for _ in range(MOST_ESCAPES):
            if self.app.screen is page:
                break
            await self.press(Key.ESCAPE)
        self.assertIs(self.app.screen, page)
        if without_blanks(document.get_setlist().to_data()) != before:
            await self.press(Key.CTRL_Z)

    async def try_the_help(self):
        """On the first stop at each kind of page, press F1 and stop on each of the help's two panels, then close it, so that
        another program is held to every page's help. About is left out, since it shows a quote chosen at random."""
        page = self.__dict__.pop(WAITING_HELP, None)
        helped = self.__dict__.setdefault(HELPED, set())
        if page is None or self.app.screen is not page or page.takes_text() or type(page).__name__ in helped:
            return
        helped.add(type(page).__name__)
        await self.press(Key.F1)
        if self.app.screen is page:
            return
        self.record_stop()
        await self.press(Key.TAB)
        self.record_stop()
        for _ in range(MOST_ESCAPES):
            if self.app.screen is page:
                break
            await self.press(Key.ESCAPE)
        self.assertIs(self.app.screen, page)

    async def try_the_keys(self):
        """On a page other than a settings page, at the first stop at each kind of place on it, press each of the page's keys
        that edits or opens something there, and stop wherever the key changed the screen: a key that opens a dialog or a page
        is followed by ESC until the page is back, a key that changed what the file holds by CTRL+Z and a stop after it, and a
        key that left the page typing, searching or carrying something by ESC, so that another program is held to every key of every
        page. Moving, leaving, playing and the everywhere keys are left to the tour."""
        page, place = self.__dict__.pop(WAITING_KEYS, (None, None))
        tried = self.__dict__.setdefault(TRIED_KEYS, set())
        if page is None or self.app.screen is not page or page.takes_text() or (type(page).__name__, place) in tried:
            return
        tried.add((type(page).__name__, place))
        document = self.app.get_document()
        for item in page.page_key_table():
            if self.app.screen is not page or key_map.place_of(page) != place:
                return
            # A stepping key is tried forward, as ] is on a settings page.
            key = item.keys[-1] if item.steps else item.keys[0]
            if item.wants_key or key in UNTRIED_KEYS or key.startswith(CONTROL_PREFIX) or item.what in PLAYING_WHATS or item.binding is keybindings.MainPage.WIZARD:
                continue
            before_data = without_blanks(document.get_setlist().to_data())
            before_dirty = document.is_dirty()
            before_screen = screen_pieces(app=self.app, folders=(os.path.realpath(self.folder), self.folder))
            await self.press(key)
            if os.environ.get('TOUR_DEBUG'):
                with open(os.environ['TOUR_DEBUG'], 'a') as log:
                    print('trial', type(page).__name__, place, key, type(self.app.screen).__name__, self.open_now(), file=log)
            if self.app.screen is not page:
                self.record_stop()
                for _ in range(MOST_ESCAPES):
                    if self.app.screen is page:
                        break
                    await self.press(Key.ESCAPE)
                if self.app.screen is not page:
                    return
                if without_blanks(document.get_setlist().to_data()) != before_data:
                    await self.press(Key.CTRL_Z)
                    self.record_stop()
                continue
            if without_blanks(document.get_setlist().to_data()) != before_data or document.is_dirty() != before_dirty:
                self.record_stop()
                await self.press(Key.CTRL_Z)
                self.record_stop()
                continue
            if page.takes_text() or key_map.place_of(page) in (key_map.MOVING, key_map.SEARCHING):
                self.record_stop()
                await self.press(Key.ESCAPE)
                self.record_stop()
                continue
            if screen_pieces(app=self.app, folders=(os.path.realpath(self.folder), self.folder)) != before_screen:
                self.record_stop()
                # A key that only says something on the status line is done with, as the next key clears the line in both
                # programs.
                status = page.holder.get_status_line()
                if not status.is_empty():
                    status.clear()
                    page.draw()
                    await self.settle()
                    if screen_pieces(app=self.app, folders=(os.path.realpath(self.folder), self.folder)) == before_screen:
                        continue
                # A key that changes only what the page shows is taken back: a stepping key by its back key, a toggle by itself.
                # A key that moved the cursor cannot be taken back so; the other program presses the same keys, so the two stay
                # in step, and the trials at this place end, since the cursor is elsewhere.
                await self.press(item.keys[0] if item.steps else key)
                if screen_pieces(app=self.app, folders=(os.path.realpath(self.folder), self.folder)) != before_screen:
                    self.record_stop()
                    return

    def try_an_edit(self):
        """On a settings field, try each edit it takes that keeps to the page: ] where its value steps, Bksp where it clears and
        Space where it is a toggle; where an edit changed what the file holds, stop, press CTRL+Z and stop again, so that
        another program is held to what each edit shows and to undoing it, and the tour goes on from the set as it was."""
        page = self.app.screen
        if not isinstance(page, FieldPage) or page.takes_text():
            return
        field = page.cell_field()
        if field is None:
            return
        edits = []
        if getattr(field, 'adjust', None) is not None:
            edits.append(Key.RIGHT_BRACKET)
        if getattr(field, 'clear', None) is not None:
            edits.append(Key.BACKSPACE)
        if isinstance(field, Toggle):
            edits.append(Key.SPACE)
        for key in edits:
            self.try_a_key(key)

    def try_a_key(self, key):
        """Press an editing key and, where it changed what the file holds, stop, undo it and stop again. A key that opens a
        dialog or a page is taken back whole: what it opened is closed, its change undone and the key left out of the record,
        since the tour cannot answer a dialog between its stops."""
        document = self.app.get_document()
        page = self.app.screen
        before = without_blanks(document.get_setlist().to_data())
        recorded = (len(self.pressed), len(self.stacks_before), len(self.sets_before))
        self.press_at_once(key)
        if self.app.screen is not page:
            while self.app.screen is not page:
                self.app.pop_screen()
            if without_blanks(document.get_setlist().to_data()) != before:
                document.undo()
            del self.pressed[recorded[0]:], self.stacks_before[recorded[1]:], self.sets_before[recorded[2]:]
            return
        if without_blanks(document.get_setlist().to_data()) == before:
            return
        self.record_stop()
        self.press_at_once(Key.CTRL_Z)
        self.record_stop()

    def record_stop(self):
        """Record the screen at a stop, with the keys pressed since the stop before."""
        page = self.app.screen
        # The set the tour starts from, saved before its first stop, kept beside the stops for another program to open.
        kept = os.path.join(os.path.dirname(os.environ[OUTPUT_SETTING]), TOUR_SET)
        if not self.stops:
            shutil.copyfile(os.path.join(self.folder, TOUR_SET), kept)
        screen = screen_pieces(app=self.app, folders=(os.path.realpath(self.folder), self.folder))
        stack = self.open_now()
        document = self.app.get_document()
        self.stops.append({
            PAGE: type(page).__name__, PLACE: place_of(page), SCREEN: screen, KEYS: self.pressed, STACK: stack,
            SET_FILE: self.set_kept(document), DIRTY: document.is_dirty(), SONG: document.get_current_song_name(), STACKS_BEFORE: self.stacks_before, SETS_BEFORE: self.sets_before,
            PATH: without_folders(text=document.get_path() or '', folders=(os.path.realpath(self.folder), self.folder)),
        })
        self.pressed = []
        self.stacks_before = []
        self.sets_before = []

    def open_now(self):
        """Return the names of the pages and dialogs open, from the main screen up."""
        return [type(each).__name__ for each in self.app.screen_stack if isinstance(each, (Page, ModalScreen))]

    def set_kept(self, document, key=None):
        """Return the name of the file the set is written to where it changed since the stop before, so that another program
        whose pages that changed it are not ported yet can take it up, or None where it is as it was."""
        data = document.get_setlist().to_data()
        digest = hashlib.sha1(json.dumps(data, sort_keys=True, default=str).encode(ENCODING)).hexdigest()
        if digest == getattr(self, LAST_DIGEST, None):
            return None
        self.last_digest = digest
        name = SET_AT_STOP.format(tour=os.path.splitext(os.path.basename(os.environ[OUTPUT_SETTING]))[0], number=len(self.stops))
        if key is not None:
            name = SET_AT_KEY.format(stop=os.path.splitext(name)[0], key=key)
        document.get_setlist().write_file(os.path.join(os.path.dirname(os.environ[OUTPUT_SETTING]), name))
        return name

    async def test_the_tour(self):
        await self.tour()
        with open(os.environ[OUTPUT_SETTING], WRITE, encoding=ENCODING) as file:
            json.dump(self.stops, file, indent=0)


def screen_pieces(*, app, folders):
    """Return every line of what Textual shows, each a list of its pieces of text with the style each is drawn in, the test's
    folder, which has a new name each run, written as FOLDER."""
    lines = []
    for strip in app.screen._compositor.render_strips():
        lines.append([[without_folders(text=segment.text, folders=folders), str(segment.style) if segment.style else ''] for segment in strip])
    return lines


def dialog_pieces(*, dialog, folders):
    """Return the dialog's own drawing, its box and what is inside it, without the page behind it, which a test may draw
    differently each run: every line's pieces of text, each with the style it is drawn in, whether the style is the line's or a
    stretch's, the test's folder written as FOLDER."""
    drawn = dialog.query_one(dialog_values.DIALOG_VIEW_SELECTOR, Static).content
    console = Console()
    lines = []
    for line in drawn.split():
        lines.append([[without_folders(text=segment.text, folders=folders), str(segment.style) if segment.style else ''] for segment in line.render(console)])
    return lines


def without_folders(*, text, folders):
    """Return text with each of the test's folders written as FOLDER, so that two runs compare."""
    for folder in folders:
        text = text.replace(folder, FOLDER)
    return text


def tour_class(size):
    """Return the screen tour at a size, as a class of its own, since a test's size is its class's."""
    return type(TOUR_NAME.format(columns=size[0], rows=size[1]), (ScreenTour,), {SIZE_ATTRIBUTE: size, SLOTS: ()})


def capture(directory):
    """Run the screen tour at every size, writing each size's stops into the directory, and capture the dialogs; return whether
    every tour finished."""
    os.makedirs(directory, exist_ok=True)
    capture_dialogs(directory)
    for size in SIZES:
        os.environ[OUTPUT_SETTING] = os.path.join(directory, FILE_NAME.format(columns=size[0], rows=size[1]))
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(tour_class(size))
        with open(os.devnull, WRITE) as nowhere:
            result = unittest.TextTestRunner(stream=nowhere).run(suite)
        if not result.wasSuccessful():
            print(MSG_TOUR_FAILED.format(size=size))
            for _, trace in result.errors + result.failures:
                print(trace)
            return False
    return True


def capture_dialogs(directory):
    """Run the tests that open dialogs, recording the screen the first time each test shows a dialog of each kind and title
    after a key, the wizard's seed drawn from the tour's, and write them into the directory."""
    seen = {}
    pressed = UITest.press

    async def press(test, *keys):
        result = await pressed(test, *keys)
        screen = test.app.screen
        if isinstance(screen, Dialog):
            key = DIALOG_KEY.format(test=test.id(), dialog=type(screen).__name__, title=getattr(screen, 'title', None))
            if key not in seen:
                seen[key] = dialog_pieces(dialog=screen, folders=(os.path.realpath(test.folder), test.folder))
        return result
    seeded = functools.partialmethod(WizardChoices.draw_seed, dice=random.Random(test_tui_help_keys.TOUR_SEED))
    with mock.patch.object(UITest, PRESS, press), mock.patch.object(WizardChoices, test_tui_help_keys.DRAW_SEED, seeded):
        suite = unittest.defaultTestLoader.loadTestsFromNames(DIALOG_MODULES)
        with open(os.devnull, WRITE) as nowhere:
            unittest.TextTestRunner(stream=nowhere).run(suite)
    with open(os.path.join(directory, DIALOGS_FILE), WRITE, encoding=ENCODING) as file:
        json.dump(seen, file, indent=0, sort_keys=True)


def compare_dialogs(*, before, after):
    """Print the dialogs that differ between two captures; return whether every dialog is the same."""
    old = read_stops(os.path.join(before, DIALOGS_FILE))
    new = read_stops(os.path.join(after, DIALOGS_FILE))
    only = sorted(set(old) ^ set(new))
    if only:
        # A dialog whose title changed is kept under another name; the rest are still compared.
        print(MSG_DIALOGS_KEPT.format(before=len(old), after=len(new), only=only[:MOST_SHOWN]))
    differing = [key for key in sorted(set(old) & set(new)) if old[key] != new[key]]
    if not differing:
        print(MSG_DIALOGS_SAME.format(count=len(set(old) & set(new))))
        return not only
    print(MSG_DIALOGS_DIFFERENT.format(count=len(differing)))
    for key in differing[:MOST_SHOWN]:
        print(MSG_DIALOG.format(key=key))
        for line, (was, now) in enumerate(zip(old[key], new[key])):
            if was != now:
                print(MSG_LINE.format(line=line, before=was, after=now))
                break
    return False


def compare(directory):
    """Capture again beside the directory's capture and print where any stop's or dialog's screen differs; return whether all
    are the same."""
    again = directory.rstrip(os.sep) + AGAIN
    differing, stops = differences(before=directory, after=again)
    if differing is None:
        return False
    dialogs_same = compare_dialogs(before=directory, after=again)
    if not differing:
        print(MSG_SAME.format(stops=stops, sizes=len(SIZES)))
        return dialogs_same
    print(MSG_DIFFERENT.format(count=len(differing)))
    for size, number, old, new in differing[:MOST_SHOWN]:
        show_difference(size=size, number=number, old=old, new=new)
    return False


def differences(*, before, after):
    """Capture into after, then return the stops whose screens differ from before's, each (size, number, old, new), and how
    many stops a size has; or None for the differences where the capture failed or the tour stopped a different number of times."""
    if not capture(after):
        return None, 0
    differing = []
    stops = 0
    for size in SIZES:
        name = FILE_NAME.format(columns=size[0], rows=size[1])
        old_stops = read_stops(os.path.join(before, name))
        new_stops = read_stops(os.path.join(after, name))
        if len(old_stops) != len(new_stops):
            print(MSG_STOPS_DIFFER.format(before=len(old_stops), after=len(new_stops), size=size))
            return None, 0
        stops = len(old_stops)
        differing += [(size, number, old, new) for number, (old, new) in enumerate(zip(old_stops, new_stops)) if old != new]
    return differing, stops


def read_stops(path):
    with open(path, encoding=ENCODING) as file:
        return json.load(file)


def show_difference(*, size, number, old, new):
    """Print a stop that differs and its first line that differs, as text with each piece's style."""
    print(MSG_STOP.format(size=size, number=number, page=new[PAGE], place=new[PLACE]))
    for line, (before, after) in enumerate(zip(old[SCREEN], new[SCREEN])):
        if before != after:
            print(MSG_LINE.format(line=line, before=before, after=after))
            return


def main(arguments):
    if len(arguments) != 2 or arguments[0] not in ACTIONS:
        print(USAGE)
        return FAILURE
    action, directory = arguments
    return SUCCESS if ACTIONS[action](directory) else FAILURE


def capture_dialogs_alone(directory):
    """Capture the dialogs alone, with no tour of the pages, for a change that touches only dialogs."""
    os.makedirs(directory, exist_ok=True)
    capture_dialogs(directory)
    return True


def compare_dialogs_alone(directory):
    """Capture the dialogs again beside the directory's capture, with no tour of the pages, and say where any differs."""
    again = directory.rstrip(os.sep) + AGAIN
    capture_dialogs_alone(again)
    return compare_dialogs(before=directory, after=again)


# What each action of the command line does.
ACTIONS = {CAPTURE: capture, COMPARE: compare, CAPTURE_DIALOGS: capture_dialogs_alone, COMPARE_DIALOGS: compare_dialogs_alone}


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
