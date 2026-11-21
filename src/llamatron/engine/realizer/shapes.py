# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shapes as a clip plays: Density thins its notes, Swell scales their velocity, Articulate their length, each by a percentage that ramps over time.

A finished clip's sounds are reshaped after its chains: each
position keeps its place, so a dropped note becomes a rest of the same length, and a lengthened
note is held past its place but never past where the track's next note starts. The percentage at
a moment comes from the shape's start, end, over and then (percent_at). Which shape a clip
follows is the last generator of the kind its chains name, else the clip's own, else its scene's.
How loud a scene and a clip play, their velocity and its ramps in and out, scales every note's
velocity besides (velocity_percent_at), after a Swell generator's.
"""

import math
from typing import NamedTuple

from llamatron.math import length as length_values
from llamatron.math.length import Length
from llamatron.math.rational import Rational
from llamatron.model.schema import defaults
from llamatron.model.schema.file_format import ShapeThen
from llamatron.model.values import midi, sound as sound_values
from llamatron.model.values.sound import Sound

FULL = 100
# How strong a place in the bar is, strongest first: the bar's start, its middle, a beat, an eighth, a sixteenth, anything finer.
BAR_START = 0
BAR_MIDDLE = 1
ON_A_BEAT = 2
ON_AN_EIGHTH = 3
ON_A_SIXTEENTH = 4
FINER = 5
# The density above which a note at each strength plays: the share of a bar of sixteenths the stronger places fill.
PLAYS_ABOVE = {BAR_START: 0, BAR_MIDDLE: Rational(25, 4), ON_A_BEAT: Rational(25, 2), ON_AN_EIGHTH: 25, ON_A_SIXTEENTH: 50}
# A Swell's accent goes on the beats and the stronger places.
ACCENTED = ON_A_BEAT
HALF = 2
QUARTER = 4


class PlacedRamp(NamedTuple):
    """A velocity ramp placed on a clip: the percentages it starts from and reaches, how long it lasts and when it begins, both in whole notes, the time counted from the clip's start."""

    start: int
    end: int
    span: object
    begins: object


class PlacedVelocity(NamedTuple):
    """How loud a clip plays over its time: the percentage that holds, and its ramp in and ramp out, each a PlacedRamp or None."""

    level: int
    ramp_in: object
    ramp_out: object


def velocity_percent_at(*, velocity, time):
    """Return the percentage of its written velocity a note plays at, at a time from its clip's start: inside the ramp in, on its way from start to end; inside the ramp out, the same; and the level anywhere else. Where the two overlap the ramp in wins."""
    ramp = velocity.ramp_in
    if ramp is not None:
        place = time - ramp.begins
        if place < ramp.span:
            return ramp.start + (ramp.end - ramp.start) * place / ramp.span
    ramp = velocity.ramp_out
    if ramp is not None:
        place = time - ramp.begins
        if place >= 0:
            return ramp.start + (ramp.end - ramp.start) * min(place / ramp.span, 1)
    return velocity.level


def percent_at(*, values, time, span):
    """Return a shape's percentage at a time from its start, ramping from start to end over its over (or the whole span), then holding, repeating or bouncing."""
    length = span if values.over is None else Rational(values.over)
    if not length:
        return values.end
    place = time / length
    if values.then == ShapeThen.REPEAT:
        share = place - math.floor(place)
    elif values.then == ShapeThen.BOUNCE:
        lap = place - 2 * math.floor(place / 2)
        share = lap if lap <= 1 else 2 - lap
    else:
        share = min(place, 1)
    return values.start + (values.end - values.start) * share


def strength(*, time, bar, beat):
    """Return how strong a time's place in the bar is, BAR_START the strongest."""
    return strengths(starts=[Length.exact(time)], bar=bar, beat=beat)[0]


def strengths(*, starts, bar, beat):
    """Return how strong each of some starts, pairs in whole notes, is in the bar, BAR_START the strongest.

    Every start is counted in whole-number ticks fine enough for each of them, the bar and its half, the beat, its eighths and its
    sixteenths, so that a place is found by a remainder: a division of fractions for every note was most of reshaping a clip.
    """
    units = (bar, bar / HALF, beat, beat / HALF, beat / QUARTER)
    ticks = math.lcm(*(unit.denominator for unit in units), *(start[1] for start in starts))
    bar_ticks, half_bar, *finer = (unit.numerator * (ticks // unit.denominator) for unit in units)
    levels = tuple(zip((ON_A_BEAT, ON_AN_EIGHTH, ON_A_SIXTEENTH), finer))
    return [_strength_in_ticks(within=Length.ticks_of(start, ticks) % bar_ticks, half_bar=half_bar, levels=levels) for start in starts]


def _strength_in_ticks(*, within, half_bar, levels):
    """Return how strong a place within the bar is, counted in ticks, given the bar's half and each finer level's unit in ticks."""
    if within == 0:
        return BAR_START
    if within == half_bar:
        return BAR_MIDDLE
    for level, unit in levels:
        if within % unit == 0:
            return level
    return FINER


def plays_at(*, density, level):
    """Return whether a note at a place of a strength plays at a density: the strongest places keep playing longest, and everything plays at 100%."""
    return density >= FULL or (level in PLAYS_ABOVE and density > PLAYS_ABOVE[level])


def reshaped(*, sounds, density=None, swell=None, articulate=None, velocity=None, span, bar, beat):
    """Return a clip's sounds reshaped by the shapes given, each (ShapeValues, the span its whole ramp covers, how far into that span the clip starts) or None, and by its velocity, a PlacedVelocity or None.

    span is the clip's length, which a note's lengthening never reaches past.
    """
    starts = []
    now = length_values.ZERO
    for sound in sounds:
        starts.append(now)
        now = Length.add(now, sound[sound_values.LENGTH])
    levels = strengths(starts=starts, bar=bar, beat=beat)
    following = _next_sounding_starts(sounds=sounds, starts=starts) if articulate is not None else None
    result = []
    for place, sound in enumerate(sounds):
        if sound[sound_values.KIND] == sound_values.REST:
            result.append(sound)
            continue
        time = Length.rational(starts[place])
        level = levels[place]
        if density is not None and not plays_at(density=percent_at(values=density[0], time=time + density[2], span=density[1]), level=level):
            result.append(Sound.rest(sound[sound_values.LENGTH]))
            continue
        if swell is not None:
            scale = percent_at(values=swell[0], time=time + swell[2], span=swell[1])
            if level <= ACCENTED:
                scale += swell[0].accent * scale / FULL
            sound = _with_velocity(sound=sound, scale=scale)
        if velocity is not None:
            sound = _with_velocity(sound=sound, scale=velocity_percent_at(velocity=velocity, time=time))
        if articulate is not None:
            room = Length.subtract(Length.exact(span) if following[place] is None else following[place], starts[place])
            result += _with_length(sound=sound, share=percent_at(values=articulate[0], time=time + articulate[2], span=articulate[1]), room=room)
            continue
        result.append(sound)
    return result


def _next_sounding_starts(*, sounds, starts):
    """Return, for each sound, where the next sound that is no rest starts, or None after the last, found in one pass from the end."""
    following = [None] * len(sounds)
    upcoming = None
    for place in range(len(sounds) - 1, -1, -1):
        following[place] = upcoming
        if sounds[place][sound_values.KIND] != sound_values.REST:
            upcoming = starts[place]
    return following


def _rational(number):
    """Return a percentage as a Rational, whether it's a whole number or already one."""
    return number if isinstance(number, Rational) else Rational(number)


def _with_velocity(*, sound, scale):
    """Return a sound with every note's velocity scaled by a percentage, held from 1 to 127."""
    kind = sound[sound_values.KIND]
    if kind == sound_values.NOTE:
        velocity = defaults.DEFAULT_VELOCITY if sound[sound_values.VELOCITY] is None else sound[sound_values.VELOCITY]
        scaled = max(min(round(velocity * scale / FULL), midi.MAX_VELOCITY), midi.MIN_VELOCITY)
        return sound[:sound_values.VELOCITY] + (scaled,) + sound[sound_values.VELOCITY + 1:]
    if kind == sound_values.CHORD:
        return (sound_values.CHORD, sound[sound_values.LENGTH], tuple(_with_velocity(sound=note, scale=scale) for note in sound[sound_values.NOTES]))
    if kind == sound_values.HELD:
        return (sound_values.HELD, sound[sound_values.LENGTH], _with_velocity(sound=sound[sound_values.HELD_SOUND], scale=scale))
    if kind == sound_values.PHRASE:
        return (sound_values.PHRASE, sound[sound_values.LENGTH], tuple(_with_velocity(sound=part, scale=scale) for part in sound[sound_values.PARTS]))
    return sound


def _with_length(*, sound, share, room):
    """Return the positions a sound becomes when it sounds for a share of its written length, held past its place if longer but never past room, the time until the track's next note."""
    if sound[sound_values.KIND] == sound_values.PHRASE:
        return [sound]
    held = sound[sound_values.KIND] == sound_values.HELD
    played = sound[sound_values.HELD_SOUND] if held else sound
    written = played[sound_values.LENGTH] if played[sound_values.KIND] != sound_values.CHORD else Length.longest([note[sound_values.LENGTH] for note in played[sound_values.NOTES]])
    place = sound[sound_values.LENGTH]
    wanted = Length.multiplied(written, Length.of(_rational(share) / FULL))
    lasting = Length.shorter(wanted, room) if Length.less(length_values.ZERO, room) else wanted
    if lasting == place:
        return [Sound.lasting(played, lasting)]
    if Length.less(lasting, place):
        return [Sound.lasting(played, lasting), Sound.rest(Length.subtract(place, lasting))]
    return [Sound.held(Sound.lasting(played, lasting), place)]
