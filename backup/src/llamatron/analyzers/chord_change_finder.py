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

from fractions import Fraction

from llamatron.chord import Chord
from llamatron.note import Note, Rest
from llamatron.song import Clip, exact_length


def _pitch_classes(position):
    notes = position.notes if isinstance(position, Chord) else [position]
    return frozenset(note.midi_number % 12 for note in notes if isinstance(note, Note))


class ChordChangeFinder:
    """Finds when the harmony changes in a clip of chords, ignoring octaves and rests.

    Returns the times of each change, in fractions of a whole note.
    """

    def analyze(self, clip):
        if not isinstance(clip, Clip):
            raise ValueError(f'expected a Clip, got {clip!r}')
        times = []
        previous = None
        now = Fraction(0)
        for position in clip.played_notes():
            if not isinstance(position, Rest):
                current = _pitch_classes(position)
                if previous is not None and current != previous:
                    times.append(now)
                previous = current
            now += exact_length(position.length)
        return times
