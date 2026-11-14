#!/usr/bin/env python3
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

"""Time how long each example takes to render, and how many objects a render makes.

Run from the top folder, before and after a change that should make rendering faster:

    .venv/bin/python internal_tools/time_renders.py            # every example, with the best of several renders each
    .venv/bin/python internal_tools/time_renders.py --profile  # the same, then where the slowest example's time goes

`internal_tools/time.sh` runs the first. Each example is rendered with one seed, so that the same notes are
made every time, and the best of several runs is shown, since the best run is the one least
disturbed by whatever else the computer was doing. The counts say how many times each kind of
object was made during one render, which is what real-time playback has to keep small.
"""

import cProfile
import os
import pstats
import sys
import timeit

from llamatron.composition.setlist import Setlist
from llamatron.playback.song_renderer import SongRenderer
from llamatron.support.example_sets import example_sets

PROFILE_FLAG = '--profile'
# The seed every timed render uses, so that probability rolls the same way each time.
SEED = 1
# How many times each example is rendered, the best of which is shown.
RUNS = 7
MILLISECONDS = 1000
PERCENT = 100
# How many functions the profile lists.
FUNCTIONS_SHOWN = 20
# Where the program's own files start in a path, so that the profile shows short names.
PACKAGE_MARK = 'llamatron/'
# What makes an object: a class's constructor, and the function that makes a note from values already checked.
CONSTRUCTORS = ('__init__', 'note_of_checked_values')
HEADING = '{name:34s} {time:>9s} {calls:>9s}'
ROW = '{name:34s} {time:9.1f} {calls:9d}'
TOTAL_NAME = 'every example'
EXAMPLE_COLUMN = 'example'
TIME_COLUMN = 'ms'
CALLS_COLUMN = 'calls'
MADE_HEADING = 'objects made in one render of {name}:'
MADE_ROW = '  {kind:28s} {count:8d}'
PROFILE_HEADING = 'where the time goes in {name}:'
PROFILE_ROW = '  {share:5.1f}%  {calls:8d} calls  {where}:{function}'


def songs_of(path):
    """Return every song of an example set."""
    setlist = Setlist.read_file(path)
    return [setlist.get_song(name) for name in setlist.get_song_names()]


def render_all(songs):
    for song in songs:
        SongRenderer(song, seed=SEED).render()


def profiled(songs):
    """Return the profile of one render of some songs."""
    profile = cProfile.Profile()
    profile.enable()
    render_all(songs)
    profile.disable()
    return pstats.Stats(profile)


def short_name(path):
    return path.split(PACKAGE_MARK)[-1]


def constructions(stats):
    """Return how many times each of the program's classes was made, by the file that defines it, most first."""
    made = {}
    for (path, _, function), (_, calls, _, _, _) in stats.stats.items():
        if function in CONSTRUCTORS and PACKAGE_MARK in path:
            made[short_name(path)] = made.get(short_name(path), 0) + calls
    return sorted(made.items(), key=lambda item: -item[1])


def slowest_functions(stats):
    """Return the functions a render spends the most of its own time in, as (share of the time, calls, file, function)."""
    rows = [(own, calls, short_name(path), function) for (path, _, function), (_, calls, own, _, _) in stats.stats.items()]
    whole = sum(own for own, _, _, _ in rows) or 1
    rows.sort(reverse=True)
    return [(own / whole * PERCENT, calls, where, function) for own, calls, where, function in rows[:FUNCTIONS_SHOWN]]


def main(arguments):
    print(HEADING.format(name=EXAMPLE_COLUMN, time=TIME_COLUMN, calls=CALLS_COLUMN))
    total_time = 0
    total_calls = 0
    slowest = None
    for path in example_sets():
        songs = songs_of(path)
        best = min(timeit.repeat(lambda: render_all(songs), number=1, repeat=RUNS)) * MILLISECONDS
        calls = profiled(songs).total_calls
        print(ROW.format(name=os.path.basename(path), time=best, calls=calls))
        total_time += best
        total_calls += calls
        if slowest is None or best > slowest[0]:
            slowest = (best, path, songs)
    print(ROW.format(name=TOTAL_NAME, time=total_time, calls=total_calls))
    _, path, songs = slowest
    stats = profiled(songs)
    print()
    print(MADE_HEADING.format(name=os.path.basename(path)))
    for kind, count in constructions(stats):
        print(MADE_ROW.format(kind=kind, count=count))
    if PROFILE_FLAG in arguments:
        print()
        print(PROFILE_HEADING.format(name=os.path.basename(path)))
        for share, calls, where, function in slowest_functions(stats):
            print(PROFILE_ROW.format(share=share, calls=calls, where=where, function=function))


if __name__ == '__main__':
    main(sys.argv[1:])
