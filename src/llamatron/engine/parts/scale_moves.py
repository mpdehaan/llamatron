# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A note moved along a scale, which the pattern player's chords and several generators share."""

from llamatron.model.values import sound
from llamatron.model.values.sound import Sound
from llamatron.music_theory.fundamentals import intervals


def along_scale(*, note, steps, scale):
    """Return a note, as a sound, moved a number of notes along a scale, or by half steps without one.

    A note that isn't in the scale keeps its distance from the scale note below it.
    """
    if not steps:
        return note
    if scale is None:
        return Sound.half_step(note, steps)
    shape = scale.get_type().value
    above_root = note[sound.MIDI] - scale.get_root().get_midi_number()
    octaves, within = divmod(above_root, intervals.HALF_STEPS_PER_OCTAVE)
    place = _scale_note_at_or_below(shape=shape, half_steps=within)
    extra = within - shape[place]
    more, place = divmod(place + steps, len(shape))
    return Sound.half_step(note, (octaves + more) * intervals.HALF_STEPS_PER_OCTAVE + shape[place] + extra - above_root)


def _scale_note_at_or_below(*, shape, half_steps):
    """Return which note of a scale's octave, counted from 0, is at or just below some half steps above its root."""
    return max(index for index, step in enumerate(shape) if step <= half_steps)
