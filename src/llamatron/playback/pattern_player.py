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

from dataclasses import dataclass, replace
from fractions import Fraction

from llamatron.chord import Chord
from llamatron.composition.checks import written_length
from llamatron.composition.defaults import DEFAULT_PROBABILITY, DEFAULT_RATCHET, DEFAULT_VELOCITY
from llamatron.composition.file_format import (
    ACCIDENTALS, CC_ROWS, FIXED_CHORDS, GATE_MODIFIERS, LIVE_OCTAVE_OFFSET, PATTERN_ROWS, REGISTER_ADD_ROWS,
    REGISTER_NOTE_ROWS, REGISTER_VELOCITY_ROWS, SCALE_CHORDS, Row,
)
from llamatron.composition.limits import MAX_GATE, MAX_PROBABILITY, MAX_VELOCITY, MIN_VELOCITY
from llamatron.composition.song_file_error import SongFileError
from llamatron.generators.arp import along_scale
from llamatron.generators.auto_ratchet import divide
from llamatron.held import Held, phrase
from llamatron.note import MAX_OCTAVE, MIN_OCTAVE, SHARP_NAMES, Degree, Note, Rest
from llamatron.clip_grid import Clip, Control

# How many octaves away a moved note can go to find one that fits the MIDI range. A move of
# whole octaves is taken out first, so this only has to cover the MIDI range itself.
MAX_OCTAVE_CHANGE = 10
HALF_STEPS_PER_OCTAVE = 12
# A step with no accidental moves its note by no half steps.
NO_ACCIDENTAL, NO_HALF_STEPS = '', 0
# The list of steps a clip keeps its place in.
PATTERN_STEPS = 'steps'
# What registers add to a note or velocity when a step uses none of them.
NOTHING_ADDED = 0
# How long the ties at the start of a pass last when there are none.
NO_TIES = Fraction(0)


@dataclass(slots=True)
class Pass:
    """One pass through a pattern: its clip, and how long the ties at its start last.

    Ties at the very start of a pass continue the note that the pass before it ended with, which
    the pass can't reach, so whoever joins the passes lengthens that note by tied_from_before.
    """

    clip: Clip
    tied_from_before: Fraction
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

    __slots__ = ('_song', '_scene', '_scale', '_transpose')

    def __init__(self, song, scene, scale, track):
        self._song = song
        self._scene = scene
        self._scale = scale
        self._transpose = track.get_transpose()

    def play_pass(self, pattern_name, grab, direction, where, rolls, order, registers, start, changes_registers=True):
        """Return one pass through a pattern as a Pass, with notes, chords and rests, starting at a time in the clip.

        Every step takes the same time, its step size, whatever order the steps play in, which is
        the pattern's direction unless direction overrides it. A step that plays sounds for its
        gate, which can run past later steps but not past the end of the pass. A tied step plays
        nothing and keeps the note that played just before it, in time, sounding to the end of
        the tied step, or for its gate if that's longer. A tie after an empty step is silence, and
        ties at the start of the pass are left for the caller to join to the pass before. The
        pattern's grab steps play what grab, a GrabSource, gives for the time they start, if it's
        given. rolls is the random generator probability uses, and order the StepOrder.

        registers is a RegisterRecorder or RegisterReader. Every step adds to the registers, even
        one with no note, unless changes_registers is false, as for a morph's target, and then
        moves its note and velocity by the values of the registers it uses, after its own adds.
        """
        if not self._song.has_pattern(pattern_name):
            raise SongFileError(MSG_NO_SUCH_PATTERN.format(where=where, name=pattern_name))
        pattern = self._song.get_pattern(pattern_name)
        step_size = self._song.get_pattern_step_size(pattern)
        length = self.pattern_length(pattern)
        where = WHERE_PATTERN.format(name=pattern_name)
        sounding, controls = [], []
        # Which entry of sounding the last step left sounding for a tie to lengthen, if any, and
        # how many tied steps came before anything else.
        tied_to, leading_ties = None, 0
        for slot in range(pattern.get_steps()):
            time = slot * step_size
            step = order.next_step((PATTERN_STEPS, pattern_name), pattern.get_steps(), direction or pattern.get_direction())
            values = _step_values(pattern, step, PATTERN_ROWS)
            # A step with no note can send CC values and add to the registers too.
            controls += _controls_sent(values, time)
            current = registers.at_step(start + time, _register_adds(values) if changes_registers else {})
            if values[Row.TIE]:
                if tied_to is not None:
                    sounding[tied_to] = _lengthened_to(sounding[tied_to], time + step_size)
                elif slot == leading_ties:
                    leading_ties += 1
                continue
            if values[Row.DEGREE] is None:
                tied_to = None
                continue
            tied_to = len(sounding)
            drum = pattern.is_drum()
            values[GRABBED] = grab.note_at(start + time) if grab and values[Row.GRAB] else None
            # Drum patterns have no scale to move a note along, so registers only change their velocity.
            note_moved = NOTHING_ADDED if drum else _used_values(values, current, REGISTER_NOTE_ROWS)
            velocity_added = _used_values(values, current, REGISTER_VELOCITY_ROWS)
            gate = min(_gate(values, step_size, where), length - time)
            sounding.append((time, self._step(values, gate, drum, where, rolls, note_moved, velocity_added)))
        clip = Clip(notes=_in_sequence(sounding, length, step_size), scale=self._scale, controls=controls)
        return Pass(clip, leading_ties * step_size)

    def pattern_length(self, pattern):
        """Return how long one pass through a pattern lasts, in whole notes: its steps times its step size."""
        return pattern.get_steps() * self._song.get_pattern_step_size(pattern)

    def _step(self, values, length, drum, where, rolls, note_moved, velocity_added):
        """Return what one step plays, lasting length, its gate, as more than one position if it ratchets.

        Registers move its note note_moved scale notes and add velocity_added to its velocity.
        """
        default = self._song.get_default_drum_octave() if drum else self._song.get_default_octave()
        octave = _value_or(values[Row.OCTAVE], default) + LIVE_OCTAVE_OFFSET
        velocity = _clamped_velocity(_value_or(values[Row.VELOCITY], DEFAULT_VELOCITY) + velocity_added)
        ratchet = values[Row.RATCHET] or DEFAULT_RATCHET
        offset = values[Row.RATCHET_OFFSET] or NO_HALF_STEPS
        slices = []
        transpose = NO_HALF_STEPS if drum else self._transpose
        for place in range(ratchet):
            shift = transpose + note_moved + place * offset
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

        # Moving by a whole octave's worth of notes is the same as moving the octave, so a big
        # move, like four registers can make, starts from an octave in the MIDI range.
        octaves, shift = divmod(shift, self._notes_per_octave(drum))
        octave = max(MIN_OCTAVE, min(octave + octaves, MAX_OCTAVE))
        problem = None
        for change in _octave_changes_to_try(shift or octaves):
            try:
                return attempt(octave + change)
            except ValueError as error:
                problem = problem or error
        raise SongFileError(MSG_CANT_PLAY.format(where=where, problem=problem)) from problem

    def _notes_per_octave(self, drum):
        """Return how many notes a move needs to go up an octave: the size of the scene's scale, or 12 half steps for drums."""
        if drum or self._scene.get_scale_name() is None:
            return HALF_STEPS_PER_OCTAVE
        return len(self._song.get_named_scale(self._scene.get_scale_name()).scale_at(MIN_OCTAVE).typ.value)

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


def _lengthened_to(entry, end):
    """Return a sounding entry, (start, pieces), with its last piece lengthened so the sound lasts until end, if it doesn't already.

    A piece that probability turned into a rest stays as it is, because there's no note to hold.
    """
    start, pieces = entry
    total = sum((piece.length for piece in pieces), Fraction(0))
    extra = end - (start + total)
    if extra <= 0 or isinstance(pieces[-1], Rest):
        return entry
    return start, [*pieces[:-1], with_sound(pieces[-1], length=pieces[-1].length + extra)]


def _gate(values, step_size, where):
    """Return how long a step's note sounds: its gate, or one step if it has none, made dotted or a triplet by its Dot row."""
    gate = step_size if values[Row.GATE] is None else written_length(values[Row.GATE], where, MAX_GATE)
    modifier = values[Row.DOT]
    return gate if modifier is None else gate * GATE_MODIFIERS[modifier]


def _in_sequence(sounding, length, step_size):
    """Return the notes of a pass as a clip's sequence of positions, from (start, what it plays) for each step that plays.

    A note whose gate reaches exactly to the next note is an ordinary position, as it always
    was. A shorter one is followed by rests, one for each step until the next note. A longer one
    is Held, so the next note starts while it still sounds.
    """
    positions, now = [], Fraction(0)
    for place, (start, played) in enumerate(sounding):
        following = sounding[place + 1][0] if place + 1 < len(sounding) else length
        positions += _rests(now, start, step_size)
        gate = sum((piece.length for piece in played), Fraction(0))
        gap = following - start
        if gate > gap:
            positions.append(Held(played[0] if len(played) == 1 else phrase(played), gap))
            now = following
        else:
            positions += played
            now = start + gate
    return positions + _rests(now, length, step_size)


def _rests(start, end, step_size):
    """Return the rests from a start to an end, one for each step, with the first ending at the next step."""
    rests, now = [], start
    while now < end:
        step_end = (now // step_size + 1) * step_size
        piece_end = min(step_end, end)
        rests.append(Rest(piece_end - now))
        now = piece_end
    return rests


def _step_values(pattern, step, rows):
    """Return one step's values on some of a pattern's rows, by row."""
    return {row: pattern.get_value(row, step) for row in rows}


def _register_adds(values):
    """Return what a step adds to each register it adds to, by register name."""
    return {name: values[row] for name, row in REGISTER_ADD_ROWS.items() if values[row]}


def _used_values(values, current, rows):
    """Return the total of the registers a step uses on some rows, like its +Note rows, from their current values."""
    return sum((current[name] for name, row in rows.items() if values[row]), NOTHING_ADDED)


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
    """Return a velocity moved into the range MIDI allows, if registers pushed it out."""
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
