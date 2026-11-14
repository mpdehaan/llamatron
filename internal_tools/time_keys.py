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
"""Time how long the tracker takes to answer one key press, page by page.

Run from the top folder, before and after a change that should make the tracker quicker:

    .venv/bin/python internal_tools/time_keys.py            # every place in PLACES, in milliseconds a key
    .venv/bin/python internal_tools/time_keys.py --profile  # the same, then where the slowest place's time goes

`internal_tools/time_keys.sh` runs the first. It opens examples/by_genre/electronic/minimal_techno.yml in the real tracker with no
terminal, presses the keys that reach each place, and then presses two keys that undo each other
over and over, so that the set ends as it began: an arrow one way and back, or `]` and `[` on a
value. Each press is handled and drawn before the next, which is everything the tracker does for
a key except Textual putting the drawing on the terminal. The best of several runs is shown,
since the best run is the one least disturbed by whatever else the computer was doing.
"""

import asyncio
import cProfile
import pathlib
import pstats
import sys
import timeit
from dataclasses import dataclass

from textual import events

from llamatron.tui import keybindings
from llamatron.tui.app import LlamatronApp
from llamatron.tui.document import Document
from llamatron.tui.key_table import first_key
from llamatron.tui.keys import Key

ROOT = pathlib.Path(__file__).resolve().parent.parent
SONG = ROOT / 'examples' / 'by_genre' / 'electronic' / 'minimal_techno.yml'
PROFILE_FLAG = '--profile'
# The terminal the keys are timed on, the same size as the screenshots.
COLUMNS = 112
ROWS = 32
# How many times each place's pair of keys is pressed in a run, and how many runs, the best of which is shown.
PAIRS = 20
RUNS = 5
KEYS_IN_A_PAIR = 2
MILLISECONDS = 1000
# How many functions the profile lists.
FUNCTIONS_SHOWN = 25
# Where the program's own files start in a path, so that the profile shows short names.
PACKAGE_MARK = 'llamatron/'
HEADING = '{name:52s} {time:>9s}'
ROW = '{name:52s} {time:9.2f}'
PLACE_COLUMN = 'one key press'
TIME_COLUMN = 'ms'
PROFILE_HEADING = 'where the time goes in {name}:'
# The third pattern of the song is a bass line, with more notes and rows than a drum pattern.
TO_BASS_PATTERN = [keybindings.MainPage.PATTERNS, Key.DOWN, Key.DOWN, Key.ENTER]
TO_BASS_ROWS = [*TO_BASS_PATTERN, keybindings.PatternEditor.TO_EDITOR]
# Velocity is the fifth row under Degree: Octave, the Basics heading, #/b, Chord and then Velocity.
ROWS_DOWN_TO_VELOCITY = 5


@dataclass(slots=True, kw_only=True)
class Place:
    """Somewhere in the tracker and a pair of keys to time there: the keys that reach it from the main screen, and two keys that undo each other."""

    name: str
    reach: list
    there: str
    back: str


def forward_key(binding):
    """Return the first key that steps a binding forward, the one the legend names."""
    steps, _, _ = binding
    return steps.forward[0]


def back_key(binding):
    """Return the first key that steps a binding back."""
    steps, _, _ = binding
    return steps.back[0]


MORE = forward_key(keybindings.PatternRow.ADJUST)
LESS = back_key(keybindings.PatternRow.ADJUST)
LONGER = forward_key(keybindings.PianoRoll.LENGTH)
SHORTER = back_key(keybindings.PianoRoll.LENGTH)

PLACES = [
    Place(name='main screen: move the cursor', reach=[], there=Key.RIGHT, back=Key.LEFT),
    Place(name='Patterns: move the cursor', reach=[keybindings.MainPage.PATTERNS], there=Key.DOWN, back=Key.UP),
    Place(name='Arrange: move the cursor between clips', reach=[keybindings.MainPage.ARRANGE, Key.RIGHT], there=Key.RIGHT, back=Key.LEFT),
    Place(name='Arrange: move the cursor between scenes', reach=[keybindings.MainPage.ARRANGE, Key.RIGHT], there=Key.DOWN, back=Key.UP),
    Place(name='piano roll: move the cursor a step', reach=TO_BASS_PATTERN, there=Key.RIGHT, back=Key.LEFT),
    Place(name='piano roll: move the cursor a row', reach=TO_BASS_PATTERN, there=Key.UP, back=Key.DOWN),
    Place(name='piano roll: make a note longer and shorter', reach=TO_BASS_PATTERN, there=LONGER, back=SHORTER),
    Place(name='rows: move the cursor a step', reach=TO_BASS_ROWS, there=Key.RIGHT, back=Key.LEFT),
    Place(name='rows: move the cursor a row', reach=TO_BASS_ROWS, there=Key.DOWN, back=Key.UP),
    Place(name='rows: step a degree up and down', reach=TO_BASS_ROWS, there=MORE, back=LESS),
    Place(name='rows: step a velocity up and down', reach=[*TO_BASS_ROWS, *[Key.DOWN] * ROWS_DOWN_TO_VELOCITY], there=MORE, back=LESS),
]


def key_event(name):
    """Return the event a terminal sends for a key: a key that types a character carries the character."""
    return events.Key(name, name if len(name) == 1 else None)


def press_pairs(*, app, place):
    """Press the place's two keys, one after the other, PAIRS times, each handled and drawn before the next."""
    for _ in range(PAIRS):
        app.screen.on_key(key_event(place.there))
        app.screen.on_key(key_event(place.back))


async def timed(*, place, profile):
    """Return the milliseconds one key press takes at a place, the best of several runs, profiling one more run if asked."""
    app = LlamatronApp(document=Document.load(str(SONG)))
    async with app.run_test(size=(COLUMNS, ROWS)) as pilot:
        await pilot.pause()
        for name in place.reach:
            await pilot.press(name if isinstance(name, str) else first_key(name))
            await pilot.pause()
        seconds = min(timeit.repeat(lambda: press_pairs(app=app, place=place), number=1, repeat=RUNS))
        if profile is not None:
            profile.runcall(press_pairs, app=app, place=place)
        return seconds * MILLISECONDS / (PAIRS * KEYS_IN_A_PAIR)


def show_profile(*, profile, name):
    """Print where the time went, the program's own functions first by the time spent inside each."""
    print()
    print(PROFILE_HEADING.format(name=name))
    statistics = pstats.Stats(profile)
    statistics.sort_stats(pstats.SortKey.CUMULATIVE).print_stats(PACKAGE_MARK, FUNCTIONS_SHOWN)


async def time_all(*, with_profile):
    print(HEADING.format(name=PLACE_COLUMN, time=TIME_COLUMN))
    times = {}
    for place in PLACES:
        times[place.name] = await timed(place=place, profile=None)
        print(ROW.format(name=place.name, time=times[place.name]))
    if with_profile:
        slowest = max(PLACES, key=lambda place: times[place.name])
        profile = cProfile.Profile()
        await timed(place=slowest, profile=profile)
        show_profile(profile=profile, name=slowest.name)


def main():
    asyncio.run(time_all(with_profile=PROFILE_FLAG in sys.argv[1:]))


if __name__ == '__main__':
    main()
