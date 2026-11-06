# llamatron: a Python language and framework for producing MIDI clips.
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

from dataclasses import dataclass

from llamatron.chord import Chord
from llamatron.note import Degree, Note, Rest, _check_length

MSG_BAD_SOUND = 'expected a Note, Chord or a phrase of them, got {value!r}'
MSG_BAD_PHRASE_PART = 'a held phrase holds Notes, Chords, Rests, Degrees and Held, got {value!r}'
# What a held phrase can hold: anything a clip can, played one after another from the Held's start.
PHRASE_TYPES = (Note, Chord, Rest, Degree)


@dataclass(frozen=True, slots=True)
class Held:
    """A sound that starts here and lasts its own length, while the next position starts after length.

    The sound is a Note, a Chord, or a phrase: a tuple of positions played one after another
    from here, which is what an arpeggiator or AutoRatchet makes of a held chord.
    """

    sound: object
    length: object

    def __post_init__(self):
        _check_length(self.length)
        if is_phrase(self.sound):
            for part in self.sound:
                if not isinstance(part, (*PHRASE_TYPES, Held)):
                    raise ValueError(MSG_BAD_PHRASE_PART.format(value=part))
        elif not isinstance(self.sound, (Note, Chord, Degree)):
            raise ValueError(MSG_BAD_SOUND.format(value=self.sound))


def is_phrase(sound):
    """Return whether a held sound is a phrase of positions, rather than one note or chord."""
    return isinstance(sound, tuple)


def phrase(positions):
    """Return positions as a held phrase, which is a tuple so that a Held can't be changed."""
    return tuple(positions)
