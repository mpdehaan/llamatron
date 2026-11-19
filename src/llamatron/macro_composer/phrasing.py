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

"""Phrasing: a tune's line made to breathe.

A sung line ends before its bars do, and the singer breathes; lines are not all one length, as lines of words are not, a
longer line then a shorter; and now and then a note comes an eighth early. A line's notes keep their pitches and their order:
only where the line stops and where a note falls change.
"""

from llamatron.macro_composer import notation

EIGHTHS_IN_BAR = 8
# The breath after a longer line and after a shorter one, in eighths, and the eighths of a bar a note may come early to: the third beat and the next bar's first.
SHORT_BREATH = 3
LONG_BREATH = 5
LONGER_BREATH = 6
PUSHED_TO = (4, 8)
# How a song may ask its lines to breathe: how long the breaths are, which lines of a section are the shorter, and how many lines in four have a note come early.
BREATH = 'breath'
LINE_LENGTHS = 'lines'
EARLY_NOTES = 'early'
SHORT = 'short'
MEDIUM = 'medium'
LONG = 'long'
# The breath after a longer line and the breaths after a shorter one, in eighths, by how long the breaths are.
BREATHS = {SHORT: (2, (4, 5)), MEDIUM: (SHORT_BREATH, (LONG_BREATH, LONGER_BREATH)), LONG: (4, (6, 7))}
LONG_THEN_SHORT = 'long, short'
SHORT_THEN_LONG = 'short, long'
EVEN = 'even'
LINE_LENGTH_WAYS = (LONG_THEN_SHORT, SHORT_THEN_LONG, EVEN)
FEWEST_EARLY = 0
MOST_EARLY = 4
USUAL_EARLY = 2
# The lines of four in the order they take an early note as more are asked for.
EARLY_ORDER = (1, 3, 0, 2)
USUAL_WAYS = {BREATH: MEDIUM, LINE_LENGTHS: LONG_THEN_SHORT, EARLY_NOTES: USUAL_EARLY}


def lasts(note):
    return note.get(notation.REST, note.get(notation.STEPS, 0))


def ended_early(*, line, breath):
    """A line that stops so many steps before its end, its last note cut where the breath begins."""
    total = sum(lasts(note) for note in line)
    room = total - breath
    kept = []
    for note in line:
        if room <= 0:
            break
        length = min(lasts(note), room)
        kept.append({**note, (notation.REST if notation.REST in note else notation.STEPS): length})
        room -= length
    while kept and notation.REST in kept[-1]:
        kept.pop()
    if not kept:
        return [dict(note) for note in line]
    return kept + [{notation.REST: total - sum(lasts(note) for note in kept)}]


def pushed(*, line, grid):
    """A line whose first note that falls on a third beat or a bar line, after a note of two eighths or more, comes an eighth early."""
    eighth = grid // EIGHTHS_IN_BAR
    at = 0
    for place, note in enumerate(line):
        before = line[place - 1] if place else None
        if before is not None and notation.REST not in note and notation.REST not in before and before[notation.STEPS] >= 2 * eighth and at % grid in [to * eighth % grid for to in PUSHED_TO]:
            moved = [dict(other) for other in line]
            moved[place - 1][notation.STEPS] -= eighth
            moved[place][notation.STEPS] += eighth
            return moved
        at += lasts(note)
    return line


def is_shorter(*, count, lengths):
    """Whether a line, counted from none in its section, is one of the shorter lines, which end in the longer breath."""
    if lengths == EVEN:
        return False
    return bool(count % 2) == (lengths == LONG_THEN_SHORT)


# What one line of a section's plan may say of itself, over the song's ways: its breath in eighths, and whether a note of it comes early.
LINE_BREATH = 'breath'
LINE_EARLY = 'early'
NO_BREATH = 0
LONGEST_BREATH = 8


def breathed(*, line, grid, count, dice, ways=None, breath=None, early=None):
    """A line of a tune made to breathe: a shorter line, the second and the fourth of its section unless the song asks otherwise,
    ends in the longer breath, and two lines of every four unless asked have a note come early. A style whose bar is not counted
    in eighths is left as written."""
    if grid % EIGHTHS_IN_BAR:
        return line
    ways = {**USUAL_WAYS, **(ways or {})}
    eighth = grid // EIGHTHS_IN_BAR
    after_longer, after_shorter = BREATHS[ways[BREATH]]
    # The dice are thrown whether or not the line says its own breath, so that the lines after it stay as they were.
    drawn = dice.choice(after_shorter) if is_shorter(count=count, lengths=ways[LINE_LENGTHS]) else after_longer
    breath = drawn if breath is None else breath
    made = ended_early(line=line, breath=breath * eighth) if breath else [dict(note) for note in line]
    # So many lines of every four have a note come early, the second and the fourth first: a count, with no dice, so that one more is always heard.
    early = EARLY_ORDER.index(count % MOST_EARLY) < ways[EARLY_NOTES] if early is None else early
    if early:
        made = pushed(line=made, grid=grid)
    return made
