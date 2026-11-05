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

from fractions import Fraction

from src.chord import Chord
from src.generators.base import ClipGenerator, exact_length, fit_to_length
from src.legacy.generators.transpose import _check_scale
from src.note import Degree, Note, Rest, _check_integer, _check_length
from src.song import _Validated

# Chords on these scale positions win ties, because they're the most common in a song.
_FAVORITE_POSITIONS = [0, 4, 3]


def _notes_in(position):
    if isinstance(position, Chord):
        return position.notes
    return [] if isinstance(position, Rest) else [position]


class Accompany(ClipGenerator):
    """Turns a melody into chords, choosing one chord from the scale for each measure.

    For each measure, this adds up how long each melody note sounds, and picks the
    three-note chord built from the scale whose notes sound the longest. Ties go to the
    chord on the first, fifth or fourth note of the scale, in that order, or else the
    lowest. A measure with no notes repeats the chord before it. This uses the scale given
    here, or else the clip's. Chords hold notes rather than degrees, so they're fixed in
    that scale. The octave is relative to the root of the scale, and measure_length is a
    fraction of a whole note, so the default of 1 is four quarter notes.
    """

    scale = _Validated(_check_scale)
    measure_length = _Validated(_check_length)
    octave = _Validated(_check_integer)

    def __init__(self, scale=None, measure_length=1, octave=-1):
        self.scale = scale
        self.measure_length = measure_length
        self.octave = octave

    def _generate(self, clip):
        scale = clip.scale if self.scale is None else self.scale
        if scale is None:
            raise ValueError('choosing chords needs a scale, but none was found')

        positions = clip.resolved_notes()
        if clip.length is not None:
            positions = fit_to_length(positions, clip.length)
        total = sum((exact_length(position.length) for position in positions), Fraction(0))
        measure = exact_length(self.measure_length)

        chords = self._chords(scale, measure)
        sounding = self._sounding_times(positions, scale, measure)
        result = []
        previous = chords[0]
        number = 0
        while number * measure < total:
            times = sounding.get(number)
            chord = self._best_chord(chords, times) if times else previous
            result.append(chord)
            previous = chord
            number += 1
        return fit_to_length(result, total) if result else [], clip.length

    def ranked_chords(self, clip):
        """Return every chord in the scale for a one-measure clip, best fit first."""
        scale = clip.scale if self.scale is None else self.scale
        if scale is None:
            raise ValueError('choosing chords needs a scale, but none was found')
        measure = exact_length(self.measure_length)
        times = self._sounding_times(clip.played_notes(), scale, measure).get(0, {})
        return sorted(self._chords(scale, measure), key=self._score(times), reverse=True)

    def _chords(self, scale, length):
        """Return the three-note chord built on each note of the scale, favorites first."""
        size = len(scale.typ.value)
        places = [place for place in _FAVORITE_POSITIONS if place < size]
        places += [place for place in range(size) if place not in places]
        return [
            Chord([
                Degree(place + step + 1, length, octave=self.octave).to_note(scale)
                for step in (0, 2, 4)
            ])
            for place in places
        ]

    def _sounding_times(self, positions, scale, measure):
        """Return {measure number: {pitch class: how long it sounds in that measure}}."""
        times = {}
        start = Fraction(0)
        for position in positions:
            for item in _notes_in(position):
                note = item.to_note(scale) if isinstance(item, Degree) else item
                self._add_note(times, note, start, measure)
            start += exact_length(position.length)
        return times

    def _add_note(self, times, note, start, measure):
        end = start + exact_length(note.length)
        number = start // measure
        while number * measure < end:
            overlap = min(end, (number + 1) * measure) - max(start, number * measure)
            pitches = times.setdefault(number, {})
            pitch_class = note.midi_number % 12
            pitches[pitch_class] = pitches.get(pitch_class, Fraction(0)) + overlap
            number += 1

    def _best_chord(self, chords, times):
        """Return the chord whose notes sound the longest, with the earliest chord winning ties."""
        return max(chords, key=self._score(times))

    def _score(self, times):
        def score(chord):
            pitch_classes = {note.midi_number % 12 for note in chord.notes}
            return sum(time for pitch, time in times.items() if pitch in pitch_classes)
        return score
