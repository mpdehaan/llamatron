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

"""The kinds of hook: a hook's bar drawn from a family of contour and a family of rhythm, with one odd detail.

Two hooks of one song differ in kind, never by chance alone: each take of a song's hook takes the next contour and the next
rhythm, so that a person asking for another hears something else. The head of a hook is what it is known by and never
changes; a hook's bar says something twice inside itself or across its two statements.

A bar is counted in eight units. A rhythm is the lengths of its notes, a silence written as a length below zero; a contour is
how far below the hook's top each note sits, the top being none.
"""

import random

from llamatron.strings.macro_composer import MSG_HOOK_KIND

UNITS = 8
# The contours.
CHANT = 'chant'
ARCH = 'arch'
FALLING = 'falling line'
LEAP_AND_FILL = 'leap and fill'
ROCKING = 'rocking'
RISING_SEQUENCE = 'rising sequence'
LONG_NOTE = 'long note'
CONTOURS = (LONG_NOTE, CHANT, ARCH, FALLING, LEAP_AND_FILL, ROCKING, RISING_SEQUENCE)
# The rhythms: on the beat; a note before the third beat; starting after the first beat; three and three and two; even eighths with a gap.
ANTHEM = 'on the beat'
PUSHED = 'before the third beat'
AFTER_ONE = 'after the first beat'
THREE_THREE_TWO = 'three and three and two'
EIGHTHS_WITH_A_GAP = 'eighths with a gap'
RHYTHMS = {
    ANTHEM: (2, 2, 2, 2),
    PUSHED: (2, 1, 2, 3),
    AFTER_ONE: (-1, 1, 2, 2, 2),
    THREE_THREE_TWO: (2, 1, 2, 1, 2),
    EIGHTHS_WITH_A_GAP: (1, 1, 1, -1, 1, 1, 2),
}
# The odd details, one a hook: a note an eighth early, a silent first beat, an ending on a note that does not close, one note
# said more often than seems reasonable, and an answer that stops a note short.
EARLY_NOTE = 'one note early'
SILENT_DOWNBEAT = 'a silent first beat'
OPEN_ENDING = 'an ending left open'
SAID_AGAIN = 'one note said again and again'
CUT_SHORT = 'a repeat cut short'
DETAILS = (EARLY_NOTE, SILENT_DOWNBEAT, OPEN_ENDING, SAID_AGAIN, CUT_SHORT)
# The farthest below its top a hook goes, in places of the style's ladder, about a sixth.
DEEPEST = 3
SEQUENCE_CELL = (2, 1, 0)
KIND_SEED = '{} hook kind'
DETAIL_SEED = '{} hook detail {}'
CONTOUR = 'contour'
RHYTHM = 'rhythm'
DETAIL = 'detail'


def kind_of(*, seed, take):
    """The kind of a song's hook at a take: its contour, its rhythm and its odd detail. The order the kinds come in is the
    song's own, and each take is the next of each."""
    dice = random.Random(KIND_SEED.format(seed))
    contours = dice.sample(CONTOURS, len(CONTOURS))
    rhythms = dice.sample(list(RHYTHMS), len(RHYTHMS))
    detail = random.Random(DETAIL_SEED.format(seed, take)).choice(DETAILS)
    return {CONTOUR: contours[take % len(contours)], RHYTHM: rhythms[take % len(rhythms)], DETAIL: detail}


def said_of(kind):
    """A hook's kind in words."""
    return MSG_HOOK_KIND.format(kind[CONTOUR], kind[RHYTHM], kind[DETAIL])


def depths_of(*, contour, count):
    """How far below the top each of a bar's notes sits."""
    if contour == CHANT:
        # One note, with its neighbour once, before the last.
        return [1 if place == count - 2 else 0 for place in range(count)]
    if contour == ARCH:
        peak = count // 2
        return [min(DEEPEST, abs(place - peak)) for place in range(count)]
    if contour == FALLING:
        return [min(DEEPEST, place) for place in range(count)]
    if contour == LEAP_AND_FILL:
        return [DEEPEST] + [min(DEEPEST, place) for place in range(count - 1)]
    if contour == ROCKING:
        return [(place + 1) % 2 for place in range(count)]
    # A cell of three notes said again a step higher, ending on the top.
    rising = [SEQUENCE_CELL[place % len(SEQUENCE_CELL)] - place // len(SEQUENCE_CELL) for place in range(count)]
    lowest = min(rising[-1], min(rising))
    return [min(DEEPEST, depth - lowest) if place < count - 1 else 0 for place, depth in enumerate(rising)]


def with_detail(*, lengths, depths, detail):
    """A bar's rhythm and contour with the odd detail that changes the bar itself; the details of an ending and of the answer are the maker's."""
    lengths = list(lengths)
    depths = list(depths)
    sounds = [place for place, length in enumerate(lengths) if length > 0]
    if detail == EARLY_NOTE:
        # The last note of the bar that follows a note of two units or more comes a unit early.
        for place in reversed(sounds[1:]):
            if lengths[place - 1] >= 2:
                lengths[place - 1] -= 1
                lengths[place] += 1
                break
    elif detail == SILENT_DOWNBEAT and lengths[0] > 0 and len(sounds) > 3:
        lengths[0] = -lengths[0]
        depths = depths[1:]
    elif detail == SAID_AGAIN:
        # The longest note is said once a unit, on the one pitch.
        longest = max(sounds, key=lambda place: lengths[place])
        if lengths[longest] > 1:
            which = sounds.index(longest)
            times = lengths[longest]
            lengths[longest:longest + 1] = [1] * times
            depths[which:which + 1] = [depths[which]] * times
    return lengths, depths


def bar_of(*, kind):
    """A hook's bar: the lengths of its notes and silences, and each note's depth below the top."""
    lengths = RHYTHMS[kind[RHYTHM]]
    count = sum(1 for length in lengths if length > 0)
    lengths, depths = with_detail(lengths=lengths, depths=depths_of(contour=kind[CONTOUR], count=count), detail=kind[DETAIL])
    # The top always sounds: the notes are lifted until the highest of them is the top.
    return lengths, [depth - min(depths) for depth in depths]
