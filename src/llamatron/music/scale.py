# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

from enum import Enum

from llamatron.math.length import Length
from llamatron.music import midi as midi_numbers, note
from llamatron.music.note import Note
from llamatron.music.sound import Sound
from llamatron.user_strings import errors, reprs


class ScaleType(Enum):
    """Each value is one octave of the scale, as half steps above the root."""

    # Major and its modes. IONIAN is another name for MAJOR, and AEOLIAN and
    # NATURAL_MINOR are other names for MINOR.
    MAJOR = (0, 2, 4, 5, 7, 9, 11)
    IONIAN = MAJOR
    DORIAN = (0, 2, 3, 5, 7, 9, 10)
    PHRYGIAN = (0, 1, 3, 5, 7, 8, 10)
    LYDIAN = (0, 2, 4, 6, 7, 9, 11)
    MIXOLYDIAN = (0, 2, 4, 5, 7, 9, 10)
    MINOR = (0, 2, 3, 5, 7, 8, 10)
    AEOLIAN = MINOR
    NATURAL_MINOR = MINOR
    LOCRIAN = (0, 1, 3, 5, 6, 8, 10)

    # Other major and minor scales. MELODIC_MINOR is the ascending form.
    HARMONIC_MINOR = (0, 2, 3, 5, 7, 8, 11)
    MELODIC_MINOR = (0, 2, 3, 5, 7, 9, 11)
    HARMONIC_MAJOR = (0, 2, 4, 5, 7, 8, 11)

    # Pentatonic and blues
    MAJOR_PENTATONIC = (0, 2, 4, 7, 9)
    MINOR_PENTATONIC = (0, 3, 5, 7, 10)
    BLUES = (0, 3, 5, 6, 7, 10)
    MAJOR_BLUES = (0, 2, 3, 4, 7, 9)

    # Symmetric scales
    CHROMATIC = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)
    WHOLE_TONE = (0, 2, 4, 6, 8, 10)
    WHOLE_HALF_DIMINISHED = (0, 2, 3, 5, 6, 8, 9, 11)
    HALF_WHOLE_DIMINISHED = (0, 1, 3, 4, 6, 7, 9, 10)
    AUGMENTED = (0, 3, 4, 7, 8, 11)

    # The modes of melodic minor, after melodic minor itself. Flat and natural are spelled
    # out, so DORIAN_FLAT2 is dorian b2.
    DORIAN_FLAT2 = (0, 1, 3, 5, 7, 9, 10)
    LYDIAN_AUGMENTED = (0, 2, 4, 6, 8, 9, 11)
    LYDIAN_DOMINANT = (0, 2, 4, 6, 7, 9, 10)
    MIXOLYDIAN_FLAT6 = (0, 2, 4, 5, 7, 8, 10)
    LOCRIAN_NATURAL2 = (0, 2, 3, 5, 6, 8, 10)
    ALTERED = (0, 1, 3, 4, 6, 8, 10)

    # Jazz
    BEBOP_DOMINANT = (0, 2, 4, 5, 7, 9, 10, 11)
    BEBOP_MAJOR = (0, 2, 4, 5, 7, 8, 9, 11)
    PROMETHEUS = (0, 2, 4, 6, 9, 10)

    # The Middle East and Europe
    PHRYGIAN_DOMINANT = (0, 1, 4, 5, 7, 8, 10)
    DOUBLE_HARMONIC = (0, 1, 4, 5, 7, 8, 11)
    HUNGARIAN_MINOR = (0, 2, 3, 6, 7, 8, 11)
    HUNGARIAN_MAJOR = (0, 3, 4, 6, 7, 9, 10)
    UKRAINIAN_DORIAN = (0, 2, 3, 6, 7, 9, 10)
    PERSIAN = (0, 1, 4, 5, 6, 8, 11)
    NEAPOLITAN_MINOR = (0, 1, 3, 5, 7, 8, 11)
    NEAPOLITAN_MAJOR = (0, 1, 3, 5, 7, 9, 11)
    ENIGMATIC = (0, 1, 4, 6, 8, 10, 11)

    # Egypt and East Asia. RYUKYU is the Okinawan scale.
    EGYPTIAN = (0, 2, 5, 7, 10)
    HIRAJOSHI = (0, 2, 3, 7, 8)
    IN_SEN = (0, 1, 5, 7, 10)
    IWATO = (0, 1, 5, 6, 10)
    KUMOI = (0, 2, 3, 7, 9)
    YO = (0, 2, 5, 7, 9)
    RYUKYU = (0, 4, 5, 7, 11)

    # Indian ragas, in twelve notes to the octave
    TODI = (0, 1, 3, 6, 7, 8, 11)
    MARWA = (0, 1, 4, 6, 7, 9, 11)
    PURVI = (0, 1, 4, 6, 7, 8, 11)


class Scale:
    """A scale that runs upward from its root to the top of the MIDI range.

    Every note in the scale has the same length as the root. Scales are immutable: there
    are no setters.
    """

    __slots__ = ('_root', '_typ')

    def __init__(self, *, root, typ):
        if not isinstance(root, Note):
            raise ValueError(errors.ERR_NOT_A_NOTE.format(value=root))
        if not isinstance(typ, ScaleType):
            raise ValueError(errors.ERR_NOT_A_SCALE_TYPE.format(value=typ))
        self._root = root
        self._typ = typ

    def get_root(self):
        return self._root

    def get_type(self):
        return self._typ

    def note_at(self, *, degree, scale_notes, half_steps, length, velocity=None, glide=False):
        """Return the Note a degree of the scale plays, moved scale_notes along the scale and then by half steps.

        Degrees are numbered from 1, the root, and carry on past the top of the scale into the
        octaves above. The note is spelled as the root's half_step spells it, and is made once,
        with its length, velocity and glide, which is why playing a pattern asks for it here
        rather than making a Degree and then a copy of its note for each thing a step sets.
        """
        # bool is a subclass of int, but True is not a real degree.
        if type(degree) is not int or degree < note.FIRST_DEGREE:
            raise ValueError(errors.ERR_BAD_DEGREE.format(value=degree, lowest=note.FIRST_DEGREE))
        steps = self._typ.value
        octaves, index = divmod(degree - note.FIRST_DEGREE + scale_notes, len(steps))
        name, octave_number = self._root.spelled_half_step(octaves * midi_numbers.HALF_STEPS_PER_OCTAVE + steps[index] + half_steps)
        return Note(name=name, octave_number=octave_number, length=length, velocity=velocity, glide=glide)

    def sound_at(self, *, degree, scale_notes, half_steps, length, velocity=None, glide=False):
        """Return the note a degree of the scale plays as a sound, the tuple a render makes (music/sound.py), with its length as a pair.

        It is the note note_at gives, worked out without making one: the root's MIDI number
        and whether it is spelled with flats are all that the note needs. A note outside the
        MIDI range raises what note_at raises. The degree is one a pattern or a Degree checked.
        """
        steps = self._typ.value
        octaves, index = divmod(degree - note.FIRST_DEGREE + scale_notes, len(steps))
        root = self._root
        midi = root.get_midi_number() + octaves * midi_numbers.HALF_STEPS_PER_OCTAVE + steps[index] + half_steps
        if midi_numbers.MIN_MIDI_NUMBER <= midi <= midi_numbers.MAX_MIDI_NUMBER:
            names = note.FLAT_NAMES if root.get_name().endswith(note.FLAT_SIGN) else note.SHARP_NAMES
            return Sound.note(length=length, midi=midi, velocity=velocity, glide=glide, name=names[midi % midi_numbers.HALF_STEPS_PER_OCTAVE])
        # The class says what is wrong with the note, in the words it always has.
        number = None if length is None else Length.rational(length)
        return Sound.of(self.note_at(degree=degree, scale_notes=scale_notes, half_steps=half_steps, length=number, velocity=velocity, glide=glide))

    def __eq__(self, other):
        if not isinstance(other, Scale):
            return NotImplemented
        return (self._root, self._typ) == (other._root, other._typ)

    def __hash__(self):
        return hash((self._root, self._typ))

    def __repr__(self):
        return reprs.REPR_SCALE.format(root=self._root, typ=self._typ)
