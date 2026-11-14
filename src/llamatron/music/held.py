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

"""A sound held past its place in a clip, so that the notes after it can start while it sounds.

Most of a clip is a sequence, where each note's length is also how long until the next one
starts. A Held separates the two: its length is how long until the next position starts, and
its sound keeps its own lengths. That's how a note with a gate longer than its step overlaps
the steps after it.
"""

from llamatron.music.chord import Chord
from llamatron.music.note import Degree, Note, Rest, _check_length
from llamatron.strings.errors import ERR_BAD_PHRASE_PART, ERR_BAD_SOUND
from llamatron.strings.reprs import REPR_HELD

# What a held phrase can hold: anything a clip can, played one after another from the Held's start.
PHRASE_TYPES = (Note, Chord, Rest, Degree)


class Held:
    """A sound that starts here and lasts its own length, while the next position starts after length.

    The sound is a Note, a Chord, or a phrase: a tuple of positions played one after another
    from here, which is what an arpeggiator or AutoRatchet makes of a held chord. A Held is
    immutable: there are no setters.
    """

    __slots__ = ('_sound', '_length')

    def __init__(self, *, sound, length):
        _check_length(length)
        if is_phrase(sound):
            for part in sound:
                if not isinstance(part, (*PHRASE_TYPES, Held)):
                    raise ValueError(ERR_BAD_PHRASE_PART.format(value=part))
        elif not isinstance(sound, (Note, Chord, Degree)):
            raise ValueError(ERR_BAD_SOUND.format(value=sound))
        self._sound = sound
        self._length = length

    def get_sound(self):
        return self._sound

    def get_length(self):
        return self._length

    def __eq__(self, other):
        if not isinstance(other, Held):
            return NotImplemented
        return (self._sound, self._length) == (other._sound, other._length)

    def __hash__(self):
        return hash((self._sound, self._length))

    def __repr__(self):
        return REPR_HELD.format(sound=self._sound, length=self._length)


def is_phrase(sound):
    """Return whether a held sound is a phrase of positions, rather than one note or chord."""
    return isinstance(sound, tuple)


def phrase(positions):
    """Return positions as a held phrase, which is a tuple so that a Held can't be changed."""
    return tuple(positions)
