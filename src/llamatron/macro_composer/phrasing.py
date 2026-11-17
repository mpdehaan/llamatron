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

from llamatron.macro_composer.notation import REST, STEPS

EIGHTHS_IN_BAR = 8
# The breath after a longer line and after a shorter one, in eighths, and the eighths of a bar a note may come early to: the third beat and the next bar's first.
SHORT_BREATH = 3
LONG_BREATH = 5
LONGER_BREATH = 6
PUSHED_TO = (4, 8)
# One line in so many has a note come early.
PUSH_ONE_IN = 2


def lasts(note):
    return note.get(REST, note.get(STEPS, 0))


def ended_early(*, line, breath):
    """A line that stops so many steps before its end, its last note cut where the breath begins."""
    total = sum(lasts(note) for note in line)
    room = total - breath
    kept = []
    for note in line:
        if room <= 0:
            break
        length = min(lasts(note), room)
        kept.append({**note, (REST if REST in note else STEPS): length})
        room -= length
    while kept and REST in kept[-1]:
        kept.pop()
    if not kept:
        return [dict(note) for note in line]
    return kept + [{REST: total - sum(lasts(note) for note in kept)}]


def pushed(*, line, grid):
    """A line whose first note that falls on a third beat or a bar line, after a note of two eighths or more, comes an eighth early."""
    eighth = grid // EIGHTHS_IN_BAR
    at = 0
    for place, note in enumerate(line):
        before = line[place - 1] if place else None
        if before is not None and REST not in note and REST not in before and before[STEPS] >= 2 * eighth and at % grid in [to * eighth % grid for to in PUSHED_TO]:
            moved = [dict(other) for other in line]
            moved[place - 1][STEPS] -= eighth
            moved[place][STEPS] += eighth
            return moved
        at += lasts(note)
    return line


def breathed(*, line, grid, count, dice):
    """A line of a tune made to breathe: a line in an odd place of its section, the second and the fourth, is the shorter, and
    one line in two has a note come early. A style whose bar is not counted in eighths is left as written."""
    if grid % EIGHTHS_IN_BAR:
        return line
    eighth = grid // EIGHTHS_IN_BAR
    breath = dice.choice((LONG_BREATH, LONGER_BREATH)) if count % 2 else SHORT_BREATH
    made = ended_early(line=line, breath=breath * eighth)
    if dice.randrange(PUSH_ONE_IN) == 0:
        made = pushed(line=made, grid=grid)
    return made
