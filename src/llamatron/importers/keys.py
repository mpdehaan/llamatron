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
"""The keys of an imported song, each a scale its scenes play in, and how a note is written as a degree of one.

A MIDI file says its key with a key signature, like Bb or F#m, which the import takes as a major
or minor scale. A file that says none has its key worked out from its notes, by how long each
note of the octave sounds against the Krumhansl-Kessler profiles of the major and minor keys,
the usual way. A note outside the scale is a degree with a sharp or a flat, sharps unless the
key's signature has flats, so every note keeps its pitch whatever the key.
"""

from typing import NamedTuple

from llamatron.composition.file_format import Accidental
from llamatron.composition.limits import MAX_OCTAVE, MIN_OCTAVE
from llamatron.composition.named_scale import scale_type_name
from llamatron.music.midi import HALF_STEPS_PER_OCTAVE
from llamatron.music.note import FLAT_NAMES, FLAT_SIGN, ROOT_NAMES, SHARP_NAMES
from llamatron.music.scale import ScaleType

# A key signature as mido writes it ends in m for a minor key.
MINOR_MARK = 'm'
# The keys whose signatures have flats though their roots don't, which spell notes outside the scale with flats.
FLAT_KEYS = ('F', 'Dm', 'Gm', 'Cm', 'Fm')
FIRST_DEGREE = 1
# The Krumhansl-Kessler profiles: how well each note of the octave, from the root, fits a major and a minor key.
MAJOR_PROFILE = (6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88)
MINOR_PROFILE = (6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17)
# How a worked-out key's root is spelled, by the root's place in the octave, as its signature spells it.
MAJOR_ROOTS = ('C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B')
MINOR_ROOTS = ('C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'G#', 'A', 'Bb', 'B')


class Key(NamedTuple):
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
    if name in SHARP_NAMES:
        return SHARP_NAMES.index(name)
    return FLAT_NAMES.index(name)


def key_of_signature(text):
    """Return the key a MIDI key signature names, like Bbm, with a root a scale can have: Cb, which no scale has, is B."""
    minor = text.endswith(MINOR_MARK)
    root = text[:-len(MINOR_MARK)] if minor else text
    flats = root.endswith(FLAT_SIGN) or text in FLAT_KEYS
    if root not in ROOT_NAMES:
        # A flat no scale has, Cb or Fb, is the white key a half step below its letter.
        root = SHARP_NAMES[(pitch_class_of(root[0]) - 1) % HALF_STEPS_PER_OCTAVE]
    kind = scale_type_name(ScaleType.MINOR if minor else ScaleType.MAJOR)
    return Key(root=root, kind=kind, flats=flats)


def key_of_notes(notes):
    """Return the key the notes are most likely in, by how long each note of the octave sounds, C major for no notes."""
    weights = [0.0] * HALF_STEPS_PER_OCTAVE
    for note in notes:
        weights[note.pitch % HALF_STEPS_PER_OCTAVE] += float(note.end - note.start)
    best = None
    for root in range(HALF_STEPS_PER_OCTAVE):
        for profile, kind, names in ((MAJOR_PROFILE, ScaleType.MAJOR, MAJOR_ROOTS), (MINOR_PROFILE, ScaleType.MINOR, MINOR_ROOTS)):
            fit = correlation(first=[weights[(root + place) % HALF_STEPS_PER_OCTAVE] for place in range(HALF_STEPS_PER_OCTAVE)], second=profile)
            if best is None or fit > best[0]:
                best = (fit, names[root], kind)
    _, root, kind = best
    return Key(root=root, kind=scale_type_name(kind), flats=root.endswith(FLAT_SIGN))


def correlation(*, first, second):
    """Return how closely two lists of numbers rise and fall together, from -1 to 1, or 0 when either is flat."""
    count = len(first)
    first_mean = sum(first) / count
    second_mean = sum(second) / count
    together = sum((a - first_mean) * (b - second_mean) for a, b in zip(first, second))
    spread = (sum((a - first_mean) ** 2 for a in first) * sum((b - second_mean) ** 2 for b in second)) ** 0.5
    return together / spread if spread else 0.0


def degree_of(*, pitch, key):
    """Return how a pattern writes a MIDI number in a key, as its degree, its accidental or None, and its octave, or None for a note too low for any octave.

    The octave is the one whose root the degree counts up from, as a pattern's Octave row is, so
    a note below the root in its octave belongs to the octave below.
    """
    steps = key.half_steps()
    octave, above = divmod(pitch - key.root_place(), HALF_STEPS_PER_OCTAVE)
    if above in steps:
        return within_octaves(degree=steps.index(above) + FIRST_DEGREE, accidental=None, octave=octave)
    if key.flats and above + 1 in steps:
        return within_octaves(degree=steps.index(above + 1) + FIRST_DEGREE, accidental=Accidental.FLAT, octave=octave)
    if above - 1 in steps:
        return within_octaves(degree=steps.index(above - 1) + FIRST_DEGREE, accidental=Accidental.SHARP, octave=octave)
    if above + 1 == HALF_STEPS_PER_OCTAVE:
        return within_octaves(degree=FIRST_DEGREE, accidental=Accidental.FLAT, octave=octave + 1)
    return within_octaves(degree=steps.index(above + 1) + FIRST_DEGREE, accidental=Accidental.FLAT, octave=octave)


def within_octaves(*, degree, accidental, octave):
    """Return a degree, accidental and octave, or None when the octave is outside the ones a pattern can hold."""
    if MIN_OCTAVE <= octave <= MAX_OCTAVE:
        return (degree, accidental, octave)
    return None


def drum_note_of(pitch):
    """Return how a drum pattern writes a MIDI number: its letter, its sharp or None, and its octave."""
    octave, place = divmod(pitch, HALF_STEPS_PER_OCTAVE)
    name = SHARP_NAMES[place]
    letter = name[0]
    return (letter, Accidental.SHARP if name != letter else None, octave)
