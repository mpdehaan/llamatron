# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The keys of an imported song, each a scale its scenes play in, and how a note is written as a degree of one.

A MIDI file says its key with a key signature, like Bb or F#m, which the import takes as a major
or minor scale. A file that says none has its key worked out from its notes, by how long each
note of the octave sounds against the Krumhansl-Kessler profiles of the major and minor keys,
the usual way (music_theory/analysis/keys.py). A note outside the scale is a degree with a sharp or a flat, sharps unless the
key's signature has flats, so every note keeps its pitch whatever the key.
"""

from typing import NamedTuple

from llamatron.model.objects.named_scale import scale_type_name
from llamatron.model.schema import limits
from llamatron.model.schema.file_format import Accidental
from llamatron.model.values import note as note_values
from llamatron.model.values.scale import ScaleType
from llamatron.music_theory.analysis import keys
from llamatron.music_theory.fundamentals import intervals

# A key signature as mido writes it ends in m for a minor key.
MINOR_MARK = 'm'
# The keys whose signatures have flats though their roots don't, which spell notes outside the scale with flats.
FLAT_KEYS = ('F', 'Dm', 'Gm', 'Cm', 'Fm')
FIRST_DEGREE = 1
# How a worked-out key's root is spelled, by the root's place in the octave, as its signature spells it.
MAJOR_ROOTS = ('C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B')
MINOR_ROOTS = ('C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'G#', 'A', 'Bb', 'B')


class MusicalKey(NamedTuple):
    """A key: its root's name, its scale type as a file writes it, like minor, and whether notes outside it are spelled with flats."""

    root: str
    kind: str
    flats: bool

    def half_steps(self):
        """Return one octave of the key's scale as half steps above the root."""
        return ScaleType[self.kind.upper()].value

    def root_place(self):
        """Return the root's place in the octave, 0 for C."""
        return pitch_class_of(self.root)


def pitch_class_of(name):
    """Return a note name's place in the octave, 0 for C, whether it is spelled with a sharp or a flat."""
    if name in note_values.SHARP_NAMES:
        return note_values.SHARP_NAMES.index(name)
    return note_values.FLAT_NAMES.index(name)


def key_of_signature(text):
    """Return the key a MIDI key signature names, like Bbm, with a root a scale can have: Cb, which no scale has, is B."""
    minor = text.endswith(MINOR_MARK)
    root = text[:-len(MINOR_MARK)] if minor else text
    flats = root.endswith(note_values.FLAT_SIGN) or text in FLAT_KEYS
    if root not in note_values.ROOT_NAMES:
        # A flat no scale has, Cb or Fb, is the white key a half step below its letter.
        root = note_values.SHARP_NAMES[(pitch_class_of(root[0]) - 1) % intervals.HALF_STEPS_PER_OCTAVE]
    kind = scale_type_name(ScaleType.MINOR if minor else ScaleType.MAJOR)
    return MusicalKey(root=root, kind=kind, flats=flats)


def key_of_notes(notes):
    """Return the key the notes are most likely in (music_theory/analysis/keys.py), C major for no notes."""
    fit = keys.key_of_notes(notes)
    roots = MAJOR_ROOTS
    kind = ScaleType.MAJOR
    if fit.mode == keys.MINOR:
        roots = MINOR_ROOTS
        kind = ScaleType.MINOR
    root = roots[fit.tonic]
    return MusicalKey(root=root, kind=scale_type_name(kind), flats=root.endswith(note_values.FLAT_SIGN))


def degree_of(*, pitch, key):
    """Return how a pattern writes a MIDI number in a key, as its degree, its accidental or None, and its octave, or None for a note too low for any octave.

    The octave is the one whose root the degree counts up from, as a pattern's Octave row is, so
    a note below the root in its octave belongs to the octave below.
    """
    steps = key.half_steps()
    octave, above = divmod(pitch - key.root_place(), intervals.HALF_STEPS_PER_OCTAVE)
    if above in steps:
        return within_octaves(degree=steps.index(above) + FIRST_DEGREE, accidental=None, octave=octave)
    if key.flats and above + 1 in steps:
        return within_octaves(degree=steps.index(above + 1) + FIRST_DEGREE, accidental=Accidental.FLAT, octave=octave)
    if above - 1 in steps:
        return within_octaves(degree=steps.index(above - 1) + FIRST_DEGREE, accidental=Accidental.SHARP, octave=octave)
    if above + 1 == intervals.HALF_STEPS_PER_OCTAVE:
        return within_octaves(degree=FIRST_DEGREE, accidental=Accidental.FLAT, octave=octave + 1)
    return within_octaves(degree=steps.index(above + 1) + FIRST_DEGREE, accidental=Accidental.FLAT, octave=octave)


def within_octaves(*, degree, accidental, octave):
    """Return a degree, accidental and octave, or None when the octave is outside the ones a pattern can hold."""
    if limits.MIN_OCTAVE <= octave <= limits.MAX_OCTAVE:
        return (degree, accidental, octave)
    return None


def drum_note_of(pitch):
    """Return how a drum pattern writes a MIDI number: its letter, its sharp or None, and its octave."""
    octave, place = divmod(pitch, intervals.HALF_STEPS_PER_OCTAVE)
    name = note_values.SHARP_NAMES[place]
    letter = name[0]
    return (letter, Accidental.SHARP if name != letter else None, octave)
