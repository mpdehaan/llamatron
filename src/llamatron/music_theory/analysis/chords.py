# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The chord that sounds in a stretch of music, found by matching how long each note of the octave sounds against chord
shapes: the shape that covers most of what sounds, few notes left over, its root sounding, wins."""

from llamatron.music_theory.fundamentals import intervals

# The qualities of the chords matched, as the genre library writes them.
MAJOR = 'M'
MINOR = 'm'
DOMINANT_SEVENTH = '7'
MAJOR_SEVENTH = 'M7'
MINOR_SEVENTH = 'm7'
DIMINISHED = 'dim'
HALF_DIMINISHED = 'm7b5'
AUGMENTED = 'aug'
SUSPENDED_FOURTH = 'sus4'
SUSPENDED_SECOND = 'sus2'
POWER = '5'
# The chord shapes matched, as half steps above the root, by quality.
CHORD_SHAPES = {
    MAJOR: (0, 4, 7), MINOR: (0, 3, 7), DOMINANT_SEVENTH: (0, 4, 7, 10), MAJOR_SEVENTH: (0, 4, 7, 11), MINOR_SEVENTH: (0, 3, 7, 10),
    DIMINISHED: (0, 3, 6), HALF_DIMINISHED: (0, 3, 6, 10), AUGMENTED: (0, 4, 8), SUSPENDED_FOURTH: (0, 5, 7), SUSPENDED_SECOND: (0, 2, 7), POWER: (0, 7),
}
# A note of the octave counts as sounding when it carries this share of what sounds, and a chord needs two such notes.
LONE_NOTE_SHARE = 0.05
FEWEST_CHORD_NOTES = 2
# What each note of a shape costs, so that a shape no bigger than what sounds wins, and how much the root's sounding counts.
SHAPE_NOTE_COST = 0.06
ROOT_WEIGHT = 0.5


def chord_of(weights):
    """Return the chord (root, quality) whose shape best covers the notes sounding, by how long each note of the octave sounds,
    C first; or None in silence and where one note sounds alone, as under a bass playing by itself, since a single note is no
    chord."""
    total = sum(weights)
    if total == 0 or sum(1 for weight in weights if weight / total >= LONE_NOTE_SHARE) < FEWEST_CHORD_NOTES:
        return None
    best = None
    best_score = None
    for root in range(intervals.HALF_STEPS_PER_OCTAVE):
        for quality, shape in CHORD_SHAPES.items():
            inside = sum(weights[(root + step) % intervals.HALF_STEPS_PER_OCTAVE] for step in shape)
            score = inside / total - SHAPE_NOTE_COST * len(shape) + ROOT_WEIGHT * weights[root] / total
            if best_score is None or score > best_score:
                best = (root, quality)
                best_score = score
    return best
