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

from llamatron.analyzers.clash_finder import ClashFinder
from llamatron.generators.base import ClipGenerator, exact_length
from llamatron.note import Note, Rest
from llamatron.renderers.timing import timed_notes
from llamatron.song import Clip, _Validated

MAX_MOVE = 7


def _check_chords(chords):
    if not isinstance(chords, Clip):
        raise ValueError(f'expected a Clip, got {chords!r}')


def _check_max_leap(max_leap):
    # bool is a subclass of int, but True is not a real number of half steps.
    if type(max_leap) is not int or max_leap < 1:
        raise ValueError(f'invalid max_leap: {max_leap!r} (must be a positive integer)')


class Smoother(ClipGenerator):
    """Makes small repairs to a melody, so that it fits its chords and doesn't jump around.

    A note that clashes with the chords moves to the closest note of the chord under it, if
    one fits. Then a note more than max_leap half steps from the note before it moves by an
    octave, if that brings it closer, which keeps the same note name. A move can't take a
    note outside the melody's original range, so it can't wander into other parts. Everything
    else stays exactly as it was. Chords and degrees in the melody are left alone.
    """

    chords = _Validated(_check_chords)
    max_leap = _Validated(_check_max_leap)

    def __init__(self, chords, max_leap=7):
        self.chords = chords
        self.max_leap = max_leap

    def _generate(self, clip):
        chord_notes, _ = timed_notes(self.chords, self.chords.scale)
        flagged = {
            (clash.time, clash.melody_pitch) for clash in ClashFinder().analyze(clip, self.chords)
        }
        pitches = [position.midi_number for position in clip.played_notes() if isinstance(position, Note)]
        lowest, highest = (min(pitches), max(pitches)) if pitches else (0, 127)
        notes = []
        now = Fraction(0)
        previous = None
        for position in clip.played_notes():
            length = exact_length(position.length)
            if isinstance(position, Note):
                pitch = position.midi_number
                if (now, pitch) in flagged:
                    pitch = self._fix_clash(position, now, chord_notes)
                pitch = self._close_leap(pitch, previous, lowest, highest)
                previous = pitch
                if pitch != position.midi_number:
                    position = Note.from_midi_number(pitch, position.length)
            elif not isinstance(position, Rest):
                previous = None
            notes.append(position)
            now += length
        return notes, clip.length

    def _clashes(self, pitch, length, start):
        note = Note.from_midi_number(pitch, length)
        melody = Clip(notes=[Rest(start), note] if start else [note])
        return ClashFinder().analyze(melody, self.chords)

    def _fix_clash(self, note, start, chord_notes):
        length = exact_length(note.length)
        pitch = note.midi_number
        sounding = {
            chord_pitch % 12 for chord_start, chord_end, chord_pitch in chord_notes
            if chord_start <= start < chord_end
        }
        for distance in range(1, MAX_MOVE + 1):
            for candidate in (pitch - distance, pitch + distance):
                if (0 <= candidate <= 127 and candidate % 12 in sounding
                        and not self._clashes(candidate, length, start)):
                    return candidate
        return pitch

    def _close_leap(self, pitch, previous, lowest, highest):
        if previous is None or abs(pitch - previous) <= self.max_leap:
            return pitch
        moved = [candidate for candidate in (pitch - 12, pitch + 12) if lowest <= candidate <= highest]
        return min([pitch] + moved, key=lambda candidate: abs(candidate - previous))
