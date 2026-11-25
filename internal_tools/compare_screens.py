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
from textual.widgets import Static
import unittest
from unittest import mock

from llamatron.interface.tracker.dialogs import dialog as dialog_values
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.dialogs.dialog import Dialog
from llamatron.interface.pages import generators as generators_values
from llamatron.interface.tracker.screens.generators.generators_page import GeneratorsPage
from llamatron.interface.tracker.screens.shared.page import Page
from llamatron.wizards.create_song.wizard_choices import WizardChoices
from tests.interface.tracker import test_tui_help_keys
from tests.interface.tracker.test_tui_help_keys import KeyTour
from tests.support.key_map import place_of
from tests.support import ui_testing
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
# The file the set is written to at a stop where it changed, whether it holds unsaved changes, and the current song.
SET_FILE = 'set'
DIRTY = 'dirty'
SONG = 'song'
PATH = 'path'
SET_AT_STOP = '{tour}_set_{number}.yml'
LAST_DIGEST = 'last_digest'
# The set the tour saves before its first stop and starts from.
TOUR_SET = test_tui_help_keys.TOUR_SET_FILE
# The most keys the tour presses to reach a generator on the Generators page, and the method it reaches one by.
MOST_KEYS_TO_A_GENERATOR = 100
PUT_CURSOR_ON = 'put_cursor_on'
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


class ScreenTour(KeyTour):
    """The key tour, recording the whole screen at every stop as well as the keys, and the keys pressed since the stop before,
    so that another program can press the same keys and be held to the same screens (internal_tools/compare_llamatron2.py)."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.stops = []
        self.pressed = []
        self.stacks_before = []
        original = ui_testing.key_event

        def noted(name):
            event = original(name)
            # The pages open as the key is pressed, so that another program can follow them where its pages that the key
            # reaches are not ported yet.
            stack = [type(each).__name__ for each in self.app.screen_stack if isinstance(each, Page)]
            self.pressed.append(event.key)
            self.stacks_before.append(stack)
            return event

        patcher = mock.patch.object(ui_testing, KEY_EVENT, noted)
        patcher.start()
        self.addCleanup(patcher.stop)
        # The tour puts the Generators page's cursor on a generator without keys; here it goes there by keys, so that another
        # program pressing the same keys reaches it too.
        tour = self

        def by_keys(page, *, kind, name):
            tour.walk_to_generator(page=page, kind=kind, name=name)

        patcher = mock.patch.object(GeneratorsPage, PUT_CURSOR_ON, by_keys)
        patcher.start()
        self.addCleanup(patcher.stop)

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
        page = self.app.screen
        # The set the tour starts from, saved before its first stop, kept beside the stops for another program to open.
        kept = os.path.join(os.path.dirname(os.environ[OUTPUT_SETTING]), TOUR_SET)
        if not self.stops:
            shutil.copyfile(os.path.join(self.folder, TOUR_SET), kept)
        screen = screen_pieces(app=self.app, folders=(os.path.realpath(self.folder), self.folder))
        stack = [type(each).__name__ for each in self.app.screen_stack if isinstance(each, Page)]
        document = self.app.get_document()
        self.stops.append({
            PAGE: type(page).__name__, PLACE: place_of(page), SCREEN: screen, KEYS: self.pressed, STACK: stack,
            SET_FILE: self.set_kept(document), DIRTY: document.is_dirty(), SONG: document.get_current_song_name(), STACKS_BEFORE: self.stacks_before,
            PATH: without_folders(text=document.get_path() or '', folders=(os.path.realpath(self.folder), self.folder)),
        })
        self.pressed = []
        self.stacks_before = []

    def set_kept(self, document):
        """Return the name of the file the set is written to where it changed since the stop before, so that another program
        whose pages that changed it are not ported yet can take it up, or None where it is as it was."""
        data = document.get_setlist().to_data()
        digest = hashlib.sha1(json.dumps(data, sort_keys=True, default=str).encode(ENCODING)).hexdigest()
        if digest == getattr(self, LAST_DIGEST, None):
            return None
        self.last_digest = digest
        name = SET_AT_STOP.format(tour=os.path.splitext(os.path.basename(os.environ[OUTPUT_SETTING]))[0], number=len(self.stops))
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
