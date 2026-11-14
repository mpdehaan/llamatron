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

from fractions import Fraction
from math import isfinite

from llamatron.music.midi import HALF_STEPS_PER_OCTAVE, MAX_MIDI_NUMBER, MAX_VELOCITY, MIN_MIDI_NUMBER, MIN_VELOCITY
from llamatron.support.rational import Rational
from llamatron.strings.errors import (
    ERR_BAD_DEGREE, ERR_BAD_GLIDE, ERR_BAD_LENGTH, ERR_BAD_NOTE_NAME, ERR_BAD_VELOCITY, ERR_NOT_A_CHORD_TYPE, ERR_NOT_AN_INTEGER,
    ERR_NOTE_BAD_OCTAVE, ERR_OUTSIDE_MIDI,
)
from llamatron.strings.reprs import REPR_DEGREE, REPR_NOTE, REPR_REST

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

# A length has to be longer than nothing.
NO_LENGTH = 0
# The kinds of number a length can be.
LENGTH_TYPES = (int, float, Rational, Fraction)
# Makes an object without running its constructor, for a copy whose fields are already checked.
_new = object.__new__

def _check_integer(n):
    # bool is a subclass of int, but half_step(True) is not a real step count.
    if type(n) is not int:
        raise ValueError(ERR_NOT_AN_INTEGER.format(value=n))


def _check_length(length):
    # bool is a subclass of int, but True is not a real length.
    if not _is_positive_length(length):
        raise ValueError(ERR_BAD_LENGTH.format(value=length))


def _is_positive_length(length):
    """Return whether a length is a finite number of whole notes above zero, not counting true and false.

    Rendering checks this for every note it builds, so fractions and whole numbers, which are
    always finite, skip the float check, which would turn them into floats first.
    """
    kind = type(length)
    if kind is Rational or kind is int:
        return length > NO_LENGTH
    return kind in LENGTH_TYPES and isfinite(length) and length > NO_LENGTH


class Rest:
    """A silence, where a length of 0.25 is a quarter note, 0.5 is a half note and so on.

    Rests are immutable: there are no setters, and a rest of another length is a new Rest.
    """

    __slots__ = ('_length',)

    def __init__(self, length):
        _check_length(length)
        self._length = length

    def get_length(self):
        return self._length

    def __eq__(self, other):
        if not isinstance(other, Rest):
            return NotImplemented
        return self._length == other._length

    def __hash__(self):
        return hash((Rest, self._length))

    def __repr__(self):
        return REPR_REST.format(length=self._length)


class Degree:
    """A position in whichever scale applies when it's rendered, such as Degree(number=3, length=0.25).

    Numbers start at 1, which is the scale's root, and continue past the top of the
    scale. A length of None uses the clip's note_length. The other fields move the
    note away from that position, and they're also how a generator moves a degree
    without needing to know the scale. Degrees are immutable: a degree with another
    length is a new Degree.
    """

    __slots__ = ('_number', '_length', '_octave', '_scale_notes', '_half_steps')

    def __init__(self, *, number, length=None, octave=0, scale_notes=0, half_steps=0):
        # bool is a subclass of int, but True is not a real degree.
        if type(number) is not int or number < FIRST_DEGREE:
            raise ValueError(ERR_BAD_DEGREE.format(value=number, lowest=FIRST_DEGREE))
        if length is not None:
            _check_length(length)
        _check_integer(octave)
        _check_integer(scale_notes)
        _check_integer(half_steps)
        self._number = number
        self._length = length
        self._octave = octave
        self._scale_notes = scale_notes
        self._half_steps = half_steps

    def get_number(self):
        return self._number

    def get_length(self):
        return self._length

    def get_octave(self):
        return self._octave

    def get_scale_notes(self):
        return self._scale_notes

    def get_half_steps(self):
        return self._half_steps

    def with_length(self, length):
        """Return the same degree with another length."""
        return Degree(number=self._number, length=length, octave=self._octave, scale_notes=self._scale_notes, half_steps=self._half_steps)

    def to_note(self, scale):
        """Return the Note that this degree plays in a scale, spelled as the root's half_step spells it."""
        return scale.note_at(
            degree=self._number, scale_notes=self._scale_notes, length=self._length,
            half_steps=self._octave * HALF_STEPS_PER_OCTAVE + self._half_steps,
        )

    def _as_tuple(self):
        return (self._number, self._length, self._octave, self._scale_notes, self._half_steps)

    def __eq__(self, other):
        if not isinstance(other, Degree):
            return NotImplemented
        return self._as_tuple() == other._as_tuple()

    def __hash__(self):
        return hash(self._as_tuple())

    def __repr__(self):
        return REPR_DEGREE.format(number=self._number, length=self._length, octave=self._octave, scale_notes=self._scale_notes, half_steps=self._half_steps)


class Note:
    """A pitch and length, such as Note(name='C#', octave_number=4, length=0.25). Enharmonic spellings compare equal.

    A length of 0.25 is a quarter note, 0.5 is a half note and so on. A length of None
    uses the note_length of the clip it's in. A velocity of None plays at the exporters'
    usual velocity, and glide makes the note run slightly into the next one, so that a synth
    with glide turned on slides between them. Neither changes how notes compare. Notes are
    immutable: there are no setters, and with_length and friends return a new Note.
    """

    __slots__ = ('_name', '_octave_number', '_length', '_velocity', '_glide', '_midi_number')

    def __init__(self, *, name, octave_number, length=None, velocity=None, glide=False):
        if length is not None:
            _check_length(length)
        if velocity is not None and not _is_velocity(velocity):
            raise ValueError(ERR_BAD_VELOCITY.format(value=velocity, lowest=MIN_VELOCITY, highest=MAX_VELOCITY))
        if type(glide) is not bool:
            raise ValueError(ERR_BAD_GLIDE.format(value=glide))
        if not isinstance(name, str) or name not in KNOWN_NOTE_NAMES:
            raise ValueError(ERR_BAD_NOTE_NAME.format(value=name))
        # bool is a subclass of int, but Note('C', True) is not a real octave.
        if type(octave_number) is not int or not MIN_OCTAVE <= octave_number <= MAX_OCTAVE:
            raise ValueError(ERR_NOTE_BAD_OCTAVE.format(value=octave_number, lowest=MIN_OCTAVE, highest=MAX_OCTAVE))
        midi_number = octave_number * HALF_STEPS_PER_OCTAVE + SEMITONES_ABOVE_C[name]
        if not MIN_MIDI_NUMBER <= midi_number <= MAX_MIDI_NUMBER:
            raise ValueError(ERR_OUTSIDE_MIDI.format(name=name, octave=octave_number, number=midi_number))
        self._name = name
        self._octave_number = octave_number
        self._length = length
        self._velocity = velocity
        self._glide = glide
        # Worked out once here, since comparing, hashing and rendering all read it.
        self._midi_number = midi_number

    def get_name(self):
        """The spelling the note was given, like C# or Db."""
        return self._name

    def get_octave_number(self):
        return self._octave_number

    def get_length(self):
        return self._length

    def get_velocity(self):
        return self._velocity

    def get_glide(self):
        return self._glide

    def get_midi_number(self):
        """The MIDI note number, where C0 is 0."""
        return self._midi_number

    def half_step(self, n):
        """Return a new Note n half steps higher, or lower if n is negative.

        The result is spelled with flats if this note's name has a flat, and
        with sharps otherwise.
        """
        name, octave_number = self.spelled_half_step(n)
        midi_number = self._midi_number + n
        if not MIN_MIDI_NUMBER <= midi_number <= MAX_MIDI_NUMBER:
            # Outside the MIDI range, the constructor says what is wrong with the note.
            return Note(name=name, octave_number=octave_number, length=self._length, velocity=self._velocity, glide=self._glide)
        # A name half_step chose and a MIDI number in range need no checking, and the rest is this note's own.
        return note_of_checked_values(
            name=name, octave_number=octave_number, midi_number=midi_number, length=self._length, velocity=self._velocity, glide=self._glide,
        )

    def spelled_half_step(self, n):
        """Return the name and octave number of the note n half steps away, spelled as half_step spells it."""
        _check_integer(n)
        names = FLAT_NAMES if self._name.endswith(FLAT_SIGN) else SHARP_NAMES
        octave_number, semitones = divmod(self._midi_number + n, HALF_STEPS_PER_OCTAVE)
        return names[semitones], octave_number

    def with_length(self, length):
        """Return the same note with another length."""
        if length is not None:
            _check_length(length)
        return self._at_this_pitch(length=length, velocity=self._velocity, glide=self._glide)

    def with_velocity(self, velocity):
        """Return the same note at another velocity."""
        if velocity is not None and not _is_velocity(velocity):
            raise ValueError(ERR_BAD_VELOCITY.format(value=velocity, lowest=MIN_VELOCITY, highest=MAX_VELOCITY))
        return self._at_this_pitch(length=self._length, velocity=velocity, glide=self._glide)

    def with_glide(self):
        """Return the same note, gliding into the next."""
        return self._at_this_pitch(length=self._length, velocity=self._velocity, glide=True)

    def _at_this_pitch(self, *, length, velocity, glide):
        """Return a note at this note's pitch with a length, a velocity and a glide that the caller has checked.

        The name, the octave and the MIDI number were checked when this note was made and can't
        change, so a copy takes them as they are: checking them again for every copy was most of
        what a note cost to make, and rendering copies a note whenever it cuts, ties or divides one.
        """
        return note_of_checked_values(
            name=self._name, octave_number=self._octave_number, midi_number=self._midi_number, length=length, velocity=velocity, glide=glide,
        )

    def to_chord(self, typ):
        """Return a new Chord of the given ChordType with this note as its root.

        The root keeps its spelling, and the other notes are spelled as
        half_step spells them.
        """
        # Imported here because llamatron.music.chord imports Note from this module.
        from llamatron.music.chord import Chord, ChordType

        if not isinstance(typ, ChordType):
            raise ValueError(ERR_NOT_A_CHORD_TYPE.format(value=typ))
        return Chord([self, *(self.half_step(n) for n in typ.value)])

    def __eq__(self, other):
        if not isinstance(other, Note):
            return NotImplemented
        return (self._midi_number, self._length) == (other._midi_number, other._length)

    def __hash__(self):
        return hash((self._midi_number, self._length))

    def __repr__(self):
        return REPR_NOTE.format(name=self._name, octave_number=self._octave_number, length=self._length, velocity=self._velocity, glide=self._glide)


def note_of_checked_values(*, name, octave_number, midi_number, length, velocity, glide):
    """Return a Note from values that are already checked, without the constructor checking them again.

    Only a Note's own copies call this, each with what it took from a checked note and what it
    checked itself. Every note that skips the constructor is made here, so that the count of
    objects a render makes (internal_tools/time_renders.py) still counts each one.
    """
    note = _new(Note)
    note._name = name
    note._octave_number = octave_number
    note._length = length
    note._velocity = velocity
    note._glide = glide
    note._midi_number = midi_number
    return note


def _is_velocity(velocity):
    """Return whether a velocity is a whole number in MIDI's range for notes, not counting true and false."""
    return type(velocity) is int and MIN_VELOCITY <= velocity <= MAX_VELOCITY
