# noose6: a Python language and framework for producing MIDI clips.
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

import random
from bisect import bisect_left
from enum import Enum, auto
from fractions import Fraction
from math import isfinite

from src.chord import Chord
from src.generators.arp import _check_seed
from src.generators.base import ClipGenerator, exact_length
from src.generators.take_rhythm import sound_at, sound_timeline
from src.note import Degree, Note, _check_length
from src.scale import Scale
from src.song import Clip, _Validated


class BlendMode(Enum):
    """The ways that Blend can move one clip towards another."""

    SLICES = auto()
    STRONG_BEATS = auto()
    CONTOUR = auto()
    LEFT = auto()
    RIGHT = auto()
    MIDDLE = auto()


def _check_mode(mode):
    if not isinstance(mode, BlendMode):
        raise ValueError(f'expected a BlendMode, got {mode!r}')


def _check_target(target):
    if not isinstance(target, Clip):
        raise ValueError(f'expected a Clip, got {target!r}')


def _check_amount(amount):
    # bool is a subclass of int, but True is not a real amount.
    if type(amount) not in (int, float, Fraction) or not isfinite(amount) or not 0 <= amount <= 100:
        raise ValueError(f'invalid amount: {amount!r} (must be from 0 to 100)')


def _check_optional_scale(scale):
    if scale is not None and not isinstance(scale, Scale):
        raise ValueError(f'expected a Scale, got {scale!r}')


def _check_points(points):
    if points is None:
        return
    if not isinstance(points, (list, tuple)):
        raise ValueError(f'expected a list of times, got {points!r}')
    for point in points:
        if type(point) not in (int, float, Fraction) or not isfinite(point) or point < 0:
            raise ValueError(f'invalid time: {point!r} (must be 0 or more)')


def _pitch_of(position):
    """Return the pitch of a note, or the top note of a chord."""
    if isinstance(position, Chord):
        return max(note.midi_number for note in position.notes)
    return position.midi_number


def _scale_pitches(scale):
    steps = set(scale.typ.value)
    return [
        pitch for pitch in range(0, 128)
        if (pitch - scale.root.midi_number) % 12 in steps
    ]


def _concrete(clip):
    """Return a copy of a clip with degrees turned into notes of its own scale.

    Slices from two songs can't share one scale, so degrees have to be settled here.
    """
    notes = []
    for position in clip.notes:
        if isinstance(position, Degree):
            if clip.scale is None:
                raise ValueError(f'{position!r} needs a scale, but the clip has none')
            position = position.to_note(clip.scale)
        notes.append(position)
    return Clip(notes=notes, length=clip.length, note_length=clip.note_length)


class Blend(ClipGenerator):
    """Moves a clip towards a target clip of the same total length.

    An amount of 0 plays this clip. SLICES, the default, plays slices of time from one clip or
    the other, with the amount setting what share of them play the target, so 100 plays all of
    the target. Slices are slice_length long, or are cut at the given points if there are any,
    and a note that crosses a change between clips is cut.

    STRONG_BEATS keeps this clip's rhythm and the notes between beats, and gives some of the
    notes starting on a strong beat the target's pitch at that moment, so the target emerges
    beneath this clip. Strong beats are strong_beat apart, and the amount sets what share of
    them change, so 100 changes all of them but not the notes in between.

    CONTOUR keeps this clip's rhythm and moves every note part way along the scale towards the
    target's pitch at that moment, by the amount, which makes melodies belonging to neither
    clip. It uses the scale given here, or else this clip's, and 100 plays the target's pitches
    in this clip's rhythm. A chord in this clip keeps its shape and moves by its top note.

    LEFT, RIGHT and MIDDLE bring in the target from one side, from the other, or from the
    center out, with the amount setting how much of the clip's length it covers. There's no
    randomness, and the edges move to the nearest note in this clip, so its notes aren't cut.

    In SLICES and STRONG_BEATS, each slice or strong beat has a fixed threshold chosen by the
    seed, so as the amount rises, whatever has changed stays changed. Use the same seed for
    every step of a morph, and for its melody and chords, so that they change together. Use
    Stretch first if the two clips are in different meters.
    """

    target = _Validated(_check_target)
    amount = _Validated(_check_amount)
    slice_length = _Validated(_check_length)
    points = _Validated(_check_points)
    seed = _Validated(_check_seed)
    mode = _Validated(_check_mode)
    strong_beat = _Validated(_check_length)
    scale = _Validated(_check_optional_scale)

    def __init__(self, target, amount, slice_length=1, points=None, seed=0,
                 mode=BlendMode.SLICES, strong_beat=Fraction(1, 2), scale=None):
        self.target = target
        self.amount = amount
        self.slice_length = slice_length
        self.points = points
        self.seed = seed
        self.mode = mode
        self.strong_beat = strong_beat
        self.scale = scale

    def slices(self, total):
        """Return the (start, end) of each slice of a clip lasting total."""
        if self.points is None:
            size = exact_length(self.slice_length)
            times = [size * number for number in range(1, int(total // size) + 1)]
        else:
            times = [exact_length(point) for point in self.points]
        inner = sorted({time for time in times if 0 < time < total})
        edges = [Fraction(0)] + inner + [total]
        return list(zip(edges, edges[1:]))

    def takes_target(self, total):
        """Return whether each slice plays the target, in the same order as slices.

        Thresholds are evenly spaced and then shuffled. Purely random ones could bunch
        together, so that some steps of a morph would change nothing at all.
        """
        return self._chosen(len(self.slices(total)))

    def _chosen(self, count):
        thresholds = [(number + Fraction(1, 2)) / count for number in range(count)]
        random.Random(self.seed).shuffle(thresholds)
        return [self.amount / 100 > threshold for threshold in thresholds]

    def _generate(self, clip):
        total = clip.total_length()
        if self.target.total_length() != total:
            raise ValueError(
                f'the clips must be the same length, but they last {total} and '
                f'{self.target.total_length()}, so try using Stretch first'
            )

        source, target = _concrete(clip), _concrete(self.target)
        if self.mode is BlendMode.STRONG_BEATS:
            return self._strong_beats(source, target), clip.length
        if self.mode is BlendMode.CONTOUR:
            return self._contour(source, target, clip), clip.length
        if self.mode in (BlendMode.LEFT, BlendMode.RIGHT, BlendMode.MIDDLE):
            return self._sweep(source, target, total), clip.length
        return self._slices(source, target, total), clip.length

    def _sweep(self, source, target, total):
        share = total * Fraction(self.amount).limit_denominator(1_000_000) / 100
        if self.mode is BlendMode.LEFT:
            start, end = Fraction(0), share
        elif self.mode is BlendMode.RIGHT:
            start, end = total - share, total
        else:
            start, end = (total - share) / 2, (total + share) / 2
        start, end = self._nearest_edge(source, start, total), self._nearest_edge(source, end, total)
        if end <= start:
            return source.notes if share < total else target.notes
        notes = []
        if start > 0:
            notes += source.section(0, start).notes
        notes += target.section(start, end).notes
        if end < total:
            notes += source.section(end, total).notes
        return notes

    def _nearest_edge(self, source, time, total):
        """Return the start of the note in the source closest to a time."""
        edges = [Fraction(0), total]
        now = Fraction(0)
        for position in source.played_notes():
            edges.append(now)
            now += exact_length(position.length)
        return min(edges, key=lambda edge: (abs(edge - time), edge))

    def _slices(self, source, target, total):
        notes = []
        run_start = Fraction(0)
        slices = self.slices(total)
        owners = self.takes_target(total)
        for index, (_, end) in enumerate(slices):
            # Neighboring slices from one clip are taken together, so notes aren't cut between them.
            if index + 1 == len(slices) or owners[index + 1] != owners[index]:
                if total > 0:
                    owner = target if owners[index] else source
                    notes += owner.section(run_start, end).notes
                run_start = end
        return notes

    def _strong_beats(self, source, target):
        strong = exact_length(self.strong_beat)
        timeline = sound_timeline(target)
        positions = source.played_notes()

        starts = []
        now = Fraction(0)
        for position in positions:
            starts.append(now)
            now += exact_length(position.length)
        strong_places = [
            place for place, (position, start) in enumerate(zip(positions, starts))
            if start % strong == 0 and isinstance(position, (Note, Chord))
        ]
        changing = {
            place for place, chosen in zip(strong_places, self._chosen(len(strong_places))) if chosen
        }

        notes = []
        for place, (position, start) in enumerate(zip(positions, starts)):
            sound = sound_at(timeline, start) if place in changing else None
            notes.append(position if sound is None else self._with_pitch(position, _pitch_of(sound)))
        return notes

    def _contour(self, source, target, clip):
        scale = clip.scale if self.scale is None else self.scale
        if scale is None:
            raise ValueError('moving by contour needs a scale, but none was found')
        pitches = _scale_pitches(scale)
        timeline = sound_timeline(target)

        notes = []
        now = Fraction(0)
        for position in source.played_notes():
            sound = sound_at(timeline, now) if isinstance(position, (Note, Chord)) else None
            if sound is not None and self.amount > 0:
                moved = self._along_scale(_pitch_of(position), _pitch_of(sound), pitches)
                position = self._with_pitch(position, moved)
            notes.append(position)
            now += exact_length(position.length)
        return notes

    def _along_scale(self, pitch, goal, pitches):
        """Return the pitch that lies the amount of the way to a goal, in steps of the scale."""
        start_place = self._nearest_place(pitch, pitches)
        goal_place = self._nearest_place(goal, pitches)
        return pitches[start_place + round((goal_place - start_place) * Fraction(self.amount) / 100)]

    def _nearest_place(self, pitch, pitches):
        place = bisect_left(pitches, pitch)
        if place == 0:
            return 0
        if place == len(pitches):
            return len(pitches) - 1
        return place if pitches[place] - pitch < pitch - pitches[place - 1] else place - 1

    def _with_pitch(self, position, pitch):
        """Return a note or chord moved so that its top note is at a pitch, keeping its length."""
        if isinstance(position, Chord):
            difference = pitch - _pitch_of(position)
            return Chord([
                Note.from_midi_number(note.midi_number + difference, note.length)
                for note in position.notes
            ])
        return Note.from_midi_number(pitch, position.length)
