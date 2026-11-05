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

import random
from collections import namedtuple
from enum import Enum, auto
from fractions import Fraction

from src.generators.arp import _check_seed
from src.generators.base import ClipGenerator, exact_length
from src.legacy.generators.force_scale import _check_required_scale as _check_a_scale
from src.note import Note, Rest, _check_length
from src.renderers.timing import timed_notes
from src.song import Clip, _Validated

BEAT = Fraction(1, 4)
BEAM_WIDTH = 40

# Intervals, in half steps above the lower note, that sound stable on a strong beat.
CONSONANT = {0, 3, 4, 7, 8, 9}
PERFECT = {0, 7}
THIRDS_AND_SIXTHS = {3, 4, 8, 9}
FORBIDDEN = 1000


class CounterpointStyle(Enum):
    """The kinds of second line that Counterpoint can write."""

    NOTE_AGAINST_NOTE = auto()
    FLOWING = auto()
    CANON = auto()


Slot = namedtuple('Slot', ['start', 'end', 'melody', 'strong', 'options'])


def _check_chords(chords):
    if not isinstance(chords, Clip):
        raise ValueError(f'expected a Clip, got {chords!r}')


def _check_style(style):
    if not isinstance(style, CounterpointStyle):
        raise ValueError(f'expected a CounterpointStyle, got {style!r}')


def _check_note(note):
    if not isinstance(note, Note):
        raise ValueError(f'expected a Note, got {note!r}')


def _check_optional_scale(scale):
    if scale is not None:
        _check_a_scale(scale)


class Counterpoint(ClipGenerator):
    """Writes a second line to go below a melody and fit its chords.

    NOTE_AGAINST_NOTE plays one note for each melody note. FLOWING plays a steady stream of
    notes, each step long, with passing notes between chord notes. CANON plays the melody
    itself, delay later and moved down by octaves, changing only notes that would clash.

    The first two choose each note by trying many lines at once and keeping the best. Strong
    notes are consonant with the melody and use the chord when they can, and a line avoids
    parallel fifths and octaves and prefers small steps moving against the melody. A note is strong if it
    starts on a beat or lasts at least a beat. The line stays from low to high and never
    goes above the melody. This uses the scale given here, or else the clip's. This aims for
    correct counterpoint in the spirit of Bach, not for Bach's sense of where a line is going.
    """

    chords = _Validated(_check_chords)
    style = _Validated(_check_style)
    low = _Validated(_check_note)
    high = _Validated(_check_note)
    step = _Validated(_check_length)
    delay = _Validated(_check_length)
    scale = _Validated(_check_optional_scale)
    seed = _Validated(_check_seed)

    def __init__(self, chords, style=CounterpointStyle.NOTE_AGAINST_NOTE, low=Note('C', 2),
                 high=Note('C', 3), step=Fraction(1, 8), delay=1, scale=None, seed=0):
        self.chords = chords
        self.style = style
        self.low = low
        self.high = high
        self.step = step
        self.delay = delay
        self.scale = scale
        self.seed = seed

    def _generate(self, clip):
        if self.low.midi_number >= self.high.midi_number:
            raise ValueError(f'low must be below high, but got {self.low!r} and {self.high!r}')
        scale = clip.scale if self.scale is None else self.scale
        if scale is None:
            raise ValueError('writing counterpoint needs a scale, but none was found')
        total = clip.total_length()
        melody, _ = timed_notes(clip, scale)
        chords, _ = timed_notes(self.chords, self.chords.scale)
        if self.style is CounterpointStyle.CANON:
            notes = self._canon(melody, chords, total, scale)
        else:
            notes = self._search(self._slots(melody, chords, total, scale), chords, scale)
        return self._as_positions(notes, total, scale), clip.length

    # Choosing where the notes go.

    def _slots(self, melody, chords, total, scale):
        highest = {}
        for start, end, pitch in melody:
            if start not in highest or pitch > highest[start][1]:
                highest[start] = (end, pitch)
        if self.style is CounterpointStyle.NOTE_AGAINST_NOTE:
            times = [(start, min(end, total)) for start, (end, _) in sorted(highest.items())]
        else:
            step = exact_length(self.step)
            count = int(total // step)
            times = [(step * number, step * (number + 1)) for number in range(count)]

        return [
            self._slot(start, end, melody, chords, scale)
            for start, end in times if end > start
        ]

    def _slot(self, start, end, melody, chords, scale):
        sounding = [pitch for note_start, note_end, pitch in melody if note_start <= start < note_end]
        melody_pitch = max(sounding) if sounding else None
        strong = start % BEAT == 0 or end - start >= BEAT
        return Slot(start, end, melody_pitch, strong, self._options(start, end, melody_pitch, strong, chords, scale))

    def _options(self, start, end, melody_pitch, strong, chords, scale):
        steps = set(scale.typ.value)
        low, high = self.low.midi_number, self.high.midi_number
        if melody_pitch is not None:
            high = min(high, melody_pitch - 1)
        in_scale = [
            pitch for pitch in range(low, high + 1)
            if (pitch - scale.root.midi_number) % 12 in steps
        ]
        heard = self._chord_notes_during(start, end, chords)
        allowed = [pitch for pitch in in_scale if not (strong and self._rubs(pitch, heard))]
        if strong:
            if melody_pitch is not None:
                consonant = [pitch for pitch in allowed if (melody_pitch - pitch) % 12 in CONSONANT]
                allowed = consonant or allowed
            chord_tones = [pitch for pitch in allowed if pitch % 12 in self._pitch_classes_at(start, chords)]
            allowed = chord_tones or allowed
        return allowed or in_scale or list(range(low, high + 1)) or [low]

    def _chord_notes_during(self, start, end, chords):
        return {
            pitch % 12 for chord_start, chord_end, pitch in chords
            if chord_start < end and start < chord_end
        }

    def _pitch_classes_at(self, time, chords):
        return {pitch % 12 for start, end, pitch in chords if start <= time < end}

    def _rubs(self, pitch, heard):
        """Return whether a pitch sits a half step from a chord note, as ClashFinder sees it."""
        pitch_class = pitch % 12
        return pitch_class not in heard and any((pitch_class - other) % 12 in (1, 11) for other in heard)

    # Choosing the notes.

    def _search(self, slots, chords, scale):
        generator = random.Random(self.seed)
        paths = [(0, [])]
        for number, slot in enumerate(slots):
            jitter = {pitch: generator.random() / 2 for pitch in slot.options}
            extended = []
            for cost, path in paths:
                for pitch in slot.options:
                    step_cost = self._cost(path, slots, number, pitch, chords)
                    extended.append((cost + step_cost + jitter[pitch], path + [pitch]))
            extended.sort(key=lambda item: item[0])
            paths = extended[:BEAM_WIDTH]
        best = paths[0][1] if paths else []
        return [(slot.start, slot.end, pitch) for slot, pitch in zip(slots, best)]

    def _cost(self, path, slots, number, pitch, chords):
        slot = slots[number]
        cost = 0
        if slot.melody is not None and slot.strong:
            interval = (slot.melody - pitch) % 12
            if interval not in CONSONANT:
                cost += FORBIDDEN
            elif interval in THIRDS_AND_SIXTHS:
                cost -= 0.5
        if not path:
            return cost

        previous = path[-1]
        before = slots[number - 1].melody
        motion = pitch - previous
        leap = abs(motion)
        if slot.melody is not None and before is not None:
            melody_motion = slot.melody - before
            if motion * melody_motion < 0:
                cost -= 1
            elif motion * melody_motion > 0:
                cost += 1
                if (before - previous) % 12 == (slot.melody - pitch) % 12 and (slot.melody - pitch) % 12 in PERFECT:
                    cost += FORBIDDEN
        if leap == 0:
            cost += 2
        elif leap <= 2:
            pass
        elif leap <= 4:
            cost += 1
        elif leap <= 7:
            cost += 3
        else:
            cost += 8
        if not slot.strong and leap > 2:
            cost += 4
        if len(path) >= 2:
            earlier_motion = previous - path[-2]
            if abs(earlier_motion) > 4 and (motion * earlier_motion >= 0 or leap > 2):
                cost += 4
        return cost

    # Writing a canon.

    def _canon(self, melody, chords, total, scale):
        delay = exact_length(self.delay)
        low, high = self.low.midi_number, self.high.midi_number
        notes = []
        for start, end, pitch in melody:
            new_start, new_end = start + delay, min(end + delay, total)
            if new_end > new_start:
                moved = self._into_range(pitch, low, high)
                notes.append((new_start, new_end, self._without_clash(moved, new_start, new_end, chords, low, high)))
        return notes

    def _into_range(self, pitch, low, high):
        while pitch > high:
            pitch -= 12
        while pitch < low:
            pitch += 12
        return pitch

    def _without_clash(self, pitch, start, end, chords, low, high):
        if not (start % BEAT == 0 or end - start >= BEAT):
            return pitch
        heard = self._chord_notes_during(start, end, chords)
        if not self._rubs(pitch, heard):
            return pitch
        tones = self._pitch_classes_at(start, chords) or heard
        for distance in range(1, 12):
            for candidate in (pitch - distance, pitch + distance):
                if low <= candidate <= high and candidate % 12 in tones and not self._rubs(candidate, heard):
                    return candidate
        return pitch

    # Turning the result into a clip.

    def _as_positions(self, notes, total, scale):
        positions = []
        now = Fraction(0)
        for start, end, pitch in sorted(notes):
            if start > now:
                positions.append(Rest(start - now))
            note = Note.from_midi_number(pitch, end - start)
            positions.append(scale.degree_of(note).to_note(scale))
            now = end
        if total > now:
            positions.append(Rest(total - now))
        return positions
