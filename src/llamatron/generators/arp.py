# llamatron: a music program
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

from enum import Enum, auto

from llamatron.generators.base import ClipGenerator
from llamatron.grid.positions import fit_to_length
from llamatron.music.midi import HALF_STEPS_PER_OCTAVE
from llamatron.support.length import ZERO, Length
from llamatron.support.random_source import random_source
from llamatron.music.note import _check_length
from llamatron.music.sound import CHORD, HELD, HELD_SOUND, KIND, LENGTH, MIDI, NOTE, NOTES, PARTS, PHRASE, Sound
from llamatron.strings.errors import (
    ERR_ARP_BAD_OCTAVE_RANGE, ERR_ARP_BAD_OFFSETS, ERR_ARP_BAD_SEED, ERR_ARP_NOT_AN_ORDER, ERR_BAD_OFFSET, ERR_NOT_A_JUMP,
)

# How many steps an arpeggiator's offsets can have, as on the Elektron Monomachine.
MIN_OFFSETS = 1
MAX_OFFSETS = 16
# How many octaves it can play a chord across, and how far one offset can move a note.
MIN_OCTAVE_RANGE = 1
MAX_OCTAVE_RANGE = 4
MAX_OFFSET = 24
# The registers, in order, as the arp's settings name their adds (composition/file_format.py's REGISTER_NAMES, which the generators don't import).
REGISTERS = ('AX', 'BX', 'CX', 'DX')
# An offset of nothing leaves a note where it is, and so does a step with no offsets at all.
NO_OFFSET = 0


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
        raise ValueError(ERR_ARP_NOT_AN_ORDER.format(value=order))


def _check_seed(seed):
    if seed is not None and type(seed) is not int:
        raise ValueError(ERR_ARP_BAD_SEED.format(value=seed))


def _check_jump(jump):
    if not isinstance(jump, OctaveJump):
        raise ValueError(ERR_NOT_A_JUMP.format(value=jump))


def _check_octave_range(octaves):
    if type(octaves) is not int or not MIN_OCTAVE_RANGE <= octaves <= MAX_OCTAVE_RANGE:
        raise ValueError(ERR_ARP_BAD_OCTAVE_RANGE.format(value=octaves, lowest=MIN_OCTAVE_RANGE, highest=MAX_OCTAVE_RANGE))


def _check_offsets(offsets):
    if offsets is None:
        return
    if not isinstance(offsets, (list, tuple)) or not MIN_OFFSETS <= len(offsets) <= MAX_OFFSETS:
        raise ValueError(ERR_ARP_BAD_OFFSETS.format(value=offsets, lowest=MIN_OFFSETS, highest=MAX_OFFSETS))
    for offset in offsets:
        if offset is not None and not _is_offset(offset):
            raise ValueError(ERR_BAD_OFFSET.format(value=offset, most=MAX_OFFSET))


def _is_offset(offset):
    """Return whether an offset is a whole number of scale notes no further than MAX_OFFSET either way."""
    return type(offset) is int and -MAX_OFFSET <= offset <= MAX_OFFSET


def along_scale(*, note, steps, scale):
    """Return a note, as a sound, moved a number of notes along a scale, or by half steps without one.

    A note that isn't in the scale keeps its distance from the scale note below it.
    """
    if not steps:
        return note
    if scale is None:
        return Sound.half_step(note, steps)
    shape = scale.get_type().value
    above_root = note[MIDI] - scale.get_root().get_midi_number()
    octaves, within = divmod(above_root, HALF_STEPS_PER_OCTAVE)
    place = _scale_note_at_or_below(shape=shape, half_steps=within)
    extra = within - shape[place]
    more, place = divmod(place + steps, len(shape))
    return Sound.half_step(note, (octaves + more) * HALF_STEPS_PER_OCTAVE + shape[place] + extra - above_root)


def _scale_note_at_or_below(*, shape, half_steps):
    """Return which note of a scale's octave, counted from 0, is at or just below some half steps above its root."""
    return max(index for index, step in enumerate(shape) if step <= half_steps)


def _lowest_to_highest(chord):
    """Return a chord's notes from lowest to highest, with each pitch only once."""
    by_pitch = {}
    for note in chord[NOTES]:
        by_pitch.setdefault(note[MIDI], note)
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

    The ax_add to dx_add settings add to a register on every note it plays, and ax_step_adds to
    dx_step_adds on each step of the offsets, silent ones too, since registers follow time and
    not sound (the user's design of 2026-11-11). register_adds() says what the last clip it made
    added and when, for the render's register timeline.
    """

    __slots__ = ('_step', '_order', '_seed', '_octave_range', '_octave_jump', '_offsets', '_note_adds', '_step_adds', '_adds', '_start_state', '_random_state')

    def __init__(self, *, step, order=ChordOrder.UP, seed=None, octave_range=1, octave_jump=OctaveJump.AFTER_CHORD, offsets=None,
                 ax_add=None, bx_add=None, cx_add=None, dx_add=None, ax_step_adds=None, bx_step_adds=None, cx_step_adds=None, dx_step_adds=None, continuation=None):
        _check_length(step)
        _check_order(order)
        _check_seed(seed)
        _check_octave_range(octave_range)
        _check_jump(octave_jump)
        _check_offsets(offsets)
        self._step = step
        self._order = order
        self._seed = seed
        self._octave_range = octave_range
        self._octave_jump = octave_jump
        self._offsets = None if offsets is None else list(offsets)
        self._note_adds = {name: amount for name, amount in zip(REGISTERS, (ax_add, bx_add, cx_add, dx_add)) if amount}
        self._step_adds = {name: list(adds) for name, adds in zip(REGISTERS, (ax_step_adds, bx_step_adds, cx_step_adds, dx_step_adds)) if adds}
        self._adds = []
        # Where its random choices carry on from, the same track's clip before's, when its Restart carries on.
        self._start_state = None if continuation is None else continuation.state
        self._random_state = self._start_state

    def end_state(self):
        return self._random_state

    def get_step(self):
        return self._step

    def set_step(self, step):
        _check_length(step)
        self._step = step

    def get_order(self):
        return self._order

    def set_order(self, order):
        _check_order(order)
        self._order = order

    def get_seed(self):
        return self._seed

    def set_seed(self, seed):
        _check_seed(seed)
        self._seed = seed

    def register_adds(self):
        return [(Length.rational(time), adds) for time, adds in self._adds]

    def _generate(self, clip):
        generator = random_source(self._seed)
        # Unseeded, the draws come from Python's own stream, which carries on by itself and is never set.
        if self._start_state is not None and self._seed is not None:
            generator.setstate(self._start_state)
        original = clip.resolved_sounds()
        self._adds = []
        positions = self._arpeggiate(positions=original, generator=generator, scale=clip.get_scale(), start=ZERO)
        if clip.get_length() is None:
            self._random_state = None if self._seed is None else generator.getstate()
            return positions, None

        wanted = Length.exact(clip.get_length())
        total = Length.total([position[LENGTH] for position in positions])
        while positions and Length.less(total, wanted):
            more = self._arpeggiate(positions=original, generator=generator, scale=clip.get_scale(), start=total)
            positions += more
            total = Length.add(total, Length.total([position[LENGTH] for position in more]))
        self._adds = [(time, adds) for time, adds in self._adds if Length.less(time, wanted)]
        self._random_state = None if self._seed is None else generator.getstate()
        return fit_to_length(positions=positions, length=wanted), clip.get_length()

    def _plays_single_notes(self):
        return self._offsets is not None or self._octave_range > MIN_OCTAVE_RANGE

    def _arpeggiate(self, *, positions, generator, scale, start):
        """Return the positions arpeggiated, the first starting at start, a length as a pair, which the register adds are timed from."""
        result = []
        now = start
        for position in positions:
            kind = position[KIND]
            if kind == HELD or kind == PHRASE:
                result.append(self._arpeggiate_held(held=position, generator=generator, scale=scale, start=now))
            elif kind == CHORD or (kind == NOTE and self._plays_single_notes()):
                result += self._arpeggiate_chord(chord=position, generator=generator, scale=scale, start=now)
            else:
                result.append(position)
            now = Length.add(now, position[LENGTH])
        return result

    def _arpeggiate_held(self, *, held, generator, scale, start):
        """Return a held sound arpeggiated across its own length, still held in the same place."""
        parts = held[PARTS] if held[KIND] == PHRASE else [held[HELD_SOUND]]
        return Sound.phrase(self._arpeggiate(positions=parts, generator=generator, scale=scale, start=start), held[LENGTH])

    def _arpeggiate_chord(self, *, chord, generator, scale, start):
        notes = self._climb(_lowest_to_highest(chord) if chord[KIND] == CHORD else [chord])
        pattern = self._pattern(notes)
        result = []
        step = Length.exact(self._step)
        remaining = chord[LENGTH]
        index = 0
        place = 0
        now = start
        while Length.is_positive(remaining):
            length = Length.shorter(step, remaining)
            offset = NO_OFFSET if self._offsets is None else self._offsets[place % len(self._offsets)]
            self._note_step_adds(time=now, place=place, plays=offset is not None)
            place += 1
            if offset is None:
                result.append(Sound.rest(length))
            else:
                note = generator.choice(notes) if pattern is None else pattern[index % len(pattern)]
                result.append(Sound.with_length(along_scale(note=note, steps=offset, scale=scale), length))
                index += 1
            remaining = Length.subtract(remaining, length)
            now = Length.add(now, length)
        return result

    def _note_step_adds(self, *, time, place, plays):
        """Note what a step of the arp adds to the registers: its offsets step's adds, and each note's adds when it plays a note."""
        adds = dict(self._note_adds) if plays else {}
        if self._offsets is not None:
            for name, row in self._step_adds.items():
                amount = row[place % len(self._offsets) % len(row)]
                if amount:
                    adds[name] = adds.get(name, 0) + amount
        if adds:
            self._adds.append((time, adds))

    def _climb(self, notes):
        """Return the chord's notes going up through the octave range, in the octave jump's order."""
        octaves = range(self._octave_range)
        if self._octave_jump is OctaveJump.AFTER_EACH_NOTE:
            return [_up_octaves(note=note, octaves=octave) for note in notes for octave in octaves]
        return [_up_octaves(note=note, octaves=octave) for octave in octaves for note in notes]

    def _pattern(self, notes):
        """Return the notes in the order they repeat, or None if the order is random."""
        down = notes[::-1]
        if self._order is ChordOrder.UP:
            return notes
        if self._order is ChordOrder.DOWN:
            return down
        # The turning points aren't repeated, so C E G becomes C E G E and then C E G E again.
        if self._order is ChordOrder.UP_DOWN:
            return notes + _back_without_ends(notes)
        if self._order is ChordOrder.DOWN_UP:
            return down + _back_without_ends(down)
        return None


def _up_octaves(*, note, octaves):
    """Return a note moved up a number of octaves."""
    return Sound.half_step(note, HALF_STEPS_PER_OCTAVE * octaves)


def _back_without_ends(notes):
    """Return the notes in reverse, without the first or last, so a turn doesn't play either end twice."""
    return notes[-2:0:-1]
