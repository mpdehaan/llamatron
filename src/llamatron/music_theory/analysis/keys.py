# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The key notes are in, found by how long each note of the octave sounds against Krumhansl and Kessler's profiles of the
major and minor keys, the standard way of finding a key from notes alone.

The notes are anything with a start, an end and a pitch, as a MIDI file's are or a rendered song's, in any one unit of time:
the profiles only weigh how long each sounds against the rest."""

from typing import NamedTuple

from llamatron.music_theory.fundamentals import intervals

# The Krumhansl-Kessler profiles: how well each note of the octave, from the tonic, fits a major and a minor key.
MAJOR_PROFILE = (6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88)
MINOR_PROFILE = (6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17)
MAJOR = 'major'
MINOR = 'minor'


class KeyFit(NamedTuple):
    """A key that notes fit: its tonic's place in the octave, 0 for C, whether it is major or minor, and how well the notes fit
    it, from -1 to 1."""

    tonic: int
    mode: str
    fit: float


def pitch_weights(notes):
    """Return how long each note of the octave sounds among some notes, C first."""
    weights = [0.0] * intervals.HALF_STEPS_PER_OCTAVE
    for note in notes:
        weights[note.pitch % intervals.HALF_STEPS_PER_OCTAVE] += float(note.end - note.start)
    return weights


def best_key(weights):
    """Return the key whose profile best matches how long each note of the octave sounds, C major where nothing sounds."""
    best = KeyFit(tonic=0, mode=MAJOR, fit=-1.0)
    for tonic in range(intervals.HALF_STEPS_PER_OCTAVE):
        rotated = [weights[(tonic + place) % intervals.HALF_STEPS_PER_OCTAVE] for place in range(intervals.HALF_STEPS_PER_OCTAVE)]
        for mode, profile in ((MAJOR, MAJOR_PROFILE), (MINOR, MINOR_PROFILE)):
            fit = correlation(first=rotated, second=profile)
            if fit > best.fit:
                best = KeyFit(tonic=tonic, mode=mode, fit=fit)
    return best


def key_of_notes(notes):
    """Return the key some notes are most likely in."""
    return best_key(pitch_weights(notes))


def correlation(*, first, second):
    """Return how closely two lists of numbers rise and fall together, from -1 to 1, or 0 when either is flat."""
    count = len(first)
    first_mean = sum(first) / count
    second_mean = sum(second) / count
    together = sum((a - first_mean) * (b - second_mean) for a, b in zip(first, second))
    spread = (sum((a - first_mean) ** 2 for a in first) * sum((b - second_mean) ** 2 for b in second)) ** 0.5
    return together / spread if spread else 0.0
