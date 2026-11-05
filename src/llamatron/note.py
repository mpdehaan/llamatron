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

from dataclasses import dataclass, replace
from fractions import Fraction
from math import isfinite

# Semitones above C in the same octave number. Octave numbers change at C, so
# B# is a semitone above B in its octave (B#3 == C4) and Cb is a semitone below
# C (Cb4 == B3).
SEMITONES_ABOVE_C = {
    'B#': 12,
    'C': 0,
    'Cb': -1,
    'C#': 1,
    'Db': 1,
    'D': 2,
    'D#': 3,
    'Eb': 3,
    'E': 4,
    'Fb': 4,
    'E#': 5,
    'F': 5,
    'F#': 6,
    'Gb': 6,
    'G': 7,
    'G#': 8,
    'Ab': 8,
    'A': 9,
    'A#': 10,
    'Bb': 10,
    'B': 11,
}

MIN_OCTAVE = 0
MAX_OCTAVE = 10
MIN_MIDI_NUMBER = 0
MAX_MIDI_NUMBER = 127

# Spellings for notes worked out from a MIDI number, indexed by semitones above C.
SHARP_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
FLAT_NAMES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']


def _check_integer(n):
    # bool is a subclass of int, but half_step(True) is not a real step count.
    if type(n) is not int:
        raise ValueError(f'expected an integer, got {n!r}')


def _check_length(length):
    # bool is a subclass of int, but True is not a real length.
    if type(length) not in (int, float, Fraction) or not isfinite(length) or length <= 0:
        raise ValueError(
            f'invalid length: {length!r} (must be a positive fraction of a whole note)'
        )


@dataclass(frozen=True)
class Rest:
    """A silence, where a length of 0.25 is a quarter note, 0.5 is a half note and so on."""

    length: float

    def __post_init__(self):
        _check_length(self.length)


@dataclass(frozen=True)
class Degree:
    """A position in whichever scale applies when it's rendered, such as Degree(3, 0.25).

    Numbers start at 1, which is the scale's root, and continue past the top of the
    scale. A length of None uses the clip's note_length. The other fields move the
    note away from that position, and they're also how a generator moves a degree
    without needing to know the scale.
    """

    number: int
    length: float = None
    octave: int = 0
    scale_notes: int = 0
    half_steps: int = 0

    def __post_init__(self):
        # bool is a subclass of int, but True is not a real degree.
        if type(self.number) is not int or self.number < 1:
            raise ValueError(f'invalid degree: {self.number!r} (must be an integer of 1 or more)')
        if self.length is not None:
            _check_length(self.length)
        _check_integer(self.octave)
        _check_integer(self.scale_notes)
        _check_integer(self.half_steps)

    def to_note(self, scale):
        """Return the Note that this degree plays in a scale."""
        steps = scale.typ.value
        octaves, index = divmod(self.number - 1 + self.scale_notes, len(steps))
        half_steps = (octaves + self.octave) * 12 + steps[index] + self.half_steps
        note = scale.root.half_step(half_steps)
        return Note(note.name, note.octave_number, self.length)


@dataclass(frozen=True, eq=False)
class Note:
    """A pitch and length, such as Note('C#', 4, 0.25). Enharmonic spellings compare equal.

    A length of 0.25 is a quarter note, 0.5 is a half note and so on. A length of None
    uses the note_length of the clip it's in. A velocity of None plays at the renderers'
    usual velocity, and glide makes the note run slightly into the next one, so that a synth
    with glide turned on slides between them. Neither changes how notes compare.
    """

    name: str
    octave_number: int
    length: float = None
    velocity: int = None
    glide: bool = False

    def __post_init__(self):
        if self.length is not None:
            _check_length(self.length)
        if self.velocity is not None and (type(self.velocity) is not int or not 1 <= self.velocity <= 127):
            raise ValueError(f'invalid velocity: {self.velocity!r} (must be a whole number from 1 to 127)')
        if type(self.glide) is not bool:
            raise ValueError(f'invalid glide: {self.glide!r} (must be True or False)')
        if not isinstance(self.name, str) or self.name not in SEMITONES_ABOVE_C:
            raise ValueError(f'invalid note name: {self.name!r}')
        # bool is a subclass of int, but Note('C', True) is not a real octave.
        if type(self.octave_number) is not int or not MIN_OCTAVE <= self.octave_number <= MAX_OCTAVE:
            raise ValueError(
                f'invalid octave: {self.octave_number!r} '
                f'(must be an integer from {MIN_OCTAVE} to {MAX_OCTAVE})'
            )
        if not MIN_MIDI_NUMBER <= self.midi_number <= MAX_MIDI_NUMBER:
            raise ValueError(
                f'{self.name}{self.octave_number} is outside the MIDI range: '
                f'its number would be {self.midi_number}'
            )

    @property
    def midi_number(self):
        """The MIDI note number, where C0 is 0."""
        return self.octave_number * 12 + SEMITONES_ABOVE_C[self.name]

    def half_step(self, n):
        """Return a new Note n half steps higher, or lower if n is negative.

        The result is spelled with flats if this note's name has a flat, and
        with sharps otherwise.
        """
        _check_integer(n)
        names = FLAT_NAMES if self.name.endswith('b') else SHARP_NAMES
        octave_number, semitones = divmod(self.midi_number + n, 12)
        return replace(self, name=names[semitones], octave_number=octave_number)

    def to_chord(self, typ):
        """Return a new Chord of the given ChordType with this note as its root.

        The root keeps its spelling, and the other notes are spelled as
        half_step spells them.
        """
        # Imported here because llamatron.chord imports Note from this module.
        from llamatron.chord import Chord, ChordType

        if not isinstance(typ, ChordType):
            raise ValueError(f'expected a ChordType, got {typ!r}')
        return Chord([self, *(self.half_step(n) for n in typ.value)])

    def __eq__(self, other):
        if not isinstance(other, Note):
            return NotImplemented
        return (self.midi_number, self.length) == (other.midi_number, other.length)

    def __hash__(self):
        return hash((self.midi_number, self.length))
