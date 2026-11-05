# llamatron: a Python language and framework for producing MIDI clips.
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

from dataclasses import replace
from fractions import Fraction

from llamatron.chord import Chord
from llamatron.generators.base import ClipGenerator, exact_length
from llamatron.note import Rest
from llamatron.song import Clip, _Validated


def _check_rhythm(rhythm):
    if not isinstance(rhythm, Clip):
        raise ValueError(f'expected a Clip, got {rhythm!r}')


def _with_length(position, length):
    if isinstance(position, Chord):
        return Chord([replace(note, length=length) for note in position.notes])
    return replace(position, length=length)


def sound_timeline(clip):
    """Return (start, end, position) for everything in a clip that isn't a rest."""
    timeline = []
    now = Fraction(0)
    for position in clip.played_notes():
        end = now + exact_length(position.length)
        if not isinstance(position, Rest):
            timeline.append((now, end, position))
        now = end
    return timeline


def sound_at(timeline, time):
    """Return what's playing at a time, or else the last sound before it, or else the next."""
    before = [item for item in timeline if item[0] <= time]
    if before:
        return before[-1][2]
    return timeline[0][2] if timeline else None


class TakeRhythm(ClipGenerator):
    """Plays a clip's pitches with the rhythm of another clip of the same length.

    Each note in the rhythm clip plays whatever pitch this clip has at that moment. If this
    clip is silent then, it uses the last pitch before that, or else the next one. Rests in
    the rhythm clip stay as rests, and if this clip has no notes at all, it stays silent.
    """

    rhythm = _Validated(_check_rhythm)

    def __init__(self, rhythm):
        self.rhythm = rhythm

    def _generate(self, clip):
        total = clip.total_length()
        if self.rhythm.total_length() != total:
            raise ValueError(
                f'the clips must be the same length, but they last {total} and '
                f'{self.rhythm.total_length()}, so try using Stretch first'
            )
        timeline = sound_timeline(clip)
        notes = []
        now = Fraction(0)
        for position in self.rhythm.played_notes():
            length = exact_length(position.length)
            sound = None if isinstance(position, Rest) else sound_at(timeline, now)
            notes.append(Rest(length) if sound is None else _with_length(sound, length))
            now += length
        return notes, clip.length
