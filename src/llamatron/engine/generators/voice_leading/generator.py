# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Voice leading generator: each chord of a clip voiced as near as it can be to the chord before.

The first chord plays as written. Each chord after takes the inversion and the octave whose notes
move least from the chord before, counting how far every note moves, and only voicings whose notes
all lie within the range, from the lowest octave to the top of the highest, are tried. With the
root kept in the bass, the chord's lowest written note stays where it is and only the notes above
it are voiced, always above it, as a keyboard player plays beside a bass player. Single notes,
rests and everything but a chord's pitches stay as written, and a chord no voicing fits stays as it
is.
"""

from llamatron.engine.generators.base import ClipGenerator
from llamatron.model.values import midi, sound as sound_values
from llamatron.model.values.chord import movement
from llamatron.model.values.sound import Sound

HALF_STEPS_PER_OCTAVE = 12
# How many octaves either way a voicing is tried from where its chord was written.
OCTAVES_TRIED = 4


class VoiceLeading(ClipGenerator):
    """Voices each chord of a clip nearest the chord before."""

    __slots__ = ('_lowest_octave', '_highest_octave', '_root_in_bass', '_first_before', '_before')

    def __init__(self, *, lowest_octave, highest_octave, root_in_bass=False, continuation=None):
        self._lowest_octave = lowest_octave
        self._highest_octave = highest_octave
        self._root_in_bass = root_in_bass
        # The pitches of the chord before, from the same track's clip before when its Restart carries on.
        self._first_before = None if continuation is None else continuation.state
        self._before = self._first_before

    def end_state(self):
        return self._before

    def _generate(self, clip):
        before = self._first_before
        result = []
        for sound in clip.resolved_sounds():
            chord = sound[sound_values.HELD_SOUND] if sound[sound_values.KIND] == sound_values.HELD else sound
            if chord[sound_values.KIND] != sound_values.CHORD:
                result.append(sound)
                continue
            voiced = chord if before is None else self._voiced(chord=chord, before=before)
            before = sorted(note[sound_values.MIDI] for note in voiced[sound_values.NOTES])
            result.append((sound_values.HELD, sound[sound_values.LENGTH], voiced) if sound[sound_values.KIND] == sound_values.HELD else voiced)
        self._before = before
        return result, clip.get_length()

    def _fits(self, pitches):
        """Return whether a voicing's notes all lie within the range and within MIDI's."""
        lowest = max(self._lowest_octave * HALF_STEPS_PER_OCTAVE, midi.MIN_MIDI_NUMBER)
        highest = min((self._highest_octave + 1) * HALF_STEPS_PER_OCTAVE - 1, midi.MAX_MIDI_NUMBER)
        return all(lowest <= pitch <= highest for pitch in pitches)

    def _voiced(self, *, chord, before):
        """Return a chord voiced nearest the pitches of the chord before it, its notes kept in the order it was built, so that its first is still its root for a grab."""
        order = list(chord[sound_values.NOTES])
        notes = sorted(order, key=lambda note: note[sound_values.MIDI])
        fixed = notes[:1] if self._root_in_bass else []
        moving = notes[1:] if self._root_in_bass else notes
        target = before[1:] if self._root_in_bass and len(before) > 1 else before
        floor = fixed[0][sound_values.MIDI] if fixed else None
        best = None
        for shape in _inversions([note[sound_values.MIDI] for note in moving]):
            for octaves in range(-OCTAVES_TRIED, OCTAVES_TRIED + 1):
                pitches = [pitch + octaves * HALF_STEPS_PER_OCTAVE for pitch in shape]
                if not self._fits(pitches) or (floor is not None and min(pitches) <= floor):
                    continue
                score = (movement(pitches=pitches, before=target), abs(octaves))
                if best is None or score < best[0]:
                    best = (score, pitches)
        if best is None:
            return chord
        moved = [Sound.half_step(note, pitch - note[sound_values.MIDI]) for note, pitch in zip(moving, best[1])]
        voiced = {id(note): placed for note, placed in zip([*fixed, *moving], [*fixed, *moved])}
        return Sound.chord([voiced[id(note)] for note in order])


def _inversions(pitches):
    """Return each inversion of pitches given lowest first, each lining up with the pitches as given: root position, then the lowest one, two and more moved up an octave."""
    return [_lowest_moved_up(pitches=pitches, moved=moved) for moved in range(len(pitches))]


def _lowest_moved_up(*, pitches, moved):
    """Return pitches given lowest first with the lowest so many of them moved up an octave."""
    return [pitch + HALF_STEPS_PER_OCTAVE if place < moved else pitch for place, pitch in enumerate(pitches)]
