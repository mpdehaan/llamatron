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

from dataclasses import replace
from fractions import Fraction

from src.analyzers.clash_finder import ClashFinder
from src.chord import Chord
from src.legacy.generators.accompany import Accompany
from src.generators.base import ClipGenerator, exact_length
from src.legacy.generators.transpose import _check_scale
from src.note import Rest
from src.song import Clip, _Validated


def _check_charts(charts):
    if not isinstance(charts, (list, tuple)) or not charts:
        raise ValueError(f'expected a list of chord charts, got {charts!r}')
    for chart in charts:
        if not isinstance(chart, Clip):
            raise ValueError(f'expected a Clip, got {chart!r}')


class Harmonize(ClipGenerator):
    """Plays a song's real chords under a melody, unless they would clash with it.

    Each chart is a clip of chords lasting as long as the melody, in order of preference.
    Each chord in the first chart sets one slot. For each slot, this plays the first chart's
    chord that doesn't clash with the melody, according to ClashFinder. If they all clash,
    it plays the best-fitting chord in the scale that doesn't clash and shares a note with
    the chord before it, so that the harmony connects. It uses the scale given here or else
    the melody clip's. If every chord clashes, it plays the best fit anyway. The result is a
    clip of chords that doesn't change the melody.
    """

    charts = _Validated(_check_charts)
    scale = _Validated(_check_scale)

    def __init__(self, charts, scale=None):
        self.charts = charts
        self.scale = scale

    def _generate(self, clip):
        total = clip.total_length()
        for chart in self.charts:
            if chart.total_length() != total:
                raise ValueError(
                    f'every chart must last as long as the melody, which lasts {total}, '
                    f'but one lasts {chart.total_length()}'
                )

        notes = []
        start = Fraction(0)
        for position in self.charts[0].played_notes():
            end = start + exact_length(position.length)
            previous = notes[-1] if notes else None
            notes.append(self._chord_for_slot(clip, start, end, previous))
            start = end
        return notes, clip.length

    def _chord_for_slot(self, clip, start, end, previous):
        for chart in self.charts:
            chord = self._first_chord(chart.section(start, end))
            if chord is not None and not self._clashes(clip, chord, start, end):
                return chord
        scale = clip.scale if self.scale is None else self.scale
        section = clip.section(start, end)
        choices = Accompany(scale=scale, measure_length=end - start).ranked_chords(section)
        fitting = [chord for chord in choices if not self._clashes(clip, chord, start, end)]
        for chord in fitting:
            if self._connects(chord, previous):
                return chord
        return fitting[0] if fitting else choices[0]

    def _connects(self, chord, previous):
        if previous is None:
            return True
        pitches = {note.midi_number % 12 for note in previous.notes}
        return any(note.midi_number % 12 in pitches for note in chord.notes)

    def _first_chord(self, section):
        for position in section.notes:
            if not isinstance(position, Rest):
                return position
        return None

    def _clashes(self, melody, chord, start, end):
        """Check the whole melody, because a note that started earlier can ring into this slot."""
        notes = chord.notes if isinstance(chord, Chord) else [chord]
        cut = Chord([replace(note, length=end - start) for note in notes])
        chords = Clip(notes=[Rest(start), cut] if start else [cut])
        return ClashFinder().analyze(melody, chords)
