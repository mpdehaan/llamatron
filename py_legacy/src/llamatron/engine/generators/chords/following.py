# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Follow Chords: a chain generator that moves a clip's notes to the chords another track plays.

The clip's pattern is taken as written over chord I, as a Progression takes it. At each moment
the chord is the one most lately started on the track followed, in the same scene, after that
track's own chains: a chord written by hand there, or made by a Progression. A note is moved up
the clip's scale by as many notes as the chord's root is above the scale's, so the scale decides
the chord, and a root between two notes of the scale moves it the half steps left over besides.
A note written a third, a fifth or a seventh above the figure's root then takes the chord's own
note where the scale gave a note a half step off, so that a chord from outside the scale, a
major chord in a minor key, is followed too. Rests, rhythm, velocity and gates stay as written,
and before the first chord, or with no track to follow, nothing moves.
"""

from llamatron.engine.generators.base import ClipGenerator
from llamatron.engine.parts.scale_moves import along_scale
from llamatron.math import length
from llamatron.math.length import Length
from llamatron.model.values import sound as sound_values
from llamatron.model.values.sound import Sound
from llamatron.music_theory.fundamentals import intervals

# The half steps above a chord's root that its third, its fifth and its seventh can be, by the place above a figure's root, counted in notes of the scale from 0, that is the figure's.
KINDS_OF_CHORD_NOTE = {2: (3, 4), 4: (6, 7, 8), 6: (9, 10, 11)}
# How many notes a scale has when its thirds, fifths and sevenths lie at those places.
PLACED_SCALE_SIZE = 7


class FollowChords(ClipGenerator):
    """Moves a clip's notes to the chord sounding on another track."""

    __slots__ = ('_chords',)

    def __init__(self, *, chords=None, continuation=None):
        # What says the chord at a time, chord_at(time) giving its root's MIDI number and its notes within an octave, or None for no track to follow.
        self._chords = chords

    def _generate(self, clip):
        scale = clip.get_scale()
        if self._chords is None or scale is None:
            return list(clip.resolved_sounds()), clip.get_length()
        result = []
        now = length.ZERO
        for sound in clip.resolved_sounds():
            result.append(self._moved(sound=sound, start=now, scale=scale))
            now = Length.add(now, sound[sound_values.LENGTH])
        return result, clip.get_length()

    def _moved(self, *, sound, start, scale):
        """Return a sound moved to the chord playing as it starts, each part of a phrase to the chord playing as the part starts."""
        kind = sound[sound_values.KIND]
        if kind == sound_values.DEGREE:
            return self._moved(sound=Sound.settled(sound, scale), start=start, scale=scale)
        if kind == sound_values.HELD:
            return (sound_values.HELD, sound[sound_values.LENGTH], self._moved(sound=sound[sound_values.HELD_SOUND], start=start, scale=scale))
        if kind == sound_values.PHRASE:
            parts = []
            for part in sound[sound_values.PARTS]:
                parts.append(self._moved(sound=part, start=start, scale=scale))
                start = Length.add(start, part[sound_values.LENGTH])
            return (sound_values.PHRASE, sound[sound_values.LENGTH], tuple(parts))
        chord = self._chords.chord_at(Length.rational(start))
        if chord is None:
            return sound
        if kind == sound_values.NOTE:
            return _to_chord(note=sound, chord=chord, scale=scale)
        if kind == sound_values.CHORD:
            return Sound.chord([_to_chord(note=note, chord=chord, scale=scale) for note in sound[sound_values.NOTES]])
        return sound


def _to_chord(*, note, chord, scale):
    """Return a note moved to a chord, given as its root's MIDI number and its notes within an octave, or as it was where moving it would leave the MIDI range.

    A root on a note of the scale moves the note along the scale. A root between two notes of
    the scale moves it by the exact half steps from the scale's root to the chord's, keeping
    the figure's own sound, as a Progression moves a figure to a degree with a sharp or a flat.
    """
    root, held = chord
    steps, extra = _place_in(midi=root, scale=scale)
    try:
        if extra:
            moved = Sound.half_step(note, (root - scale.get_root().get_midi_number()) % intervals.HALF_STEPS_PER_OCTAVE)
        else:
            moved = along_scale(note=note, steps=steps, scale=scale)
        return _as_the_chord_has_it(note=note, moved=moved, chord=chord, scale=scale)
    except ValueError:
        return note


def _as_the_chord_has_it(*, note, moved, chord, scale):
    """Return a moved note as the chord's own third, fifth or seventh, where the note is the figure's third, fifth or seventh and the chord has another of that kind.

    Each kind is the half steps above a chord's root it can be: a third 3 or 4, a fifth 6, 7 or
    8, a seventh 9, 10 or 11. A chord with none of the kind, a triad with no seventh, says
    nothing of it, and one with two leaves the note as moved.
    """
    root, held = chord
    above, extra = _place_in(midi=note[sound_values.MIDI], scale=scale)
    if extra or above not in KINDS_OF_CHORD_NOTE or len(scale.get_type().value) != PLACED_SCALE_SIZE:
        return moved
    kind = KINDS_OF_CHORD_NOTE[above]
    own = (moved[sound_values.MIDI] - root) % intervals.HALF_STEPS_PER_OCTAVE
    has = [interval for interval in kind if (root + interval) % intervals.HALF_STEPS_PER_OCTAVE in held]
    if own not in kind or own in has or len(has) != 1:
        return moved
    return Sound.half_step(moved, has[0] - own)


def _place_in(*, midi, scale):
    """Return which note of a scale's octave, counted from 0, a MIDI number is at or just above, and how many half steps above it."""
    shape = scale.get_type().value
    within = (midi - scale.get_root().get_midi_number()) % intervals.HALF_STEPS_PER_OCTAVE
    place = max(index for index, step in enumerate(shape) if step <= within)
    return place, within - shape[place]
