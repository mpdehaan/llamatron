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

"""The chords a finished clip plays, by when each starts, which a Follow Chords reads from the track it follows."""

from bisect import bisect_right

from llamatron.exporters.timing import as_note, clip_end
from llamatron.music.sound import CHORD, HELD, HELD_SOUND, KIND, LENGTH, MIDI, NOTES, PARTS, PHRASE, REST
from llamatron.support.length import ZERO, Length

HALF_STEPS_PER_OCTAVE = 12


class ChordSource:
    """The chords a finished clip starts, by when they start: each its root and its notes within an octave."""

    __slots__ = ('_chords', '_times')

    def __init__(self, clip):
        self._chords = _chords_by_start(clip)
        self._times = sorted(self._chords)

    def chord_at(self, time):
        """Return the chord most recently started at or before a time, as its root's MIDI number and the set of its notes within an octave, or None before the first.

        A chord's root is the note it was built on, its first however it is inverted or voiced, and
        a single note is a chord of itself. A chord goes on through the rests after it.
        """
        started = bisect_right(self._times, time)
        return self._chords[self._times[started - 1]] if started else None


def _chords_by_start(clip):
    """Return the chord each note or chord of a clip gives, by when it starts, up to the clip's end, the first at each time kept."""
    sounds = clip.resolved_sounds()
    end = clip_end(clip=clip, positions=sounds)
    chords = {}
    start = ZERO
    for sound in sounds:
        _place_chord(sound=sound, start=start, end=end, scale=clip.get_scale(), chords=chords)
        start = Length.add(start, sound[LENGTH])
    return chords


def _place_chord(*, sound, start, end, scale, chords):
    """Note the chord a sound starting at a time gives, and those a held phrase's parts give one after another."""
    kind = sound[KIND]
    if kind == HELD:
        _place_chord(sound=sound[HELD_SOUND], start=start, end=end, scale=scale, chords=chords)
    elif kind == PHRASE:
        for part in sound[PARTS]:
            _place_chord(sound=part, start=start, end=end, scale=scale, chords=chords)
            start = Length.add(start, part[LENGTH])
    elif kind != REST:
        time = Length.rational(start)
        if time < end:
            chords.setdefault(time, _chord_of(sound=sound, scale=scale))


def _chord_of(*, sound, scale):
    """Return a note's or a chord's root as a MIDI number, and its notes within an octave."""
    notes = sound[NOTES] if sound[KIND] == CHORD else [sound]
    numbers = [as_note(position=note, scale=scale)[MIDI] for note in notes]
    return numbers[0], frozenset(number % HALF_STEPS_PER_OCTAVE for number in numbers)
