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

from llamatron.generators.arp import along_scale
from llamatron.generators.base import ClipGenerator
from llamatron.music.sound import CHORD, DEGREE, HELD, HELD_SOUND, KIND, LENGTH, MIDI, NOTE, NOTES, PARTS, PHRASE, Sound
from llamatron.support.length import ZERO, Length

HALF_STEPS_PER_OCTAVE = 12
HALF_STEP = 1
# The places above a figure's root, counted in notes of the scale from 0, that are a chord's third, fifth and seventh.
CHORD_PLACES = (2, 4, 6)
# How many notes a scale has when its thirds, fifths and sevenths lie at those places.
PLACED_SCALE_SIZE = 7
# How many different notes a chord needs before it says what its third is.
FEWEST_NOTES_OF_A_FULL_CHORD = 3


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
        now = ZERO
        for sound in clip.resolved_sounds():
            result.append(self._moved(sound=sound, start=now, scale=scale))
            now = Length.add(now, sound[LENGTH])
        return result, clip.get_length()

    def _moved(self, *, sound, start, scale):
        """Return a sound moved to the chord playing as it starts, each part of a phrase to the chord playing as the part starts."""
        kind = sound[KIND]
        if kind == DEGREE:
            return self._moved(sound=Sound.settled(sound, scale), start=start, scale=scale)
        if kind == HELD:
            return (HELD, sound[LENGTH], self._moved(sound=sound[HELD_SOUND], start=start, scale=scale))
        if kind == PHRASE:
            parts = []
            for part in sound[PARTS]:
                parts.append(self._moved(sound=part, start=start, scale=scale))
                start = Length.add(start, part[LENGTH])
            return (PHRASE, sound[LENGTH], tuple(parts))
        chord = self._chords.chord_at(Length.rational(start))
        if chord is None:
            return sound
        if kind == NOTE:
            return _to_chord(note=sound, chord=chord, scale=scale)
        if kind == CHORD:
            return Sound.chord([_to_chord(note=note, chord=chord, scale=scale) for note in sound[NOTES]])
        return sound


def _to_chord(*, note, chord, scale):
    """Return a note moved to a chord, given as its root's MIDI number and its notes within an octave, or as it was where moving it would leave the MIDI range."""
    root, held = chord
    steps, extra = _place_in(midi=root, scale=scale)
    try:
        moved = along_scale(note=note, steps=steps, scale=scale)
        if extra:
            moved = Sound.half_step(moved, extra)
        return _as_the_chord_has_it(note=note, moved=moved, held=held, scale=scale)
    except ValueError:
        return note


def _as_the_chord_has_it(*, note, moved, held, scale):
    """Return a moved note as the chord's own third, fifth or seventh where the scale's is a half step off the chord's."""
    above, extra = _place_in(midi=note[MIDI], scale=scale)
    if extra or above not in CHORD_PLACES or len(scale.get_type().value) != PLACED_SCALE_SIZE or len(held) < FEWEST_NOTES_OF_A_FULL_CHORD:
        return moved
    place = moved[MIDI] % HALF_STEPS_PER_OCTAVE
    if place in held:
        return moved
    higher = (place + HALF_STEP) % HALF_STEPS_PER_OCTAVE in held
    lower = (place - HALF_STEP) % HALF_STEPS_PER_OCTAVE in held
    if higher == lower:
        return moved
    return Sound.half_step(moved, HALF_STEP if higher else -HALF_STEP)


def _place_in(*, midi, scale):
    """Return which note of a scale's octave, counted from 0, a MIDI number is at or just above, and how many half steps above it."""
    shape = scale.get_type().value
    within = (midi - scale.get_root().get_midi_number()) % HALF_STEPS_PER_OCTAVE
    place = max(index for index, step in enumerate(shape) if step <= within)
    return place, within - shape[place]
