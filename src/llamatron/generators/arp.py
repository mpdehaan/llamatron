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
from llamatron.note import Note, Rest, _check_length
from llamatron.song import _Validated

# How many steps an arpeggiator's offsets can have, as on the Elektron Monomachine.
MAX_OFFSETS = 16
MAX_OCTAVE_RANGE = 4
MAX_OFFSET = 24


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
        raise ValueError(f'expected a ChordOrder, got {order!r}')


def _check_seed(seed):
    if seed is not None and type(seed) is not int:
        raise ValueError(f'invalid seed: {seed!r} (must be an integer or None)')


def _check_jump(jump):
    if not isinstance(jump, OctaveJump):
        raise ValueError(f'expected an OctaveJump, got {jump!r}')


def _check_octave_range(octaves):
    if type(octaves) is not int or not 1 <= octaves <= MAX_OCTAVE_RANGE:
        raise ValueError(f'invalid octave range: {octaves!r} (must be a whole number from 1 to {MAX_OCTAVE_RANGE})')


def _check_offsets(offsets):
    if offsets is None:
        return
    if not isinstance(offsets, (list, tuple)) or not 1 <= len(offsets) <= MAX_OFFSETS:
        raise ValueError(f'invalid offsets: {offsets!r} (must be a list of 1 to {MAX_OFFSETS} steps)')
    for offset in offsets:
        if offset is not None and (type(offset) is not int or not -MAX_OFFSET <= offset <= MAX_OFFSET):
            raise ValueError(f'invalid offset: {offset!r} (must be a whole number from -{MAX_OFFSET} to {MAX_OFFSET}, or None to mute the step)')


def along_scale(note, steps, scale):
    """Return a note moved a number of notes along a scale, or by half steps without one.

    A note that isn't in the scale keeps its distance from the scale note below it.
    """
    if not steps:
        return note
    if scale is None:
        return note.half_step(steps)
    shape = scale.typ.value
    octaves, within = divmod(note.midi_number - scale.root.midi_number, 12)
    place = max(index for index, step in enumerate(shape) if step <= within)
    extra = within - shape[place]
    more, place = divmod(place + steps, len(shape))
    return note.half_step((octaves + more) * 12 + shape[place] + extra - (note.midi_number - scale.root.midi_number))


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
        return self.offsets is not None or self.octave_range > 1

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
        while remaining > 0:
            length = self.step if step <= remaining else remaining
            offset = 0 if self.offsets is None else self.offsets[place % len(self.offsets)]
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
            return [note.half_step(12 * octave) for note in notes for octave in octaves]
        return [note.half_step(12 * octave) for octave in octaves for note in notes]

    def _pattern(self, notes):
        """Return the notes in the order they repeat, or None if the order is random."""
        down = notes[::-1]
        if self.order is ChordOrder.UP:
            return notes
        if self.order is ChordOrder.DOWN:
            return down
        # The turning points aren't repeated, so C E G becomes C E G E and then C E G E again.
        if self.order is ChordOrder.UP_DOWN:
            return notes + notes[-2:0:-1]
        if self.order is ChordOrder.DOWN_UP:
            return down + down[-2:0:-1]
        return None
