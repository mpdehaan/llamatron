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

"""Joins: how the last bar of a section hands over to the next.

A join is said on the section left, as what the section leaves with: the size of the drummer's fill, and a tail, what the
band does together in the last bar in place of what each player would play: a drop-out, where everybody stops and the next
section comes in at full strength; stops, where the band plays a few hits together; or a build, where the snare plays every
eighth. A figure a player loops is written out for the whole section, so that its last bar alone can differ.
"""

from llamatron.macro_composer import notation

# The fields of what a section leaves with.
LEAVES = 'leaves'
FILL_OF_JOIN = 'fill'
TAIL = 'tail'
TAIL_EIGHTHS = 'eighths'
# The tails.
DROP_OUT = 'drop-out'
STOPS = 'stops'
BUILD = 'build'
TAILS = (DROP_OUT, STOPS, BUILD)
# The eighths of a bar in four that the band hits together in stops, and the pieces of the kit that hit with the band.
STOP_PLACES = (0, 3, 6)
EIGHTHS_IN_BAR = 8
STOP_PIECES = ('kick', 'crash')
BUILD_PIECE = 'snare'
KEPT_IN_BUILD = ('kick',)
# The share of a build's bar played soft before the loud strokes.
SOFT_SHARE_OF_BUILD = 2


def lasts(note):
    """How many steps a note or a rest lasts."""
    return note.get(notation.REST, note.get(notation.STEPS, 0))


def first_part(*, bar, steps):
    """The first steps of a bar, a note they end inside cut short."""
    kept = []
    room = steps
    for note in bar:
        if room <= 0:
            break
        length = min(lasts(note), room)
        kept.append({**note, (notation.REST if notation.REST in note else notation.STEPS): length})
        room -= length
    return kept


def sounding(bar):
    """The first note of a bar that sounds, or nothing."""
    return next((note for note in bar if notation.REST not in note), None)


def dropped_out(*, bar, eighths):
    """A bar whose last eighths are silent."""
    grid = sum(lasts(note) for note in bar)
    silent = grid * eighths // EIGHTHS_IN_BAR
    return first_part(bar=bar, steps=grid - silent) + [{notation.REST: silent}]


def stopped(bar):
    """A bar as stops: the bar's first note, one eighth long, at each place the band hits together, and silence between."""
    grid = sum(lasts(note) for note in bar)
    hit = sounding(bar)
    if hit is None or grid % EIGHTHS_IN_BAR:
        return [dict(note) for note in bar]
    eighth = grid // EIGHTHS_IN_BAR
    made = []
    for place in range(EIGHTHS_IN_BAR):
        made.append({**hit, notation.STEPS: eighth} if place in STOP_PLACES else {notation.REST: eighth})
    return made


def with_tail(*, bars, count, tail, eighths):
    """A looped figure written out for a section of so many bars, its last bar ending as the tail says; a build leaves the figure alone."""
    written = [[dict(note) for note in bars[place % len(bars)]] for place in range(count)]
    if tail == DROP_OUT:
        written[-1] = dropped_out(bar=written[-1], eighths=eighths)
    elif tail == STOPS:
        written[-1] = stopped(written[-1])
    return written


def drum_tail(*, piece, plain, tail, eighths):
    """A piece's last bar under a tail, from the bar the piece plays plainly: silent where the band drops out, the stops' hits on
    the kick and the crash, and in a build the snare on every eighth, soft and then loud, over the kick."""
    grid = len(plain)
    if tail == DROP_OUT:
        silent = grid * eighths // EIGHTHS_IN_BAR
        return plain[:grid - silent] + [notation.NONE] * silent
    if tail == STOPS:
        if piece not in STOP_PIECES or grid % EIGHTHS_IN_BAR:
            return [notation.NONE] * grid
        return [notation.LOUD if place % (grid // EIGHTHS_IN_BAR) == 0 and place // (grid // EIGHTHS_IN_BAR) in STOP_PLACES else notation.NONE for place in range(grid)]
    if tail == BUILD:
        if piece in KEPT_IN_BUILD:
            return list(plain)
        if piece != BUILD_PIECE or grid % EIGHTHS_IN_BAR:
            return [notation.NONE] * grid
        eighth = grid // EIGHTHS_IN_BAR
        return [(notation.SOFT if place // eighth < EIGHTHS_IN_BAR // SOFT_SHARE_OF_BUILD else notation.LOUD) if place % eighth == 0 else notation.NONE for place in range(grid)]
    return list(plain)


def pieces_of_tail(tail):
    """The pieces of the kit a tail plays whatever the groove has."""
    if tail == STOPS:
        return STOP_PIECES
    if tail == BUILD:
        return (BUILD_PIECE,)
    return ()
