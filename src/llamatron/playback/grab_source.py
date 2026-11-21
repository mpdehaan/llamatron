# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What a track has played, for another track's grab steps to take notes from."""

from bisect import bisect_right

from llamatron.exporters.timing import as_note, clip_end
from llamatron.math import length
from llamatron.math.length import Length
from llamatron.model.values import sound as sound_values


class GrabSource:
    """The notes a finished clip starts, by when they start, like a step sequencer's note grab."""

    __slots__ = ('_onsets', '_times')

    def __init__(self, clip):
        self._onsets = _notes_by_start(clip)
        self._times = sorted(self._onsets)

    def note_at(self, time):
        """Return the MIDI number of the note most recently started at or before a time, or None.

        A chord gives its root, the note it was built on, which is its first note however it's
        inverted or voiced, where it gave its lowest until
        inversions came. Two sounds starting together give the first one's.
        """
        latest = self._latest_start_by(time)
        return None if latest is None else self._onsets[latest]

    def _latest_start_by(self, time):
        """Return the latest time a note starts at or before a time, or None if none has started."""
        started = bisect_right(self._times, time)
        return self._times[started - 1] if started else None


def _notes_by_start(clip):
    """Return the MIDI number each note or chord a clip plays gives a grab, its root for a chord, by when it starts, up to the clip's end.

    It reads the clip's sounds rather than its timed notes, where a chord would be only the
    pitches that start together and its root lost. Grooves and strums only move timing, so a grab
    reads the notes where the grid puts them.
    """
    sounds = clip.resolved_sounds()
    end = clip_end(clip=clip, positions=sounds)
    roots = {}
    start = length.ZERO
    for sound in sounds:
        _place_root(sound=sound, start=start, end=end, scale=clip.get_scale(), roots=roots)
        start = Length.add(start, sound[sound_values.LENGTH])
    return roots


def _place_root(*, sound, start, end, scale, roots):
    """Note the root a sound starting at a time gives, and those a held phrase's parts give one after another, keeping the first at each time."""
    kind = sound[sound_values.KIND]
    if kind == sound_values.HELD:
        _place_root(sound=sound[sound_values.HELD_SOUND], start=start, end=end, scale=scale, roots=roots)
    elif kind == sound_values.PHRASE:
        for part in sound[sound_values.PARTS]:
            _place_root(sound=part, start=start, end=end, scale=scale, roots=roots)
            start = Length.add(start, part[sound_values.LENGTH])
    elif kind != sound_values.REST:
        time = Length.rational(start)
        if time < end:
            roots.setdefault(time, _root(sound=sound, scale=scale))


def _root(*, sound, scale):
    """Return the MIDI number of a note, or of a chord's root, its first note as built."""
    if sound[sound_values.KIND] == sound_values.CHORD:
        return _root(sound=sound[sound_values.NOTES][0], scale=scale)
    return as_note(position=sound, scale=scale)[sound_values.MIDI]
