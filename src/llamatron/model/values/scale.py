# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

from enum import Enum

from llamatron.math.length import Length
from llamatron.model.values import midi as midi_numbers, note
from llamatron.model.values.note import Note
from llamatron.model.values.sound import Sound
from llamatron.music_theory.fundamentals import intervals, scale_shapes
from llamatron.user_strings import errors, reprs


class ScaleType(Enum):
    """Each scale llamatron names, by the name a set file writes; each value is the scale's shape, one octave as half steps
    above the root (music_theory/fundamentals/scale_shapes.py). A name with the same shape as one before it is another name for
    that scale. The scales come in the order and the groups of their shapes, where each group is said."""

    MAJOR = scale_shapes.MAJOR
    IONIAN = scale_shapes.IONIAN
    DORIAN = scale_shapes.DORIAN
    PHRYGIAN = scale_shapes.PHRYGIAN
    LYDIAN = scale_shapes.LYDIAN
    MIXOLYDIAN = scale_shapes.MIXOLYDIAN
    MINOR = scale_shapes.MINOR
    AEOLIAN = scale_shapes.AEOLIAN
    NATURAL_MINOR = scale_shapes.NATURAL_MINOR
    LOCRIAN = scale_shapes.LOCRIAN

    HARMONIC_MINOR = scale_shapes.HARMONIC_MINOR
    MELODIC_MINOR = scale_shapes.MELODIC_MINOR
    HARMONIC_MAJOR = scale_shapes.HARMONIC_MAJOR

    MAJOR_PENTATONIC = scale_shapes.MAJOR_PENTATONIC
    MINOR_PENTATONIC = scale_shapes.MINOR_PENTATONIC
    BLUES = scale_shapes.BLUES
    MAJOR_BLUES = scale_shapes.MAJOR_BLUES

    CHROMATIC = scale_shapes.CHROMATIC
    WHOLE_TONE = scale_shapes.WHOLE_TONE
    WHOLE_HALF_DIMINISHED = scale_shapes.WHOLE_HALF_DIMINISHED
    HALF_WHOLE_DIMINISHED = scale_shapes.HALF_WHOLE_DIMINISHED
    AUGMENTED = scale_shapes.AUGMENTED

    DORIAN_FLAT2 = scale_shapes.DORIAN_FLAT2
    LYDIAN_AUGMENTED = scale_shapes.LYDIAN_AUGMENTED
    LYDIAN_DOMINANT = scale_shapes.LYDIAN_DOMINANT
    MIXOLYDIAN_FLAT6 = scale_shapes.MIXOLYDIAN_FLAT6
    LOCRIAN_NATURAL2 = scale_shapes.LOCRIAN_NATURAL2
    ALTERED = scale_shapes.ALTERED

    BEBOP_DOMINANT = scale_shapes.BEBOP_DOMINANT
    BEBOP_MAJOR = scale_shapes.BEBOP_MAJOR
    PROMETHEUS = scale_shapes.PROMETHEUS

    PHRYGIAN_DOMINANT = scale_shapes.PHRYGIAN_DOMINANT
    DOUBLE_HARMONIC = scale_shapes.DOUBLE_HARMONIC
    HUNGARIAN_MINOR = scale_shapes.HUNGARIAN_MINOR
    HUNGARIAN_MAJOR = scale_shapes.HUNGARIAN_MAJOR
    UKRAINIAN_DORIAN = scale_shapes.UKRAINIAN_DORIAN
    PERSIAN = scale_shapes.PERSIAN
    NEAPOLITAN_MINOR = scale_shapes.NEAPOLITAN_MINOR
    NEAPOLITAN_MAJOR = scale_shapes.NEAPOLITAN_MAJOR
    ENIGMATIC = scale_shapes.ENIGMATIC

    EGYPTIAN = scale_shapes.EGYPTIAN
    HIRAJOSHI = scale_shapes.HIRAJOSHI
    IN_SEN = scale_shapes.IN_SEN
    IWATO = scale_shapes.IWATO
    KUMOI = scale_shapes.KUMOI
    YO = scale_shapes.YO
    RYUKYU = scale_shapes.RYUKYU

    TODI = scale_shapes.TODI
    MARWA = scale_shapes.MARWA
    PURVI = scale_shapes.PURVI
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
        name, octave_number = self._root.spelled_half_step(octaves * intervals.HALF_STEPS_PER_OCTAVE + steps[index] + half_steps)
        return Note(name=name, octave_number=octave_number, length=length, velocity=velocity, glide=glide)

    def sound_at(self, *, degree, scale_notes, half_steps, length, velocity=None, glide=False):
        """Return the note a degree of the scale plays as a sound, the tuple a render makes (model/values/sound.py), with its length as a pair.

        It is the note note_at gives, worked out without making one: the root's MIDI number
        and whether it is spelled with flats are all that the note needs. A note outside the
        MIDI range raises what note_at raises. The degree is one a pattern or a Degree checked.
        """
        steps = self._typ.value
        octaves, index = divmod(degree - note.FIRST_DEGREE + scale_notes, len(steps))
        root = self._root
        midi = root.get_midi_number() + octaves * intervals.HALF_STEPS_PER_OCTAVE + steps[index] + half_steps
        if midi_numbers.MIN_MIDI_NUMBER <= midi <= midi_numbers.MAX_MIDI_NUMBER:
            names = note.SHARP_NAMES
            if root.get_name().endswith(note.FLAT_SIGN):
                names = note.FLAT_NAMES
            return Sound.note(length=length, midi=midi, velocity=velocity, glide=glide, name=names[midi % intervals.HALF_STEPS_PER_OCTAVE])
        # The class says what is wrong with the note, in the words it always has.
        number = None
        if length is not None:
            number = Length.rational(length)
        return Sound.of(self.note_at(degree=degree, scale_notes=scale_notes, half_steps=half_steps, length=number, velocity=velocity, glide=glide))

    def __eq__(self, other):
        if not isinstance(other, Scale):
            return NotImplemented
        return (self._root, self._typ) == (other._root, other._typ)

    def __hash__(self):
        return hash((self._root, self._typ))

    def __repr__(self):
        return reprs.REPR_SCALE.format(root=self._root, typ=self._typ)
