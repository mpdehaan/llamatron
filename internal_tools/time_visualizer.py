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

"""How long each visualizer mode takes to draw a frame, with a few tracks and with 64, on an 80 by 24 console and on a large terminal.

    .venv/bin/python internal_tools/time_visualizer.py
    internal_tools/time_visualizer.sh

Each mode draws FRAMES frames of made-up notes, a frame apart, every track playing a note now and
then and drums among them, the way a busy song would, and the report gives the mean and the worst
cost of a frame in milliseconds against the frame's budget (the time between frames on Arrange).
A mode that stays well under its budget leaves the computer cool and the screen answering keys.
"""

import random
import time

from llamatron.tui.screens.arrange_page import FRAME_SECONDS
from llamatron.visualizers.heard import Heard, HeardNote
from llamatron.visualizers.modes import MODES

FRAMES = 200
SEED = 1
# The clip area of an 80 by 24 console, and of a large terminal, in columns and rows.
SIZES = ((56, 16), (176, 56))
TRACK_COUNTS = (8, 64)
# How often a track's note starts in a frame, and how often it is held, as chances; every eighth track is a drum.
START_CHANCE = 0.15
HELD_CHANCE = 0.4
DRUM_EVERY = 8
LOWEST_PITCH = 36
HIGHEST_PITCH = 90
SOFTEST = 50
LOUDEST = 127
SECONDS_PER_BEAT = 0.5
MILLISECONDS = 1000
HEADING = '{mode:<12} {tracks:>6} {size:>9} {mean:>9} {worst:>9} {budget:>8}'
COLUMNS = {'mode': 'mode', 'tracks': 'tracks', 'size': 'area', 'mean': 'mean ms', 'worst': 'worst ms', 'budget': 'of budget'}
LINE = '{mode:<12} {tracks:>6} {size:>9} {mean:>9.2f} {worst:>9.2f} {budget:>7.0f}%'
SIZE = '{columns}x{rows}'


def made_up_notes(*, tracks, chooser):
    """Return a frame's notes: each track starting a note, holding one, or resting, by chance."""
    notes = []
    for track in range(tracks):
        roll = chooser.random()
        if roll < START_CHANCE + HELD_CHANCE:
            notes.append(HeardNote(track, chooser.randint(LOWEST_PITCH, HIGHEST_PITCH), chooser.randint(SOFTEST, LOUDEST), roll < START_CHANCE, track % DRUM_EVERY == DRUM_EVERY - 1))
    return tuple(notes)


def timed(*, mode, tracks, columns, rows):
    """Return the mean and the worst seconds a mode takes to draw a frame."""
    chooser = random.Random(SEED)
    visualizer = mode()
    costs = []
    for number in range(FRAMES):
        heard = Heard(notes=made_up_notes(tracks=tracks, chooser=chooser), seconds_per_beat=SECONDS_PER_BEAT, beats=number * FRAME_SECONDS / SECONDS_PER_BEAT)
        start = time.perf_counter()
        visualizer.frame(width=columns, height=rows, now=number * FRAME_SECONDS, heard=heard)
        costs.append(time.perf_counter() - start)
    return sum(costs) / len(costs), max(costs)


def main():
    print(HEADING.format(**COLUMNS))
    for mode in MODES:
        for tracks in TRACK_COUNTS:
            for columns, rows in SIZES:
                mean, worst = timed(mode=mode, tracks=tracks, columns=columns, rows=rows)
                print(LINE.format(mode=mode.OPTION, tracks=tracks, size=SIZE.format(columns=columns, rows=rows), mean=mean * MILLISECONDS,
                                  worst=worst * MILLISECONDS, budget=mean / FRAME_SECONDS * 100))


if __name__ == '__main__':
    main()
