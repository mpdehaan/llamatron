# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Chords built on single notes, which Guitarify and the Chords generator's AutoChord share: the triad a note's place in a scale
builds, and a chord of fixed half steps on a note or ending on it."""

from llamatron.model.values import midi as midi_numbers, sound as sound_values
from llamatron.model.values.sound import Sound
from llamatron.music_theory.fundamentals import intervals

# A triad's third and fifth, counted in notes of the scale above its root.
TRIAD_STEPS = (2, 4)


def triad_above(*, note, scale):
    """Return how many half steps above a note the third and the fifth of the chord its place in a scale builds are, or nothing
    for a note outside the scale."""
    steps = scale.get_type().value
    place = (note[sound_values.MIDI] - scale.get_root().get_midi_number()) % intervals.HALF_STEPS_PER_OCTAVE
    if place not in steps:
        return ()
    index = steps.index(place)
    above = []
    for along in TRIAD_STEPS:
        octaves, wrapped = divmod(index + along, len(steps))
        above.append(octaves * intervals.HALF_STEPS_PER_OCTAVE + steps[wrapped] - place)
    return tuple(above)


def chord_on(*, note, above, on_top=False):
    """Return a chord of a note and the notes some half steps above it, or, on_top, the same chord ending on the note: each other
    note an octave lower, so that a melody keeps its line. A note that would fall outside MIDI's range is left out."""
    pitch = note[sound_values.MIDI]
    pitches = [pitch, *(pitch + half_steps for half_steps in above)]
    if on_top:
        pitches = sorted({pitch - intervals.HALF_STEPS_PER_OCTAVE + half_steps for half_steps in above} | {pitch})
    notes = []
    for each in pitches:
        if midi_numbers.MIN_MIDI_NUMBER <= each <= midi_numbers.MAX_MIDI_NUMBER:
            notes.append(Sound.half_step(note, each - pitch))
    return Sound.chord(notes)
