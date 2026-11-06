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

"""Playing one pass through a pattern, step by step, into notes, chords and rests."""

from dataclasses import replace
from fractions import Fraction

from llamatron.chord import Chord
from llamatron.composition.checks import number
from llamatron.composition.file_format import (
    ACCIDENTALS, CC_ROWS, DEFAULT_PROBABILITY, DEFAULT_RATCHET, DEFAULT_VELOCITY, FIXED_CHORDS, LIVE_OCTAVE_OFFSET,
    NOTE_ROWS, PATTERN_ROWS, SCALE_CHORDS,
)
from llamatron.composition.song_file_error import SongFileError
from llamatron.generators.arp import along_scale
from llamatron.generators.auto_ratchet import divide
from llamatron.note import SHARP_NAMES, Degree, Note, Rest
from llamatron.song import Clip, Control

# How many octaves away a moved note can go to find one that fits the MIDI range.
MAX_OCTAVE_CHANGE = 10


class PatternPlayer:
    """Plays a track's patterns in one scene, a pass at a time.

    It knows the song, for patterns, defaults and scales, the scene it plays in, the clip's scale
    and the track's transpose.
    """

    def __init__(self, song, scene, scale, track):
        self._song = song
        self._scene = scene
        self._scale = scale
        self._transpose = track.get_transpose()
        self._default_length = song.get_default_length()

    def play_pass(self, rhythm_name, notes_name, grab, direction, where, rolls, order, totals, start):
        """Return one pass through a rhythm, as notes, chords and rests, starting at a time in the clip.

        The notes pattern's grab steps play what grab, a GrabSource, gives for the time they start,
        if it's given. Whichever order the steps play in, a pass lasts as long as the rhythm pattern
        does, so that a direction can't change how long a clip or scene is. The last step is cut to
        fit. rolls is the random generator probability uses, order the StepOrder, and totals the
        clip's Accumulators.
        """
        for name in (rhythm_name, notes_name):
            if not self._song.has_pattern(name):
                raise SongFileError(f'{where}: no pattern called {name!r}')
        rhythm, notes = self._song.get_pattern(rhythm_name), self._song.get_pattern(notes_name)
        combined = rhythm_name != notes_name
        note_steps = notes.get_note_steps()

        def direction_of(pattern):
            return direction or pattern.get_direction()

        length = self.pattern_length(rhythm)
        where = f'pattern {notes_name!r}'
        positions, controls, time = [], [], Fraction(0)
        while time < length:
            step = order.next_step(('rhythm', rhythm_name), rhythm.get_steps(), direction_of(rhythm))
            values = {row: rhythm.get_value(row, step) for row in PATTERN_ROWS}
            moment = start + time
            duration = self._default_length if values['duration'] is None else number(values['duration'], where)
            # CC values belong to the rhythm, and a rest can send them too.
            controls += [
                Control(time, lane, values[row], bool(values['slide']))
                for lane, row in enumerate(CC_ROWS) if values[row] is not None
            ]
            time += duration
            if values['degree'] is None or (combined and not note_steps):
                positions.append(Rest(duration))
                continue
            note_step = step
            if combined:
                note_step = note_steps[order.next_step(('notes', notes_name), len(note_steps), direction_of(notes))]
                values.update({row: notes.get_value(row, note_step) for row in NOTE_ROWS})
            drum = notes.is_drum()
            values['grabbed'] = grab.note_at(moment) if grab and notes.get_value('grab', note_step) else None
            note_total = totals.add('note', values['note_add'], notes.get_accumulator_limit())
            velocity_total = totals.add('velocity', values['velocity_add'], rhythm.get_accumulator_limit())
            positions += self._step(values, drum, where, rolls, note_total, velocity_total)
        clip = Clip(notes=positions, scale=self._scale, controls=controls)
        return clip.section(0, length) if time > length else clip

    def pattern_length(self, pattern):
        """Return how long one pass through a pattern lasts, in whole notes."""
        return sum(
            (self._default_length if pattern.get_value('duration', step) is None else number(pattern.get_value('duration', step), 'duration')
             for step in range(pattern.get_steps())),
            Fraction(0),
        )

    def _step(self, values, drum, where, rolls, note_total, velocity_total):
        """Return what one step plays, as more than one position if it ratchets."""
        length = self._default_length if values['duration'] is None else number(values['duration'], where)
        default = self._song.get_default_drum_octave() if drum else self._song.get_default_octave()
        octave = (default if values['octave'] is None else values['octave']) + LIVE_OCTAVE_OFFSET
        velocity = DEFAULT_VELOCITY if values['velocity'] is None else values['velocity']
        velocity = max(min(velocity + velocity_total, 127), 1)
        ratchet = values['ratchet'] or DEFAULT_RATCHET
        offset = values['ratchet_offset'] or 0
        slices = []
        transpose = 0 if drum else self._transpose
        for place in range(ratchet):
            shift = transpose + note_total + place * offset
            if values['grabbed'] is not None:
                played = self._grabbed_sound(values['grabbed'], length, shift, drum)
            else:
                played = self._sound(values, drum, length, octave, shift, where)
            slices.append(divide(with_sound(played, velocity=velocity), ratchet))
        if values['glide']:
            slices[-1] = with_sound(slices[-1], glide=True)
        probability = DEFAULT_PROBABILITY if values['probability'] is None else values['probability']
        if probability >= 100:
            return slices
        return [
            piece if rolls.random() * 100 < probability else Rest(piece.length)
            for piece in slices
        ]

    def _grabbed_sound(self, number_grabbed, length, shift, drum):
        """Return a grabbed note, moved along this clip's scale, or by half steps for drums.

        A note moved outside the MIDI range stays where it was grabbed.
        """
        octave, place = divmod(number_grabbed, 12)
        note = Note(SHARP_NAMES[place], octave, length)
        try:
            return along_scale(note, shift, None if drum else self._scale)
        except ValueError:
            return note

    def _sound(self, values, drum, length, octave, shift, where):
        """Return a step's note or chord, moved by a number of scale degrees or, for drums, half steps.

        A note moved outside the MIDI range goes to the nearest octave that fits.
        """
        def attempt(at_octave):
            if not drum:
                return self._degree_sound(values, length, at_octave, shift, where)
            note = Note(values['degree'] + (values['accidental'] or ''), at_octave, length)
            return note.half_step(shift) if shift else note

        changes = [0]
        if shift:
            changes += [change for size in range(1, MAX_OCTAVE_CHANGE + 1) for change in (-size, size)]
        problem = None
        for change in changes:
            try:
                return attempt(octave + change)
            except ValueError as error:
                problem = problem or error
        raise SongFileError(f'{where}: {problem}') from problem

    def _degree_sound(self, values, length, octave, shift, where):
        if self._scene.get_scale_name() is None:
            raise SongFileError(f'{where}: it uses scale degrees, but scene {self._scene.get_number()} and the song have no scale')
        scale = self._song.get_named_scale(self._scene.get_scale_name()).scale_at(octave)
        half_steps = ACCIDENTALS.get(values['accidental'], 0)
        degree = values['degree']
        root = Degree(degree, length, half_steps=half_steps, scale_notes=shift).to_note(scale)
        symbol = None if values['chord'] is None else str(values['chord'])
        if symbol is None:
            return root
        if symbol in FIXED_CHORDS:
            return root.to_chord(FIXED_CHORDS[symbol])
        return Chord([
            Degree(degree + above, length, half_steps=half_steps, scale_notes=shift).to_note(scale)
            for above in SCALE_CHORDS[symbol]
        ])


def with_sound(played, **changes):
    """Return a note or chord with changes to how every note in it plays."""
    if isinstance(played, Chord):
        return Chord([replace(note, **changes) for note in played.notes])
    return replace(played, **changes)
