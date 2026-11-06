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

import random
from dataclasses import replace
from enum import Enum, auto

from llamatron.chord import Chord
from llamatron.generators.base import ClipGenerator, exact_length, fit_to_length
from llamatron.midi import HALF_STEPS_PER_OCTAVE
from llamatron.note import Note, Rest, _check_length
from llamatron.clip_grid import _Validated

# How many steps an arpeggiator's offsets can have, as on the Elektron Monomachine.
MIN_OFFSETS, MAX_OFFSETS = 1, 16
# How many octaves it can play a chord across, and how far one offset can move a note.
MIN_OCTAVE_RANGE, MAX_OCTAVE_RANGE = 1, 4
MAX_OFFSET = 24
# An offset of nothing leaves a note where it is, and so does a step with no offsets at all.
NO_OFFSET = 0
# A chord with nothing left of it to play.
NO_LENGTH = 0

MSG_NOT_AN_ORDER = 'expected a ChordOrder, got {value!r}'
MSG_BAD_SEED = 'invalid seed: {value!r} (must be an integer or None)'
MSG_NOT_A_JUMP = 'expected an OctaveJump, got {value!r}'
MSG_BAD_OCTAVE_RANGE = 'invalid octave range: {value!r} (must be a whole number from {lowest} to {highest})'
MSG_BAD_OFFSETS = 'invalid offsets: {value!r} (must be a list of {lowest} to {highest} steps)'
MSG_BAD_OFFSET = 'invalid offset: {value!r} (must be a whole number from -{most} to {most}, or None to mute the step)'


class ChordOrder(Enum):
    """The order in which Arp plays a chord's notes."""

    UP = auto()
    DOWN = auto()
    UP_DOWN = auto()
    DOWN_UP = auto()
    RANDOM = auto()


class OctaveJump(Enum):
    """Where an arpeggiator with an octave range moves up an octave.

    AFTER_CHORD plays the whole chord and then the whole chord again an octave up, so C E G
    becomes C E G C E G. AFTER_EACH_NOTE plays each note in every octave before the next note,
    so it becomes C C E E G G.
    """

    AFTER_CHORD = auto()
    AFTER_EACH_NOTE = auto()


def _check_order(order):
    if not isinstance(order, ChordOrder):
        raise ValueError(MSG_NOT_AN_ORDER.format(value=order))


def _check_seed(seed):
    if seed is not None and type(seed) is not int:
        raise ValueError(MSG_BAD_SEED.format(value=seed))


def _check_jump(jump):
    if not isinstance(jump, OctaveJump):
        raise ValueError(MSG_NOT_A_JUMP.format(value=jump))


def _check_octave_range(octaves):
    if type(octaves) is not int or not MIN_OCTAVE_RANGE <= octaves <= MAX_OCTAVE_RANGE:
        raise ValueError(MSG_BAD_OCTAVE_RANGE.format(value=octaves, lowest=MIN_OCTAVE_RANGE, highest=MAX_OCTAVE_RANGE))


def _check_offsets(offsets):
    if offsets is None:
        return
    if not isinstance(offsets, (list, tuple)) or not MIN_OFFSETS <= len(offsets) <= MAX_OFFSETS:
        raise ValueError(MSG_BAD_OFFSETS.format(value=offsets, lowest=MIN_OFFSETS, highest=MAX_OFFSETS))
    for offset in offsets:
        if offset is not None and not _is_offset(offset):
            raise ValueError(MSG_BAD_OFFSET.format(value=offset, most=MAX_OFFSET))


def _is_offset(offset):
    """Return whether an offset is a whole number of scale notes no further than MAX_OFFSET either way."""
    return type(offset) is int and -MAX_OFFSET <= offset <= MAX_OFFSET


def along_scale(note, steps, scale):
    """Return a note moved a number of notes along a scale, or by half steps without one.

    A note that isn't in the scale keeps its distance from the scale note below it.
    """
    if not steps:
        return note
    if scale is None:
        return note.half_step(steps)
    shape = scale.typ.value
    above_root = note.midi_number - scale.root.midi_number
    octaves, within = divmod(above_root, HALF_STEPS_PER_OCTAVE)
    place = _scale_note_at_or_below(shape, within)
    extra = within - shape[place]
    more, place = divmod(place + steps, len(shape))
    return note.half_step((octaves + more) * HALF_STEPS_PER_OCTAVE + shape[place] + extra - above_root)


def _scale_note_at_or_below(shape, half_steps):
    """Return which note of a scale's octave, counted from 0, is at or just below some half steps above its root."""
    return max(index for index, step in enumerate(shape) if step <= half_steps)


def _lowest_to_highest(chord):
    """Return a chord's notes from lowest to highest, with each pitch only once."""
    by_pitch = {}
    for note in chord.notes:
        by_pitch.setdefault(note.midi_number, note)
    return [by_pitch[midi_number] for midi_number in sorted(by_pitch)]


class Arp(ClipGenerator):
    """Plays each chord one note at a time, every step long, for as long as the chord lasts.

    Rests are left as they are. If the clip has a set length, the result starts again from the
    beginning until it fills that length, and anything past the end is cut off. Set a seed to get
    the same RANDOM result every time.

    octave_range plays the chord again in up to that many octaves, moving up as octave_jump says.
    offsets is a little step sequencer of its own, like the Elektron Monomachine's: each step
    moves its note that many notes along the clip's scale, or half steps if it has none, and a
    step of None is silent. A silent step doesn't use up a note of the chord, and the offsets
    start again with each chord. With offsets or an octave range, a single note is played as a
    chord of one note, so that one note can make a melody. Without them it's left as it is.
    """

    __slots__ = ('_step', '_order', '_seed', '_octave_range', '_octave_jump', '_offsets')

    step = _Validated(_check_length)
    order = _Validated(_check_order)
    seed = _Validated(_check_seed)
    octave_range = _Validated(_check_octave_range)
    octave_jump = _Validated(_check_jump)
    offsets = _Validated(_check_offsets)

    def __init__(self, step, order=ChordOrder.UP, seed=None, octave_range=1, octave_jump=OctaveJump.AFTER_CHORD, offsets=None):
        self.step = step
        self.order = order
        self.seed = seed
        self.octave_range = octave_range
        self.octave_jump = octave_jump
        self.offsets = None if offsets is None else list(offsets)

    def _generate(self, clip):
        generator = random.Random(self.seed)
        original = clip.resolved_notes()
        positions = self._arpeggiate(original, generator, clip.scale)
        if clip.length is None:
            return positions, None

        total = sum(exact_length(position.length) for position in positions)
        while positions and total < exact_length(clip.length):
            more = self._arpeggiate(original, generator, clip.scale)
            positions += more
            total += sum(exact_length(position.length) for position in more)
        return fit_to_length(positions, clip.length), clip.length

    def _plays_single_notes(self):
        return self.offsets is not None or self.octave_range > MIN_OCTAVE_RANGE

    def _arpeggiate(self, positions, generator, scale):
        result = []
        for position in positions:
            if isinstance(position, Chord) or (isinstance(position, Note) and self._plays_single_notes()):
                result += self._arpeggiate_chord(position, generator, scale)
            else:
                result.append(position)
        return result

    def _arpeggiate_chord(self, chord, generator, scale):
        notes = self._climb(_lowest_to_highest(chord) if isinstance(chord, Chord) else [chord])
        pattern = self._pattern(notes)
        result = []
        step = exact_length(self.step)
        remaining = exact_length(chord.length)
        index = 0
        place = 0
        while remaining > NO_LENGTH:
            length = self.step if step <= remaining else remaining
            offset = NO_OFFSET if self.offsets is None else self.offsets[place % len(self.offsets)]
            place += 1
            if offset is None:
                result.append(Rest(length))
            else:
                note = generator.choice(notes) if pattern is None else pattern[index % len(pattern)]
                result.append(replace(along_scale(note, offset, scale), length=length))
                index += 1
            remaining -= min(step, remaining)
        return result

    def _climb(self, notes):
        """Return the chord's notes going up through the octave range, in the octave jump's order."""
        octaves = range(self.octave_range)
        if self.octave_jump is OctaveJump.AFTER_EACH_NOTE:
            return [_up_octaves(note, octave) for note in notes for octave in octaves]
        return [_up_octaves(note, octave) for octave in octaves for note in notes]

    def _pattern(self, notes):
        """Return the notes in the order they repeat, or None if the order is random."""
        down = notes[::-1]
        if self.order is ChordOrder.UP:
            return notes
        if self.order is ChordOrder.DOWN:
            return down
        # The turning points aren't repeated, so C E G becomes C E G E and then C E G E again.
        if self.order is ChordOrder.UP_DOWN:
            return notes + _back_without_ends(notes)
        if self.order is ChordOrder.DOWN_UP:
            return down + _back_without_ends(down)
        return None


def _up_octaves(note, octaves):
    """Return a note moved up a number of octaves."""
    return note.half_step(HALF_STEPS_PER_OCTAVE * octaves)


def _back_without_ends(notes):
    """Return the notes in reverse, without the first or last, so a turn doesn't play either end twice."""
    return notes[-2:0:-1]
