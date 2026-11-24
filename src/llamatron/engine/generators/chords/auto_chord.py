# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""AutoChord: the Chords generator's mode that turns each single note of a clip into a chord, so that an instrument needs no
chords of its own to play them.

From scale builds the triad the note's place in the clip's scale builds, major, minor, diminished or augmented as the scale
says, and leaves a note outside the scale a single note, a passing note staying a passing note. Major, Minor, Augmented,
Diminished and Power build that chord on the note whatever the scale. The note is the chord's root, or, with Note on top, the
chord's top, its other notes an octave down, so that a melody keeps its line. A sound that is already a chord of more than one
note is left as it is, and rests, rhythm, velocity and gates stay as written.
"""

from llamatron.engine.generators.base import ClipGenerator
from llamatron.engine.parts.chords_on_notes import chord_on, triad_above
from llamatron.model.values import sound as sound_values
from llamatron.model.values.sound import Sound

FROM_SCALE = 'from_scale'
MAJOR = 'major'
MINOR = 'minor'
AUGMENTED = 'augmented'
DIMINISHED = 'diminished'
POWER = 'power'
CHORDS = (FROM_SCALE, MAJOR, MINOR, AUGMENTED, DIMINISHED, POWER)
DEFAULT_CHORD = FROM_SCALE
# The half steps above the root of each fixed chord: its third and fifth, a power chord's fifth and octave.
FIXED_CHORDS = {MAJOR: (4, 7), MINOR: (3, 7), AUGMENTED: (4, 8), DIMINISHED: (3, 6), POWER: (7, 12)}


class AutoChord(ClipGenerator):
    """Turns each single note of a clip into its chord: chord is one of CHORDS, on_top whether the note ends the chord."""

    __slots__ = ('_chord', '_on_top')

    def __init__(self, *, chord=DEFAULT_CHORD, on_top=False):
        self._chord = chord
        self._on_top = on_top

    def _generate(self, clip):
        scale = clip.get_scale()
        return [self._chorded(sound=sound, scale=scale) for sound in clip.resolved_sounds()], clip.get_length()

    def _chorded(self, *, sound, scale):
        """Return a sound with each single note in it made a chord: a held sound's and each part of a phrase's too."""
        kind = sound[sound_values.KIND]
        if kind == sound_values.HELD:
            return (sound_values.HELD, sound[sound_values.LENGTH], self._chorded(sound=sound[sound_values.HELD_SOUND], scale=scale))
        if kind == sound_values.PHRASE:
            parts = [self._chorded(sound=part, scale=scale) for part in sound[sound_values.PARTS]]
            return (sound_values.PHRASE, sound[sound_values.LENGTH], tuple(parts))
        if kind == sound_values.DEGREE:
            if scale is None:
                return sound
            return self._chorded(sound=Sound.settled(sound, scale), scale=scale)
        if kind == sound_values.CHORD and len(sound[sound_values.NOTES]) == 1:
            return self._chorded(sound=sound[sound_values.NOTES][0], scale=scale)
        if kind == sound_values.NOTE:
            return self._built(note=sound, scale=scale)
        return sound

    def _built(self, *, note, scale):
        """Return a single note's chord, or the note itself where From scale finds it outside the scale, or there is no scale."""
        above = FIXED_CHORDS.get(self._chord)
        if above is None:
            if scale is None:
                return note
            above = triad_above(note=note, scale=scale)
            if not above:
                return note
        return chord_on(note=note, above=above, on_top=self._on_top)
