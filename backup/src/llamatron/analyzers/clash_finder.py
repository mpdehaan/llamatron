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

from collections import namedtuple

from llamatron.note import _check_length
from llamatron.renderers.timing import timed_notes
from llamatron.song import Clip, _Validated, exact_length

Clash = namedtuple('Clash', ['time', 'melody_pitch', 'chord_pitch'])


class ClashFinder:
    """Finds melody notes that fight the chord playing under them.

    A clash is a melody note a half step from a chord note, unless it's also in the chord. It
    only counts if the note starts on a beat or lasts at least a beat. A note up to a beat long
    that steps to and from its neighbors is a passing note, so it never counts. This is a rule
    of thumb, so your ears get the final say.
    """

    beat = _Validated(_check_length)

    def __init__(self, beat=0.25):
        self.beat = beat

    def analyze(self, melody, chords):
        """Return a Clash for every clash, in time order."""
        for clip in (melody, chords):
            if not isinstance(clip, Clip):
                raise ValueError(f'expected a Clip, got {clip!r}')
        beat = exact_length(self.beat)
        chord_notes, _ = timed_notes(chords, chords.scale)
        melody_notes, _ = timed_notes(melody, melody.scale)

        clashes = []
        ordered = sorted(melody_notes)
        for index, (start, end, pitch) in enumerate(ordered):
            start, end = exact_length(start), exact_length(end)
            if start % beat != 0 and end - start < beat:
                continue
            if end - start <= beat and self._moves_by_step(ordered, index):
                continue
            sounding = [
                chord_pitch for chord_start, chord_end, chord_pitch in chord_notes
                if chord_start < end and start < chord_end
            ]
            pitch_classes = {chord_pitch % 12 for chord_pitch in sounding}
            for chord_pitch in sorted(sounding):
                if pitch % 12 not in pitch_classes and (pitch - chord_pitch) % 12 in (1, 11):
                    clashes.append(Clash(start, pitch, chord_pitch))
        return clashes

    def _moves_by_step(self, notes, index):
        """Return whether a note is a step from both the note before it and the note after it."""
        if index == 0 or index == len(notes) - 1:
            return False
        pitch = notes[index][2]
        return (1 <= abs(pitch - notes[index - 1][2]) <= 2
                and 1 <= abs(notes[index + 1][2] - pitch) <= 2)
