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

"""A song's hooks, found from its notes: on every melodic part, each bar's figure (its intervals and rhythm, apart from where it
starts, so a transposed return counts) and each two-bar figure; the one that returns most is the hook. How much of the song its
returns cover is its strength, how well it fits a hum is its hummability, and the share of its returns that fall on the song's
loudest bars is its placement."""

from collections import Counter

from llamatron.genres.measures.traits import Hook, Role

FIGURE_BARS = (1, 2)
HUM_RANGE = 12
HUM_NOTES = 10
HUM_STEPS = 0.6
HIGH_POINT = 0.7
MIN_NOTES = 3
GRID = 4
HOOK_ROLES = (Role.LEAD, Role.COUNTER)


def figures_of(*, track, performance, bars):
    """Return each figure a part plays a window of bars long, by where it starts: its intervals and its rhythm, transposable."""
    windows = {}
    span = float(performance.beats_per_bar) * bars
    for note in track.notes:
        windows.setdefault(int(note.begins // span), []).append(note)
    figures = {}
    for window, notes in windows.items():
        highest = {}
        for note in notes:
            if note.start not in highest or note.pitch > highest[note.start].pitch:
                highest[note.start] = note
        line = [highest[start] for start in sorted(highest)]
        if len(line) < MIN_NOTES:
            continue
        intervals = tuple(later.pitch - earlier.pitch for earlier, later in zip(line, line[1:]))
        rhythm = tuple(round((note.begins - window * span) * GRID) for note in line)
        figures[window * bars] = (intervals, rhythm, tuple(note.pitch for note in line))
    return figures


def hummability(pitches):
    """Return how well a figure fits a hum: within an octave, a handful of notes, mostly by step."""
    moves = [later - earlier for earlier, later in zip(pitches, pitches[1:])]
    steps = sum(1 for move in moves if abs(move) <= 2) / len(moves) if moves else 0.0
    within = 1.0 if max(pitches) - min(pitches) <= HUM_RANGE else 0.5
    few = 1.0 if len(pitches) <= HUM_NOTES else HUM_NOTES / len(pitches)
    return round(within * few * min(1.0, steps / HUM_STEPS) * 0.5 + 0.5 * within * few, 3)


def hook_of(*, performance, levels, roles):
    """Return the song's hook as a trait, looked for on the lines the ear follows, the lead and the counter lines, since a
    repeating accompaniment is a groove rather than a hook."""
    best = None
    bars = performance.bars()
    for track in [track for track, role in roles.items() if role in HOOK_ROLES]:
        for size in FIGURE_BARS:
            figures = figures_of(track=track, performance=performance, bars=size)
            if not figures:
                continue
            counts = Counter((intervals, rhythm) for intervals, rhythm, _ in figures.values())
            shape, returns = counts.most_common(1)[0]
            if returns < 2:
                continue
            covered = returns * size / bars
            starts = [start for start, figure in figures.items() if (figure[0], figure[1]) == shape]
            pitches = next(figure[2] for figure in figures.values() if (figure[0], figure[1]) == shape)
            if best is None or covered > best[0]:
                best = (covered, pitches, starts)
    if best is None:
        return Hook(strength=0.0, hummable=None, placement=None)
    covered, pitches, starts = best
    high = sum(1 for start in starts if start < len(levels) and levels[start] >= HIGH_POINT) / len(starts)
    return Hook(strength=round(min(1.0, covered), 3), hummable=hummability(pitches), placement=round(high, 3))
