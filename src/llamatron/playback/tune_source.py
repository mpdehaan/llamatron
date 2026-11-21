# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""When a finished clip sounds, which a musician reads from the track that carries the tune, to play round it."""

from bisect import bisect_right

from llamatron.math import length
from llamatron.math.length import Length
from llamatron.music import sound as sound_values


class TuneSource:
    """The stretches of a finished clip in which a note sounds, each from when a note starts to when it stops."""

    __slots__ = ('_starts', '_ends')

    def __init__(self, clip):
        stretches = sorted(_stretches_of(clip))
        self._starts = [start for start, _ in stretches]
        self._ends = [end for _, end in stretches]

    def sounds_at(self, time):
        """Return whether a note of the clip sounds at a time: one has started at or before the time and has not stopped."""
        started = bisect_right(self._starts, time)
        return bool(started) and time < self._ends[started - 1]


def _stretches_of(clip):
    """Return when each note or chord of a clip starts and stops, in whole notes from the clip's start."""
    stretches = []
    start = length.ZERO
    for sound in clip.resolved_sounds():
        _place_stretch(sound=sound, start=start, stretches=stretches)
        start = Length.add(start, sound[sound_values.LENGTH])
    return stretches


def _place_stretch(*, sound, start, stretches):
    """Note the stretch a sound starting at a time sounds for, and those of a phrase's parts one after another; a held sound sounds as long as itself, past its place."""
    kind = sound[sound_values.KIND]
    if kind == sound_values.HELD:
        _place_stretch(sound=sound[sound_values.HELD_SOUND], start=start, stretches=stretches)
    elif kind == sound_values.PHRASE:
        for part in sound[sound_values.PARTS]:
            _place_stretch(sound=part, start=start, stretches=stretches)
            start = Length.add(start, part[sound_values.LENGTH])
    elif kind in (sound_values.NOTE, sound_values.CHORD, sound_values.DEGREE):
        stretches.append((Length.rational(start), Length.rational(Length.add(start, sound[sound_values.LENGTH]))))
