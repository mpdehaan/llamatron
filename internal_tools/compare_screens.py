# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Capture every page as the key tour draws it, at two sizes, and compare two captures, so that a change meant to leave the
screens alone, such as moving pages to declarative forms, is proved to leave every page's spacing, text and styles as they were.

Run from the top folder:

    .venv/bin/python internal_tools/compare_screens.py capture DIRECTORY   # every stop of the tour, at each size, into DIRECTORY
    .venv/bin/python internal_tools/compare_screens.py compare DIRECTORY   # capture again, and say where anything differs

The key tour (tests/interface/tracker/test_tui_help_keys.py) opens every page and walks its cursor to every place it can stand.
At each stop the screen is recorded as Textual composed it, dialogs over pages included: every line's text, cut where its style
changes, with the style beside each piece, so that a lost blank line, a column moved by one, or a word no longer dim is found.
The tour is run at 80 by 24, the smallest console a page must be good at, and at 160 by 50, a large one.
"""

import functools
import json
import os
import random
import sys
import unittest
from unittest import mock

from llamatron.wizards.create_song.wizard_choices import WizardChoices
from tests.interface.tracker.test_tui_help_keys import KeyTour
from tests.support.key_map import place_of

CAPTURE = 'capture'
COMPARE = 'compare'
USAGE = 'usage: compare_screens.py capture|compare DIRECTORY'
# The sizes the tour is run at: the smallest console a page must be good at, and a large one.
SIZES = ((80, 24), (160, 50))
FILE_NAME = 'screens_{columns}x{rows}.json'
# What the test's folder is written as.
FOLDER = 'FOLDER'
# What each stop of the tour records.
PAGE = 'page'
PLACE = 'place'
SCREEN = 'screen'
WRITE = 'w'
ENCODING = 'utf-8'
# The name of the screen tour at a size, and the class attribute that holds a test's size.
TOUR_NAME = 'ScreenTour{columns}x{rows}'
SIZE_ATTRIBUTE = 'SIZE'
SLOTS = '__slots__'
# The song wizard draws a new seed each time it opens, so that every song it makes differs; the tour draws from a fixed one,
# so that two runs plan the same song and the wizard's panels compare.
DRAW_SEED = 'draw_seed'
TOUR_SEED = 1
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
    """The key tour, recording the whole screen at every stop as well as the keys."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.stops = []
        seeded = functools.partialmethod(WizardChoices.draw_seed, dice=random.Random(TOUR_SEED))
        patcher = mock.patch.object(WizardChoices, DRAW_SEED, seeded)
        patcher.start()
        self.addCleanup(patcher.stop)

    def note(self):
        super().note()
        page = self.app.screen
        screen = screen_pieces(app=self.app, folders=(os.path.realpath(self.folder), self.folder))
        self.stops.append({PAGE: type(page).__name__, PLACE: place_of(page), SCREEN: screen})

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


def without_folders(*, text, folders):
    """Return text with each of the test's folders written as FOLDER, so that two runs compare."""
    for folder in folders:
        text = text.replace(folder, FOLDER)
    return text


def tour_class(size):
    """Return the screen tour at a size, as a class of its own, since a test's size is its class's."""
    return type(TOUR_NAME.format(columns=size[0], rows=size[1]), (ScreenTour,), {SIZE_ATTRIBUTE: size, SLOTS: ()})


def capture(directory):
    """Run the screen tour at every size, writing each size's stops into the directory; return whether every tour finished."""
    os.makedirs(directory, exist_ok=True)
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


def compare(directory):
    """Capture again beside the directory's capture and print where any stop's screen differs; return whether all are the same."""
    differing, stops = differences(before=directory, after=directory.rstrip(os.sep) + AGAIN)
    if differing is None:
        return False
    if not differing:
        print(MSG_SAME.format(stops=stops, sizes=len(SIZES)))
        return True
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
    if len(arguments) != 2 or arguments[0] not in (CAPTURE, COMPARE):
        print(USAGE)
        return FAILURE
    action, directory = arguments
    worked = capture(directory) if action == CAPTURE else compare(directory)
    return SUCCESS if worked else FAILURE


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
