# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Voice leading: moving from one chord to the next with as little movement as the notes allow.

A keyboard player going from C major to F major doesn't jump the whole hand up a fourth: C stays, E moves up a half step to F,
and G up a whole step to A, so that the voices, each finger's line, move as little as they can. The same chord can be voiced
many ways, in an inversion, with some of its notes an octave up, and in another octave altogether; voice leading chooses the
voicing whose notes move least from the chord before. Pitches here are MIDI numbers.
"""

from llamatron.music_theory.fundamentals import intervals


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


def inverted(*, pitches, inversion):
    """Return a chord's pitches, given lowest first, as an inversion plays them: so many of its lowest notes an octave up, never
    all of them, each pitch lining up with the one it came from."""
    return _lowest_moved_up(pitches=pitches, moved=min(inversion, len(pitches) - 1))


def inversions(pitches):
    """Return every inversion of a chord's pitches given lowest first: root position, then the lowest one, two and more moved up
    an octave."""
    return [_lowest_moved_up(pitches=pitches, moved=moved) for moved in range(len(pitches))]


def voiced(*, pitches, inversion, shift):
    """Return a chord's pitches in an inversion, moved so many octaves."""
    return [pitch + shift * intervals.HALF_STEPS_PER_OCTAVE for pitch in inverted(pitches=pitches, inversion=inversion)]


def _lowest_moved_up(*, pitches, moved):
    """Return pitches given lowest first with the lowest so many of them moved up an octave."""
    played = []
    for place, pitch in enumerate(pitches):
        if place < moved:
            pitch += intervals.HALF_STEPS_PER_OCTAVE
        played.append(pitch)
    return played
