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

"""A clip's notes placed on one count of ticks, for the timing code: a whole note is shared into as many ticks as every length
the clip holds, its own length, its groove's moves and a glide's run need, so that placing, moving and cutting each note adds and
compares whole numbers, many times faster than fractions, and only each note's start and end become fractions at the end.
The timing code uses it for a clip with no strum and no rushes or drags, most clips of most songs, and fractions for the rest;
every export is the same either way."""

import math

from llamatron.exporters import sounding
from llamatron.exporters.sounding import degree_to_note, NoteEvent, sounding_notes, velocity_of
from llamatron.music import sound
from llamatron.support.length import Length
from llamatron.support.rational import reduced

UNMOVED = 0


class ClipTicks:
    """A clip's notes placed on one count of ticks, each slot its start in ticks and the notes it sounds by MIDI number, in time
    order, with the clip's length, the groove's cell and moves and a glide's run in ticks too."""

    __slots__ = ('_ticks', '_slots', '_length', '_cell', '_moves', '_glide')

    def __init__(self, *, positions, scale, length, groove):
        """positions are the clip's, every length filled in; length is the clip's, a Rational; groove is its Groove, or None."""
        cell, moves = groove.moves() if groove is not None else (None, [])
        found = set()
        for position in positions:
            _add_denominators(position=position, found=found)
        self._ticks = math.lcm(length.denominator, sounding.GLIDE_OVERLAP.denominator, *found, *(move.denominator for move in moves), cell.denominator if cell is not None else 1)
        self._length = self._ticks_of(length)
        self._glide = self._ticks_of(sounding.GLIDE_OVERLAP)
        self._cell = None if cell is None else self._ticks_of(cell)
        self._moves = [self._ticks_of(move) for move in moves]
        self._slots = []
        start = 0
        for position in positions:
            self._place(position=position, start=start, scale=scale)
            start += Length.ticks_of(position[sound.LENGTH], self._ticks)
        self._slots.sort(key=_slot_start)

    def timed(self):
        """Return the clip's notes as NoteEvents, each moved by the groove, gliding into what follows and cut at the clip's end."""
        timed = []
        ticks = self._ticks
        slots = self._slots
        for place, (slot_start, notes) in enumerate(slots):
            if not notes:
                continue
            onset = self._moved(slot_start)
            following = slots[place + 1][1] if place + 1 < len(slots) else {}
            start = min(onset, self._length)
            start_whole = reduced(numerator=start, denominator=ticks)
            for midi_number, note in notes.items():
                end = onset + Length.ticks_of(note[sound.LENGTH], ticks)
                if note[sound.GLIDE] and following and midi_number not in following:
                    end += self._glide
                end = min(end, self._length)
                if end > start:
                    timed.append(NoteEvent(start_whole, reduced(numerator=end, denominator=ticks), midi_number, velocity_of(note)))
        return timed

    def _moved(self, start):
        """Return when a slot starting at a tick plays once the groove has moved it, never before the clip's start."""
        if self._cell is None:
            return start
        return max(start + self._moves[(start // self._cell) % len(self._moves)], UNMOVED)

    def _ticks_of(self, value):
        """Return a Rational, whose denominator the count of ticks holds, as ticks."""
        return value.numerator * (self._ticks // value.denominator)

    def _place(self, *, position, start, scale):
        """Add the slots a position sounds, starting at a tick, including everything a held sound holds."""
        kind = position[sound.KIND]
        if kind == sound.HELD:
            self._place(position=position[sound.HELD_SOUND], start=start, scale=scale)
        elif kind == sound.PHRASE:
            for part in position[sound.PARTS]:
                self._place(position=part, start=start, scale=scale)
                start += Length.ticks_of(part[sound.LENGTH], self._ticks)
        else:
            self._slots.append((start, sounding_notes(degree_to_note(position=position, scale=scale))))


def _slot_start(slot):
    return slot[0]


def _add_denominators(*, position, found):
    """Add the denominators of every length a position holds, everything a held sound holds and a chord's notes included."""
    found.add(position[sound.LENGTH][1])
    kind = position[sound.KIND]
    if kind == sound.HELD:
        _add_denominators(position=position[sound.HELD_SOUND], found=found)
    elif kind == sound.PHRASE:
        for part in position[sound.PARTS]:
            _add_denominators(position=part, found=found)
    elif kind == sound.CHORD:
        for note in position[sound.NOTES]:
            found.add(note[sound.LENGTH][1])
