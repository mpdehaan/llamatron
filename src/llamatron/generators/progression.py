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
"""The Progression generator: a clip's notes moved along the scale to each chord of a progression in turn, the user's design of 2026-11-11.

The clip's pattern is taken as written over chord I. Each chord lasts every (a bar by default),
counted from the clip's start, and the progression loops for as long as the clip plays. A plain
degree moves every note that many scale steps up, less one, so the scale decides whether the
chord is major or minor; a degree with a sharp or a flat moves every note by exact half steps,
the half steps from the root to that scale degree and one more or less, keeping the figure's own
sound, so bVII from a C major figure is B flat major. A chord's inversion moves its lowest one or
two notes up an octave. Rests, rhythm, velocity and gates stay as written.

A chord may also leave the clip's scale three ways (the user's design, composition/chords.py). Its scale, a scale type on the
clip's root, takes the clip's scale's place while the chord plays, each note of the figure carried to the same place in it, so
a chord is borrowed from the parallel minor with its passing notes. Its quality, a named chord symbol, sets the figure's notes
that are the chord's third, fifth and seventh. Its tensions set the notes between, and are added on top of a chord of the figure.
"""

import math

from llamatron.composition.chords import PLACED_SCALE_SIZE, ROOT_PLACE, replaced_places
from llamatron.composition.file_format import ACCIDENTALS, TENSIONS
from llamatron.composition.named_scale import scale_type_called
from llamatron.generators.arp import along_scale
from llamatron.generators.base import ClipGenerator
from llamatron.music.scale import Scale, ScaleType
from llamatron.music.sound import CHORD, DEGREE, HELD, HELD_SOUND, KIND, LENGTH, MIDI, NOTE, NOTES, PARTS, PHRASE, Sound
from llamatron.support.length import ZERO, Length

HALF_STEPS_PER_OCTAVE = 12
ZERO_OFFSET = 0
# The scale whose half steps place a degree with a sharp or flat when a clip has no scale.
SHAPE_WITHOUT_A_SCALE = ScaleType.MAJOR.value


class Progression(ClipGenerator):
    """Moves a clip's notes to each chord of a progression in turn."""

    __slots__ = ('_chords', '_accidentals', '_inversions', '_scales', '_tensions', '_replaced', '_plain', '_every', '_offset', '_borrowed')

    def __init__(self, *, chords, every, accidentals=None, inversions=None, scales=None, qualities=None, tensions=None, continuation=None):
        self._chords = list(chords)
        nothing = [None] * len(self._chords)
        self._accidentals = list(accidentals or nothing)
        self._inversions = list(inversions or nothing)
        self._scales = [None if kind is None else scale_type_called(kind) for kind in scales or nothing]
        self._tensions = list(tensions or nothing)
        # For each chord, the half steps its quality and tensions give the figure's notes, by their place above the chord's root.
        self._replaced = [replaced_places(symbol=symbol, tensions=added) for symbol, added in zip(qualities or nothing, self._tensions)]
        # A progression none of whose chords leaves the clip's scale moves its notes the short way.
        self._plain = not any(self._scales) and not any(self._replaced)
        # The scales chords borrow, each built once for the clip's scale it was asked under.
        self._borrowed = {}
        self._every = every
        # How far into its run the clip starts, which a Restart that doesn't start over with the clip sets.
        self._offset = ZERO_OFFSET if continuation is None else continuation.offset

    def chord_at(self, time):
        """Return which chord of the progression plays at a time from the clip's start, counted from 0."""
        return math.floor((time + self._offset) / self._every) % len(self._chords)

    def _generate(self, clip):
        scale = clip.get_scale()
        result = []
        now = ZERO
        for sound in clip.resolved_sounds():
            place = self.chord_at(Length.rational(now))
            result.append(self._moved(sound=sound, place=place, scale=scale))
            now = Length.add(now, sound[LENGTH])
        return result, clip.get_length()

    def _moved(self, *, sound, place, scale):
        """Return a sound moved to one chord of the progression."""
        kind = sound[KIND]
        if kind == DEGREE and scale is not None:
            return self._moved(sound=Sound.settled(sound, scale), place=place, scale=scale)
        if kind == NOTE:
            return self._moved_note(note=sound, place=place, scale=scale)
        if kind == CHORD:
            notes = [self._moved_note(note=note, place=place, scale=scale) for note in sound[NOTES]]
            if self._tensions[place]:
                notes = _with_tensions(notes=notes, tensions=self._tensions[place])
            return Sound.inverted(Sound.chord(notes), self._inversions[place])
        if kind == HELD:
            return (HELD, sound[LENGTH], self._moved(sound=sound[HELD_SOUND], place=place, scale=scale))
        if kind == PHRASE:
            return (PHRASE, sound[LENGTH], tuple(self._moved(sound=part, place=place, scale=scale) for part in sound[PARTS]))
        return sound

    def _moved_note(self, *, note, place, scale):
        """Return a note moved to a chord: along the scale for a plain degree, by exact half steps for one with a sharp or flat, and as it was where moving it would leave the MIDI range."""
        try:
            if self._plain or scale is None:
                return self._to_chord(note=note, place=place, scale=scale)
            return self._to_changed_chord(note=note, place=place, scale=scale)
        except ValueError:
            return note

    def _to_chord(self, *, note, place, scale):
        """Return a note moved to a chord's degree in a scale."""
        accidental = self._accidentals[place]
        if accidental is None:
            return along_scale(note=note, steps=self._chords[place] - 1, scale=scale)
        return Sound.half_step(note, _half_steps_to(degree=self._chords[place], scale=scale) + ACCIDENTALS[accidental])

    def _to_changed_chord(self, *, note, place, scale):
        """Return a note moved to a chord that borrows a scale, or names its quality or tensions.

        The note is first carried to the same place in the chord's scale. Where it is a note of that scale, and the chord
        names the note at its place above the root, it becomes the chord's root, moved, and that many half steps.
        """
        kind = self._scales[place]
        drawn_from = scale if kind is None else self._scale_borrowed(scale=scale, kind=kind)
        above, extra = _place_in(note=note, scale=scale)
        if drawn_from is not scale:
            note = _carried(note=note, scale=scale, drawn_from=drawn_from)
        replaced = self._replaced[place]
        size = len(drawn_from.get_type().value)
        if extra or size != PLACED_SCALE_SIZE or above not in replaced or above == ROOT_PLACE:
            return self._to_chord(note=note, place=place, scale=drawn_from)
        root = self._to_chord(note=along_scale(note=note, steps=-above, scale=drawn_from), place=place, scale=drawn_from)
        return Sound.half_step(root, replaced[above])

    def _scale_borrowed(self, *, scale, kind):
        key = (scale.get_root().get_midi_number(), kind)
        if key not in self._borrowed:
            self._borrowed[key] = Scale(root=scale.get_root(), typ=kind)
        return self._borrowed[key]


def _place_in(*, note, scale):
    """Return which note of a scale's octave, counted from 0, a note is at or just above, and how many half steps above it."""
    shape = scale.get_type().value
    within = (note[MIDI] - scale.get_root().get_midi_number()) % HALF_STEPS_PER_OCTAVE
    place = max(index for index, step in enumerate(shape) if step <= within)
    return place, within - shape[place]


def _carried(*, note, scale, drawn_from):
    """Return a note of one scale as the note at the same place of another on the same root, keeping its distance above a scale note."""
    place, _ = _place_in(note=note, scale=scale)
    shape = scale.get_type().value
    other = drawn_from.get_type().value
    return Sound.half_step(note, other[place % len(other)] - shape[place])


def _with_tensions(*, notes, tensions):
    """Return a chord's notes with its tensions added above its lowest note, each left out where a note of the chord already has its pitch or it would leave the MIDI range."""
    lowest = min(notes, key=lambda note: note[MIDI])
    held = {note[MIDI] % HALF_STEPS_PER_OCTAVE for note in notes}
    result = list(notes)
    for tension in tensions:
        if (lowest[MIDI] + TENSIONS[tension]) % HALF_STEPS_PER_OCTAVE in held:
            continue
        try:
            result.append(Sound.half_step(lowest, TENSIONS[tension]))
        except ValueError:
            pass
    return result


def _half_steps_to(*, degree, scale):
    """Return how many half steps a degree of a scale is above its root, the major scale's when there's no scale."""
    shape = SHAPE_WITHOUT_A_SCALE if scale is None else scale.get_type().value
    octaves, place = divmod(degree - 1, len(shape))
    return octaves * HALF_STEPS_PER_OCTAVE + shape[place]

