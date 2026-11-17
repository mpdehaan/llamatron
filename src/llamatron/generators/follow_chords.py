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
    """Return a note moved to a chord, given as its root's MIDI number and its notes within an octave, or as it was where moving it would leave the MIDI range.

    A root on a note of the scale moves the note along the scale. A root between two notes of
    the scale moves it by the exact half steps from the scale's root to the chord's, keeping
    the figure's own sound, as a Progression moves a figure to a degree with a sharp or a flat.
    """
    root, held = chord
    steps, extra = _place_in(midi=root, scale=scale)
    try:
        if extra:
            moved = Sound.half_step(note, (root - scale.get_root().get_midi_number()) % HALF_STEPS_PER_OCTAVE)
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
    above, extra = _place_in(midi=note[MIDI], scale=scale)
    if extra or above not in KINDS_OF_CHORD_NOTE or len(scale.get_type().value) != PLACED_SCALE_SIZE:
        return moved
    kind = KINDS_OF_CHORD_NOTE[above]
    own = (moved[MIDI] - root) % HALF_STEPS_PER_OCTAVE
    has = [interval for interval in kind if (root + interval) % HALF_STEPS_PER_OCTAVE in held]
    if own not in kind or own in has or len(has) != 1:
        return moved
    return Sound.half_step(moved, has[0] - own)


def _place_in(*, midi, scale):
    """Return which note of a scale's octave, counted from 0, a MIDI number is at or just above, and how many half steps above it."""
    shape = scale.get_type().value
    within = (midi - scale.get_root().get_midi_number()) % HALF_STEPS_PER_OCTAVE
    place = max(index for index, step in enumerate(shape) if step <= within)
    return place, within - shape[place]
