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

"""What a track has played, for another track's grab steps to take notes from."""

from bisect import bisect_right

from llamatron.exporters.timing import as_note, clip_end
from llamatron.music.sound import CHORD, HELD, HELD_SOUND, KIND, LENGTH, MIDI, NOTES, PARTS, PHRASE, REST
from llamatron.support.length import ZERO, Length


class GrabSource:
    """The notes a finished clip starts, by when they start, like the Cirklon's note grab."""

    __slots__ = ('_onsets', '_times')

    def __init__(self, clip):
        self._onsets = _notes_by_start(clip)
        self._times = sorted(self._onsets)

    def note_at(self, time):
        """Return the MIDI number of the note most recently started at or before a time, or None.

        A chord gives its root, the note it was built on, which is its first note however it's
        inverted or voiced (the user's rule of 2026-11-11), where it gave its lowest until
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
    start = ZERO
    for sound in sounds:
        _place_root(sound=sound, start=start, end=end, scale=clip.get_scale(), roots=roots)
        start = Length.add(start, sound[LENGTH])
    return roots


def _place_root(*, sound, start, end, scale, roots):
    """Note the root a sound starting at a time gives, and those a held phrase's parts give one after another, keeping the first at each time."""
    kind = sound[KIND]
    if kind == HELD:
        _place_root(sound=sound[HELD_SOUND], start=start, end=end, scale=scale, roots=roots)
    elif kind == PHRASE:
        for part in sound[PARTS]:
            _place_root(sound=part, start=start, end=end, scale=scale, roots=roots)
            start = Length.add(start, part[LENGTH])
    elif kind != REST:
        time = Length.rational(start)
        if time < end:
            roots.setdefault(time, _root(sound=sound, scale=scale))


def _root(*, sound, scale):
    """Return the MIDI number of a note, or of a chord's root, its first note as built."""
    if sound[KIND] == CHORD:
        return _root(sound=sound[NOTES][0], scale=scale)
    return as_note(position=sound, scale=scale)[MIDI]
