# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

from enum import auto, Enum

from llamatron.engine.clips.positions import fit_to_length
from llamatron.engine.generators.arp import schema
from llamatron.engine.generators.base import ClipGenerator
from llamatron.engine.parts.scale_moves import along_scale
from llamatron.math import length as length_values
from llamatron.math.length import Length
from llamatron.math.random_source import random_source
from llamatron.model.values import midi, sound
from llamatron.model.values.note import _check_length
from llamatron.model.values.sound import Sound
from llamatron.user_strings import errors

# How many steps an arpeggiator's offsets can have, as on a groovebox.
MIN_OFFSETS = 1
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
        raise ValueError(errors.ERR_ARP_NOT_AN_ORDER.format(value=order))


def _check_seed(seed):
    if seed is not None and type(seed) is not int:
        raise ValueError(errors.ERR_ARP_BAD_SEED.format(value=seed))


def _check_jump(jump):
    if not isinstance(jump, OctaveJump):
        raise ValueError(errors.ERR_NOT_A_JUMP.format(value=jump))


def _check_octave_range(octaves):
    if type(octaves) is not int or not schema.MIN_OCTAVE_RANGE <= octaves <= schema.MAX_OCTAVE_RANGE:
        raise ValueError(errors.ERR_ARP_BAD_OCTAVE_RANGE.format(value=octaves, lowest=schema.MIN_OCTAVE_RANGE, highest=schema.MAX_OCTAVE_RANGE))


def _check_offsets(offsets):
    if offsets is None:
        return
    if not isinstance(offsets, (list, tuple)) or not MIN_OFFSETS <= len(offsets) <= schema.MAX_OFFSETS:
        raise ValueError(errors.ERR_ARP_BAD_OFFSETS.format(value=offsets, lowest=MIN_OFFSETS, highest=schema.MAX_OFFSETS))
    for offset in offsets:
        if offset is not None and not _is_offset(offset):
            raise ValueError(errors.ERR_BAD_OFFSET.format(value=offset, most=schema.MAX_OFFSET))


def _is_offset(offset):
    """Return whether an offset is a whole number of scale notes no further than MAX_OFFSET either way."""
    return type(offset) is int and -schema.MAX_OFFSET <= offset <= schema.MAX_OFFSET


def _lowest_to_highest(chord):
    """Return a chord's notes from lowest to highest, with each pitch only once."""
    by_pitch = {}
    for note in chord[sound.NOTES]:
        by_pitch.setdefault(note[sound.MIDI], note)
    return [by_pitch[midi_number] for midi_number in sorted(by_pitch)]


class Arp(ClipGenerator):
    """Plays each chord one note at a time, every step long, for as long as the chord lasts.

    Rests are left as they are. If the clip has a set length, the result starts again from the
    beginning until it fills that length, and anything past the end is cut off. Set a seed to get
    the same RANDOM result every time.

    octave_range plays the chord again in up to that many octaves, moving up as octave_jump says.
    offsets is a little step sequencer of its own, like a groovebox's: each step
    moves its note that many notes along the clip's scale, or half steps if it has none, and a
    step of None is silent. A silent step doesn't use up a note of the chord, and the offsets
    start again with each chord. With offsets or an octave range, a single note is played as a
    chord of one note, so that one note can make a melody. Without them it's left as it is.
    """

    __slots__ = ('_step', '_order', '_seed', '_octave_range', '_octave_jump', '_offsets', '_start_state', '_random_state')

    def __init__(self, *, step, order=ChordOrder.UP, seed=None, octave_range=1, octave_jump=OctaveJump.AFTER_CHORD, offsets=None, continuation=None):
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
        self._offsets = None
        if offsets is not None:
            self._offsets = list(offsets)
        # Where its random choices carry on from, the same track's clip before's, when its Restart carries on.
        self._start_state = None
        if continuation is not None:
            self._start_state = continuation.state
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

    def _generate(self, clip):
        generator = random_source(self._seed)
        # Unseeded, the draws come from Python's own stream, which carries on by itself and is never set.
        if self._start_state is not None and self._seed is not None:
            generator.setstate(self._start_state)
        original = clip.resolved_sounds()
        positions = self._arpeggiate(positions=original, generator=generator, scale=clip.get_scale(), start=length_values.ZERO)
        if clip.get_length() is None:
            self._random_state = None
            if self._seed is not None:
                self._random_state = generator.getstate()
            return positions, None

        wanted = Length.exact(clip.get_length())
        total = Length.total([position[sound.LENGTH] for position in positions])
        while positions and Length.less(total, wanted):
            more = self._arpeggiate(positions=original, generator=generator, scale=clip.get_scale(), start=total)
            positions += more
            total = Length.add(total, Length.total([position[sound.LENGTH] for position in more]))
        self._random_state = None
        if self._seed is not None:
            self._random_state = generator.getstate()
        return fit_to_length(positions=positions, length=wanted), clip.get_length()

    def _plays_single_notes(self):
        return self._offsets is not None or self._octave_range > schema.MIN_OCTAVE_RANGE

    def _arpeggiate(self, *, positions, generator, scale, start):
        """Return the positions arpeggiated, the first starting at start, a length as a pair."""
        result = []
        now = start
        for position in positions:
            kind = position[sound.KIND]
            if kind == sound.HELD or kind == sound.PHRASE:
                result.append(self._arpeggiate_held(held=position, generator=generator, scale=scale, start=now))
            elif kind == sound.CHORD or (kind == sound.NOTE and self._plays_single_notes()):
                result += self._arpeggiate_chord(chord=position, generator=generator, scale=scale, start=now)
            else:
                result.append(position)
            now = Length.add(now, position[sound.LENGTH])
        return result

    def _arpeggiate_held(self, *, held, generator, scale, start):
        """Return a held sound arpeggiated across its own length, still held in the same place."""
        parts = [held[sound.HELD_SOUND]]
        if held[sound.KIND] == sound.PHRASE:
            parts = held[sound.PARTS]
        return Sound.phrase(self._arpeggiate(positions=parts, generator=generator, scale=scale, start=start), held[sound.LENGTH])

    def _arpeggiate_chord(self, *, chord, generator, scale, start):
        chord_notes = [chord]
        if chord[sound.KIND] == sound.CHORD:
            chord_notes = _lowest_to_highest(chord)
        notes = self._climb(chord_notes)
        pattern = self._pattern(notes)
        result = []
        step = Length.exact(self._step)
        remaining = chord[sound.LENGTH]
        index = 0
        place = 0
        now = start
        while Length.is_positive(remaining):
            length = Length.shorter(step, remaining)
            offset = NO_OFFSET
            if self._offsets is not None:
                offset = self._offsets[place % len(self._offsets)]
            place += 1
            if offset is None:
                result.append(Sound.rest(length))
            else:
                if pattern is None:
                    note = generator.choice(notes)
                else:
                    note = pattern[index % len(pattern)]
                result.append(Sound.with_length(along_scale(note=note, steps=offset, scale=scale), length))
                index += 1
            remaining = Length.subtract(remaining, length)
            now = Length.add(now, length)
        return result

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
    return Sound.half_step(note, midi.HALF_STEPS_PER_OCTAVE * octaves)


def _back_without_ends(notes):
    """Return the notes in reverse, without the first or last, so a turn doesn't play either end twice."""
    return notes[-2:0:-1]
