# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What each position of a clip sounds, for the timing code: a degree settled into its note in a scale, the notes a position
sounds by MIDI number, and a note as it plays, with how loud a note with no velocity of its own is and how far a glide runs on."""

from typing import NamedTuple

from llamatron.music import midi, sound
from llamatron.music.sound import Sound
from llamatron.strings import errors
from llamatron.support.length import Length
from llamatron.support.rational import Rational

# A note with no velocity of its own plays as loud as MIDI allows.
VELOCITY = midi.MAX_VELOCITY
# How far a note with glide runs into the next one, in fractions of a whole note.
GLIDE_OVERLAP = Rational(1, 128)


class NoteEvent(NamedTuple):
    """One note as it plays: when it starts and ends, in whole notes from the clip's start, its MIDI number and velocity."""

    start: Rational
    end: Rational
    midi_number: int
    velocity: int


def degree_to_note(*, position, scale):
    """Return the note a degree plays in a scale, leaving anything else as it is."""
    if position[sound.KIND] != sound.DEGREE:
        return position
    if scale is None:
        raise ValueError(errors.ERR_DEGREE_NEEDS_SCALE.format(degree=Sound.position(position)))
    return Sound.settled(position, scale)


def sounding_notes(position):
    """Return {MIDI number: note} for one position in a clip, keeping the longest of any pitch."""
    kind = position[sound.KIND]
    if kind == sound.REST:
        return {}
    if kind == sound.NOTE:
        return {position[sound.MIDI]: position}
    if kind == sound.CHORD:
        notes = {}
        for note in position[sound.NOTES]:
            if note[sound.MIDI] not in notes or Length.less(notes[note[sound.MIDI]][sound.LENGTH], note[sound.LENGTH]):
                notes[note[sound.MIDI]] = note
        return notes
    raise ValueError(errors.ERR_TIMING_NOT_A_POSITION.format(value=Sound.position(position)))


def velocity_of(note):
    """Return how loud a note plays: its own velocity, or VELOCITY where it has none."""
    return VELOCITY if note[sound.VELOCITY] is None else note[sound.VELOCITY]
