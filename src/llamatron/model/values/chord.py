# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

from enum import Enum

from llamatron.model.values.note import Note
from llamatron.user_strings import errors, reprs

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


def movement(*, pitches, before):
    """Return how far a voicing's notes move from the chord before, as MIDI numbers: lowest to lowest when both have as many
    notes, and otherwise each note to the nearest of the chord before. Voice leading and the munge that voices chords nearest
    both choose the voicing that moves least."""
    now = sorted(pitches)
    moved = 0
    if len(now) == len(before):
        for pitch, other in zip(now, before):
            moved += abs(pitch - other)
        return moved
    for pitch in now:
        moved += distance_to_nearest(pitch=pitch, others=before)
    return moved


def distance_to_nearest(*, pitch, others):
    """Return how far a pitch is from the nearest of other pitches."""
    distances = []
    for other in others:
        distances.append(abs(pitch - other))
    return min(distances)
