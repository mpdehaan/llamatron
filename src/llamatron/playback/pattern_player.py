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
from llamatron.composition.defaults import DEFAULT_PROBABILITY, DEFAULT_RATCHET, DEFAULT_VELOCITY
from llamatron.composition.file_format import (
    ACCIDENTALS, CC_ROWS, FIXED_CHORDS, LIVE_OCTAVE_OFFSET, NOTE_ROWS, PATTERN_ROWS, SCALE_CHORDS, Row,
)
from llamatron.composition.limits import MAX_PROBABILITY, MAX_VELOCITY, MIN_VELOCITY
from llamatron.composition.song_file_error import SongFileError
from llamatron.generators.arp import along_scale
from llamatron.generators.auto_ratchet import divide
from llamatron.note import SHARP_NAMES, Degree, Note, Rest
from llamatron.song import Clip, Control

# How many octaves away a moved note can go to find one that fits the MIDI range.
MAX_OCTAVE_CHANGE = 10
HALF_STEPS_PER_OCTAVE = 12
# A step with no accidental moves its note by no half steps.
NO_ACCIDENTAL, NO_HALF_STEPS = '', 0
# A clip's running totals, and the lists of steps it keeps its place in.
NOTE_TOTAL, VELOCITY_TOTAL = 'note', 'velocity'
RHYTHM_STEPS, NOTE_STEPS = 'rhythm', 'notes'
# Where a step's values hold the note its grab took, beside its rows.
GRABBED = 'grabbed'
# How messages name a pattern, and what goes wrong while playing one.
WHERE_PATTERN = 'pattern {name!r}'
MSG_NO_SUCH_PATTERN = '{where}: no pattern called {name!r}'
MSG_CANT_PLAY = '{where}: {problem}'
MSG_NO_SCALE = '{where}: it uses scale degrees, but scene {scene} and the song have no scale'


class PatternPlayer:
    """Plays a track's patterns in one scene, a pass at a time.

    It knows the song, for patterns, defaults and scales, the scene it plays in, the clip's scale
    and the track's transpose.
    """

    __slots__ = ('_song', '_scene', '_scale', '_transpose', '_default_length')

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
                raise SongFileError(MSG_NO_SUCH_PATTERN.format(where=where, name=name))
        rhythm, notes = self._song.get_pattern(rhythm_name), self._song.get_pattern(notes_name)
        combined = rhythm_name != notes_name
        note_steps = notes.get_note_steps()

        def direction_of(pattern):
            return direction or pattern.get_direction()

        length = self.pattern_length(rhythm)
        where = WHERE_PATTERN.format(name=notes_name)
        positions, controls, time = [], [], Fraction(0)
        while time < length:
            step = order.next_step((RHYTHM_STEPS, rhythm_name), rhythm.get_steps(), direction_of(rhythm))
            values = _step_values(rhythm, step, PATTERN_ROWS)
            moment = start + time
            duration = self._step_length(values, where)
            # CC values belong to the rhythm, and a rest can send them too.
            controls += _controls_sent(values, time)
            time += duration
            if values[Row.DEGREE] is None or (combined and not note_steps):
                positions.append(Rest(duration))
                continue
            note_step = step
            if combined:
                note_step = note_steps[order.next_step((NOTE_STEPS, notes_name), len(note_steps), direction_of(notes))]
                values.update(_step_values(notes, note_step, NOTE_ROWS))
            drum = notes.is_drum()
            values[GRABBED] = grab.note_at(moment) if grab and notes.get_value(Row.GRAB, note_step) else None
            note_total = totals.add(NOTE_TOTAL, values[Row.NOTE_ADD], notes.get_accumulator_limit())
            velocity_total = totals.add(VELOCITY_TOTAL, values[Row.VELOCITY_ADD], rhythm.get_accumulator_limit())
            positions += self._step(values, drum, where, rolls, note_total, velocity_total)
        clip = Clip(notes=positions, scale=self._scale, controls=controls)
        return clip.section(0, length) if time > length else clip

    def pattern_length(self, pattern):
        """Return how long one pass through a pattern lasts, in whole notes."""
        return sum(
            (self._step_length({Row.DURATION: pattern.get_value(Row.DURATION, step)}, Row.DURATION)
             for step in range(pattern.get_steps())),
            Fraction(0),
        )

    def _step_length(self, values, where):
        """Return how long a step lasts: its duration, or the song's default length if it has none."""
        duration = values[Row.DURATION]
        return self._default_length if duration is None else number(duration, where)

    def _step(self, values, drum, where, rolls, note_total, velocity_total):
        """Return what one step plays, as more than one position if it ratchets."""
        length = self._step_length(values, where)
        default = self._song.get_default_drum_octave() if drum else self._song.get_default_octave()
        octave = _value_or(values[Row.OCTAVE], default) + LIVE_OCTAVE_OFFSET
        velocity = _clamped_velocity(_value_or(values[Row.VELOCITY], DEFAULT_VELOCITY) + velocity_total)
        ratchet = values[Row.RATCHET] or DEFAULT_RATCHET
        offset = values[Row.RATCHET_OFFSET] or NO_HALF_STEPS
        slices = []
        transpose = NO_HALF_STEPS if drum else self._transpose
        for place in range(ratchet):
            shift = transpose + note_total + place * offset
            if values[GRABBED] is not None:
                played = self._grabbed_sound(values[GRABBED], length, shift, drum)
            else:
                played = self._sound(values, drum, length, octave, shift, where)
            slices.append(divide(with_sound(played, velocity=velocity), ratchet))
        if values[Row.GLIDE]:
            slices[-1] = with_sound(slices[-1], glide=True)
        probability = _value_or(values[Row.PROBABILITY], DEFAULT_PROBABILITY)
        if probability >= MAX_PROBABILITY:
            return slices
        return [piece if _rolls_under(rolls, probability) else Rest(piece.length) for piece in slices]

    def _grabbed_sound(self, number_grabbed, length, shift, drum):
        """Return a grabbed note, moved along this clip's scale, or by half steps for drums.

        A note moved outside the MIDI range stays where it was grabbed.
        """
        octave, place = divmod(number_grabbed, HALF_STEPS_PER_OCTAVE)
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
            note = Note(values[Row.DEGREE] + (values[Row.ACCIDENTAL] or NO_ACCIDENTAL), at_octave, length)
            return note.half_step(shift) if shift else note

        problem = None
        for change in _octave_changes_to_try(shift):
            try:
                return attempt(octave + change)
            except ValueError as error:
                problem = problem or error
        raise SongFileError(MSG_CANT_PLAY.format(where=where, problem=problem)) from problem

    def _degree_sound(self, values, length, octave, shift, where):
        if self._scene.get_scale_name() is None:
            raise SongFileError(MSG_NO_SCALE.format(where=where, scene=self._scene.get_number()))
        scale = self._song.get_named_scale(self._scene.get_scale_name()).scale_at(octave)
        half_steps = ACCIDENTALS.get(values[Row.ACCIDENTAL], NO_HALF_STEPS)
        degree = values[Row.DEGREE]
        root = Degree(degree, length, half_steps=half_steps, scale_notes=shift).to_note(scale)
        symbol = None if values[Row.CHORD] is None else str(values[Row.CHORD])
        if symbol is None:
            return root
        if symbol in FIXED_CHORDS:
            return root.to_chord(FIXED_CHORDS[symbol])
        return _scale_chord(SCALE_CHORDS[symbol], degree, length, half_steps, shift, scale)


def _step_values(pattern, step, rows):
    """Return one step's values on some of a pattern's rows, by row."""
    return {row: pattern.get_value(row, step) for row in rows}


def _controls_sent(values, time):
    """Return the CC values a step sends at a time, one for each CC lane it has a value on."""
    return [
        Control(time, lane, values[row], bool(values[Row.SLIDE]))
        for lane, row in enumerate(CC_ROWS) if values[row] is not None
    ]


def _scale_chord(degrees_above, degree, length, half_steps, shift, scale):
    """Return a chord of scale notes: the step's degree and the scale degrees above it that a symbol like 7 names."""
    return Chord([
        Degree(degree + above, length, half_steps=half_steps, scale_notes=shift).to_note(scale)
        for above in degrees_above
    ])


def _value_or(value, default):
    """Return a step's value, or a default if the step leaves it blank."""
    return default if value is None else value


def _clamped_velocity(velocity):
    """Return a velocity moved into the range MIDI allows, if a running total pushed it out."""
    return max(min(velocity, MAX_VELOCITY), MIN_VELOCITY)


def _rolls_under(rolls, probability):
    """Return whether a step with a probability, from 0 to 100, plays this time."""
    return rolls.random() * MAX_PROBABILITY < probability


def _octave_changes_to_try(shift):
    """Return the octave changes to try for a note, nearest first, so a moved note can find an octave that fits.

    A note that isn't moved is only tried where it is.
    """
    changes = [0]
    if shift:
        changes += [change for size in range(1, MAX_OCTAVE_CHANGE + 1) for change in (-size, size)]
    return changes


def with_sound(played, **changes):
    """Return a note or chord with changes to how every note in it plays."""
    if isinstance(played, Chord):
        return Chord([replace(note, **changes) for note in played.notes])
    return replace(played, **changes)
