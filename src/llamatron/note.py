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
from fractions import Fraction
from math import isfinite

from llamatron.midi import HALF_STEPS_PER_OCTAVE, MAX_MIDI_NUMBER, MAX_VELOCITY, MIN_MIDI_NUMBER, MIN_VELOCITY

class NoteName:
    """Every way a note can be spelled: a letter, then # for sharp or b for flat.

    Double sharps and double flats aren't supported.
    """

    C_FLAT = 'Cb'
    C = 'C'
    C_SHARP = 'C#'
    D_FLAT = 'Db'
    D = 'D'
    D_SHARP = 'D#'
    E_FLAT = 'Eb'
    E = 'E'
    E_SHARP = 'E#'
    F_FLAT = 'Fb'
    F = 'F'
    F_SHARP = 'F#'
    G_FLAT = 'Gb'
    G = 'G'
    G_SHARP = 'G#'
    A_FLAT = 'Ab'
    A = 'A'
    A_SHARP = 'A#'
    B_FLAT = 'Bb'
    B = 'B'
    B_SHARP = 'B#'


# Semitones above C in the same octave number. Octave numbers change at C, so
# B# is a semitone above B in its octave (B#3 == C4) and Cb is a semitone below
# C (Cb4 == B3).
SEMITONES_ABOVE_C = {
    NoteName.B_SHARP: 12,
    NoteName.C: 0,
    NoteName.C_FLAT: -1,
    NoteName.C_SHARP: 1,
    NoteName.D_FLAT: 1,
    NoteName.D: 2,
    NoteName.D_SHARP: 3,
    NoteName.E_FLAT: 3,
    NoteName.E: 4,
    NoteName.F_FLAT: 4,
    NoteName.E_SHARP: 5,
    NoteName.F: 5,
    NoteName.F_SHARP: 6,
    NoteName.G_FLAT: 6,
    NoteName.G: 7,
    NoteName.G_SHARP: 8,
    NoteName.A_FLAT: 8,
    NoteName.A: 9,
    NoteName.A_SHARP: 10,
    NoteName.B_FLAT: 10,
    NoteName.B: 11,
}
# Every spelling a note's name can have, and the same as a set, for checking a name quickly.
NOTE_NAMES = list(SEMITONES_ABOVE_C)
KNOWN_NOTE_NAMES = frozenset(NOTE_NAMES)

# Spellings for notes worked out from a MIDI number, indexed by semitones above C.
SHARP_NAMES = [
    NoteName.C, NoteName.C_SHARP, NoteName.D, NoteName.D_SHARP, NoteName.E, NoteName.F,
    NoteName.F_SHARP, NoteName.G, NoteName.G_SHARP, NoteName.A, NoteName.A_SHARP, NoteName.B,
]
FLAT_NAMES = [
    NoteName.C, NoteName.D_FLAT, NoteName.D, NoteName.E_FLAT, NoteName.E, NoteName.F,
    NoteName.G_FLAT, NoteName.G, NoteName.A_FLAT, NoteName.A, NoteName.B_FLAT, NoteName.B,
]
# The roots the tracker offers for a scale: each key of the keyboard once, as a sharp and as a flat.
ROOT_NAMES = [
    NoteName.C, NoteName.C_SHARP, NoteName.D_FLAT, NoteName.D, NoteName.D_SHARP, NoteName.E_FLAT, NoteName.E,
    NoteName.F, NoteName.F_SHARP, NoteName.G_FLAT, NoteName.G, NoteName.G_SHARP, NoteName.A_FLAT, NoteName.A,
    NoteName.A_SHARP, NoteName.B_FLAT, NoteName.B,
]

MIN_OCTAVE = 0
MAX_OCTAVE = 10
# Degrees are numbered from 1, the scale's root.
FIRST_DEGREE = 1
# A note spelled with a flat has a name ending in b, like Eb.
FLAT_SIGN = 'b'

MSG_NOT_AN_INTEGER = 'expected an integer, got {value!r}'
MSG_BAD_LENGTH = 'invalid length: {value!r} (must be a positive fraction of a whole note)'
MSG_BAD_DEGREE = 'invalid degree: {value!r} (must be an integer of {lowest} or more)'
MSG_BAD_VELOCITY = 'invalid velocity: {value!r} (must be a whole number from {lowest} to {highest})'
MSG_BAD_GLIDE = 'invalid glide: {value!r} (must be True or False)'
MSG_BAD_NOTE_NAME = 'invalid note name: {value!r}'
MSG_BAD_OCTAVE = 'invalid octave: {value!r} (must be an integer from {lowest} to {highest})'
MSG_OUTSIDE_MIDI = '{name}{octave} is outside the MIDI range: its number would be {number}'
MSG_NOT_A_CHORD_TYPE = 'expected a ChordType, got {value!r}'
# A length has to be longer than nothing.
NO_LENGTH = 0
# The kinds of number a length can be.
LENGTH_TYPES = (int, float, Fraction)

def _check_integer(n):
    # bool is a subclass of int, but half_step(True) is not a real step count.
    if type(n) is not int:
        raise ValueError(MSG_NOT_AN_INTEGER.format(value=n))


def _check_length(length):
    # bool is a subclass of int, but True is not a real length.
    if not _is_positive_length(length):
        raise ValueError(MSG_BAD_LENGTH.format(value=length))


def _is_positive_length(length):
    """Return whether a length is a finite number of whole notes above zero, not counting true and false.

    Rendering checks this for every note it builds, so fractions and whole numbers, which are
    always finite, skip the float check, which would turn them into floats first.
    """
    kind = type(length)
    if kind is Fraction or kind is int:
        return length > NO_LENGTH
    return kind in LENGTH_TYPES and isfinite(length) and length > NO_LENGTH


@dataclass(frozen=True, slots=True)
class Rest:
    """A silence, where a length of 0.25 is a quarter note, 0.5 is a half note and so on."""

    length: float

    def __post_init__(self):
        _check_length(self.length)


@dataclass(frozen=True, slots=True)
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
        if type(self.number) is not int or self.number < FIRST_DEGREE:
            raise ValueError(MSG_BAD_DEGREE.format(value=self.number, lowest=FIRST_DEGREE))
        if self.length is not None:
            _check_length(self.length)
        _check_integer(self.octave)
        _check_integer(self.scale_notes)
        _check_integer(self.half_steps)

    def with_length(self, length):
        """Return the same degree with another length."""
        return Degree(self.number, length, self.octave, self.scale_notes, self.half_steps)

    def to_note(self, scale):
        """Return the Note that this degree plays in a scale, spelled as the root's half_step spells it."""
        steps = scale.typ.value
        octaves, index = divmod(self.number - FIRST_DEGREE + self.scale_notes, len(steps))
        half_steps = (octaves + self.octave) * HALF_STEPS_PER_OCTAVE + steps[index] + self.half_steps
        name, octave_number = scale.root.spelled_half_step(half_steps)
        return Note(name, octave_number, self.length)


@dataclass(frozen=True, eq=False, slots=True)
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
        if self.velocity is not None and not _is_velocity(self.velocity):
            raise ValueError(MSG_BAD_VELOCITY.format(value=self.velocity, lowest=MIN_VELOCITY, highest=MAX_VELOCITY))
        if type(self.glide) is not bool:
            raise ValueError(MSG_BAD_GLIDE.format(value=self.glide))
        if not isinstance(self.name, str) or self.name not in KNOWN_NOTE_NAMES:
            raise ValueError(MSG_BAD_NOTE_NAME.format(value=self.name))
        # bool is a subclass of int, but Note('C', True) is not a real octave.
        if type(self.octave_number) is not int or not MIN_OCTAVE <= self.octave_number <= MAX_OCTAVE:
            raise ValueError(MSG_BAD_OCTAVE.format(value=self.octave_number, lowest=MIN_OCTAVE, highest=MAX_OCTAVE))
        if not MIN_MIDI_NUMBER <= self.midi_number <= MAX_MIDI_NUMBER:
            raise ValueError(MSG_OUTSIDE_MIDI.format(name=self.name, octave=self.octave_number, number=self.midi_number))

    @property
    def midi_number(self):
        """The MIDI note number, where C0 is 0."""
        return self.octave_number * HALF_STEPS_PER_OCTAVE + SEMITONES_ABOVE_C[self.name]

    def half_step(self, n):
        """Return a new Note n half steps higher, or lower if n is negative.

        The result is spelled with flats if this note's name has a flat, and
        with sharps otherwise.
        """
        name, octave_number = self.spelled_half_step(n)
        return Note(name, octave_number, self.length, self.velocity, self.glide)

    def spelled_half_step(self, n):
        """Return the name and octave number of the note n half steps away, spelled as half_step spells it."""
        _check_integer(n)
        names = FLAT_NAMES if self.name.endswith(FLAT_SIGN) else SHARP_NAMES
        octave_number, semitones = divmod(self.midi_number + n, HALF_STEPS_PER_OCTAVE)
        return names[semitones], octave_number

    def with_length(self, length):
        """Return the same note with another length."""
        return Note(self.name, self.octave_number, length, self.velocity, self.glide)

    def with_velocity(self, velocity):
        """Return the same note at another velocity."""
        return Note(self.name, self.octave_number, self.length, velocity, self.glide)

    def with_glide(self):
        """Return the same note, gliding into the next."""
        return Note(self.name, self.octave_number, self.length, self.velocity, True)

    def to_chord(self, typ):
        """Return a new Chord of the given ChordType with this note as its root.

        The root keeps its spelling, and the other notes are spelled as
        half_step spells them.
        """
        # Imported here because llamatron.chord imports Note from this module.
        from llamatron.chord import Chord, ChordType

        if not isinstance(typ, ChordType):
            raise ValueError(MSG_NOT_A_CHORD_TYPE.format(value=typ))
        return Chord([self, *(self.half_step(n) for n in typ.value)])

    def __eq__(self, other):
        if not isinstance(other, Note):
            return NotImplemented
        return (self.midi_number, self.length) == (other.midi_number, other.length)

    def __hash__(self):
        return hash((self.midi_number, self.length))


def _is_velocity(velocity):
    """Return whether a velocity is a whole number in MIDI's range for notes, not counting true and false."""
    return type(velocity) is int and MIN_VELOCITY <= velocity <= MAX_VELOCITY
