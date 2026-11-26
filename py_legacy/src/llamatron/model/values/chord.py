# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

from enum import Enum

from llamatron.model.values.note import Note
from llamatron.music_theory.fundamentals import chord_shapes
from llamatron.user_strings import errors, reprs

# A note with no length yet sorts as if it had none, after the ones that have one.
NO_LENGTH = 0


class ChordType(Enum):
    """Each chord llamatron names; each value is the chord's shape, its notes above the root as half steps
    (music_theory/fundamentals/chord_shapes.py), in the order and the groups of the shapes."""

    POWER = chord_shapes.POWER
    OCTAVE = chord_shapes.OCTAVE
    MINOR_THIRD = chord_shapes.MINOR_THIRD
    MAJOR_THIRD = chord_shapes.MAJOR_THIRD
    FOURTH = chord_shapes.FOURTH
    MINOR_SIXTH = chord_shapes.MINOR_SIXTH
    MAJOR_SIXTH = chord_shapes.MAJOR_SIXTH

    MAJOR = chord_shapes.MAJOR
    MINOR = chord_shapes.MINOR
    DIMINISHED = chord_shapes.DIMINISHED
    AUGMENTED = chord_shapes.AUGMENTED
    SUS2 = chord_shapes.SUS2
    SUS4 = chord_shapes.SUS4

    MAJOR6 = chord_shapes.MAJOR6
    MINOR6 = chord_shapes.MINOR6

    DOMINANT7 = chord_shapes.DOMINANT7
    MAJOR7 = chord_shapes.MAJOR7
    MINOR7 = chord_shapes.MINOR7
    MINOR_MAJOR7 = chord_shapes.MINOR_MAJOR7
    DIMINISHED7 = chord_shapes.DIMINISHED7
    HALF_DIMINISHED7 = chord_shapes.HALF_DIMINISHED7
    AUGMENTED7 = chord_shapes.AUGMENTED7
    AUGMENTED_MAJOR7 = chord_shapes.AUGMENTED_MAJOR7
    DOMINANT7_SUS4 = chord_shapes.DOMINANT7_SUS4

    ADD9 = chord_shapes.ADD9
    MINOR_ADD9 = chord_shapes.MINOR_ADD9

    DOMINANT9 = chord_shapes.DOMINANT9
    MAJOR9 = chord_shapes.MAJOR9
    MINOR9 = chord_shapes.MINOR9
    DOMINANT11 = chord_shapes.DOMINANT11
    MAJOR11 = chord_shapes.MAJOR11
    MINOR11 = chord_shapes.MINOR11
    DOMINANT13 = chord_shapes.DOMINANT13
    MAJOR13 = chord_shapes.MAJOR13
    MINOR13 = chord_shapes.MINOR13


class Chord:
    """A group of notes. Chords with the same pitches and lengths compare equal in any order.

    Chords are immutable: the notes are kept as a tuple, and there are no setters.
    """

    __slots__ = ('_notes',)

    def __init__(self, notes):
        if not isinstance(notes, (list, tuple)):
            raise ValueError(errors.ERR_CHORD_NOT_A_LIST.format(value=notes))
        if not notes:
            raise ValueError(errors.ERR_NO_NOTES)
        for note in notes:
            if not isinstance(note, Note):
                raise ValueError(errors.ERR_NOT_A_NOTE.format(value=note))
        # Copied into a tuple so that changing the caller's list can't change the chord.
        self._notes = tuple(notes)

    def get_notes(self):
        """The notes, in the order the chord was built in."""
        return self._notes

    def get_length(self):
        """The length of the longest note, or None if any note doesn't have a length yet."""
        lengths = [note.get_length() for note in self._notes]
        if None in lengths:
            return None
        return max(lengths)

    def __eq__(self, other):
        if not isinstance(other, Chord):
            return NotImplemented
        return self._sorted_pitches_and_lengths() == other._sorted_pitches_and_lengths()

    def __hash__(self):
        return hash(self._sorted_pitches_and_lengths())

    def __repr__(self):
        return reprs.REPR_CHORD.format(notes=self._notes)

    def _sorted_pitches_and_lengths(self):
        ordered = []
        for note in self._notes:
            length = note.get_length()
            # The middle value stops a length of None being compared with a number.
            ordered.append((note.get_midi_number(), length is None, length or NO_LENGTH))
        ordered.sort()
        return tuple(ordered)
