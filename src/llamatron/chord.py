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

from dataclasses import dataclass
from enum import Enum

from llamatron.note import Note

MSG_NOT_A_LIST = 'expected a list of notes, got {value!r}'
MSG_NO_NOTES = 'a chord needs at least one note'
MSG_NOT_A_NOTE = 'expected a Note, got {value!r}'
# A note with no length yet sorts as if it had none, after the ones that have one.
NO_LENGTH = 0


class ChordType(Enum):
    """Each value is the chord's notes as half steps above the root."""

    # Two notes
    POWER = (7,)

    # Triads
    MAJOR = (4, 7)
    MINOR = (3, 7)
    DIMINISHED = (3, 6)
    AUGMENTED = (4, 8)
    SUS2 = (2, 7)
    SUS4 = (5, 7)

    # Sixths
    MAJOR6 = (4, 7, 9)
    MINOR6 = (3, 7, 9)

    # Sevenths
    DOMINANT7 = (4, 7, 10)
    MAJOR7 = (4, 7, 11)
    MINOR7 = (3, 7, 10)
    MINOR_MAJOR7 = (3, 7, 11)
    DIMINISHED7 = (3, 6, 9)
    HALF_DIMINISHED7 = (3, 6, 10)
    AUGMENTED7 = (4, 8, 10)
    AUGMENTED_MAJOR7 = (4, 8, 11)
    DOMINANT7_SUS4 = (5, 7, 10)

    # Added notes
    ADD9 = (4, 7, 14)
    MINOR_ADD9 = (3, 7, 14)

    # Extended chords
    DOMINANT9 = (4, 7, 10, 14)
    MAJOR9 = (4, 7, 11, 14)
    MINOR9 = (3, 7, 10, 14)
    DOMINANT11 = (4, 7, 10, 14, 17)
    MAJOR11 = (4, 7, 11, 14, 17)
    MINOR11 = (3, 7, 10, 14, 17)
    DOMINANT13 = (4, 7, 10, 14, 17, 21)
    MAJOR13 = (4, 7, 11, 14, 17, 21)
    MINOR13 = (3, 7, 10, 14, 17, 21)


@dataclass(frozen=True, eq=False, slots=True)
class Chord:
    """A group of notes. Chords with the same pitches and lengths compare equal in any order."""

    notes: tuple

    def __post_init__(self):
        if not isinstance(self.notes, (list, tuple)):
            raise ValueError(MSG_NOT_A_LIST.format(value=self.notes))
        if not self.notes:
            raise ValueError(MSG_NO_NOTES)
        for note in self.notes:
            if not isinstance(note, Note):
                raise ValueError(MSG_NOT_A_NOTE.format(value=note))
        # Copied into a tuple so that changing the caller's list can't change the chord.
        object.__setattr__(self, 'notes', tuple(self.notes))

    @property
    def length(self):
        """The length of the longest note, or None if any note doesn't have a length yet."""
        lengths = [note.length for note in self.notes]
        return None if None in lengths else max(lengths)

    @property
    def _sorted_pitches_and_lengths(self):
        # The middle value stops a length of None being compared with a number.
        ordered = sorted(
            (note.midi_number, note.length is None, note.length or NO_LENGTH) for note in self.notes
        )
        return tuple(ordered)

    def __eq__(self, other):
        if not isinstance(other, Chord):
            return NotImplemented
        return self._sorted_pitches_and_lengths == other._sorted_pitches_and_lengths

    def __hash__(self):
        return hash(self._sorted_pitches_and_lengths)
