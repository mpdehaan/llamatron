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

"""A scene's tempo ramps worked out: the tempo of every beat of the scene's whole play.

A scene has a ramp in, counted from its first bar, and a ramp out, counted back from its last,
each a tempo it starts from, a tempo it reaches and the bars it takes. The tempo changes at
every step, the song's step size, so that a ramp is a slope and never a stair of bars or beats. Where the two ramps' bars overlap the
ramp in wins, between them the tempo is the scene's own, and neither reaches past the scene.
A ramp in starts at its start and comes to its end on the first step after its bars; a ramp
out leaves its start on its first step and is at its end on the scene's last step.
"""

from typing import NamedTuple

from llamatron.support.rational import Rational

# How finely a tempo inside a ramp is kept: more than any export can write.
TEMPO_PLACES = 4
SCENE_START = Rational(0)
WHOLE_RAMP = 1


class TempoChange(NamedTuple):
    """A tempo a scene takes at a time: the time in whole notes from the scene's start, and the tempo from then on."""

    time: Rational
    tempo: float


def ramped_tempos(*, base, ramp_in, ramp_out, length, bar, step):
    """Return (time, tempo) for each step of a scene's whole play at which the tempo changes, the first at the scene's start.

    base is the tempo with no ramp, each ramp a TempoRamp or None, and length, bar and step are in whole notes.
    """
    in_span = _span(ramp=ramp_in, length=length, bar=bar)
    out_span = _span(ramp=ramp_out, length=length, bar=bar)
    out_from = length - out_span
    tempos = []
    time = SCENE_START
    while time < length or not tempos:
        if ramp_in is not None and time < in_span:
            tempo = _between(ramp=ramp_in, base=base, share=time / in_span)
        elif ramp_out is not None and time >= out_from:
            tempo = _between(ramp=ramp_out, base=base, share=min((time - out_from + step) / out_span, WHOLE_RAMP))
        else:
            tempo = float(base)
        if not tempos or tempos[-1].tempo != tempo:
            tempos.append(TempoChange(time, tempo))
        time += step
    return tempos


def tempos_within(*, tempos, start, end):
    """Return the part of a scene's tempos that one of its rows plays, from start to end, as times counted from the row's start, the first at 0."""
    before = [change.tempo for change in tempos if change.time <= start]
    return [TempoChange(SCENE_START, before[-1])] + [TempoChange(change.time - start, change.tempo) for change in tempos if start < change.time < end]


def _span(*, ramp, length, bar):
    """Return how long a ramp lasts in whole notes, by its bars, or the whole scene for no ramp, which is never read."""
    return length if ramp is None else ramp.over * bar


def _between(*, ramp, base, share):
    """Return the tempo a share of the way through a ramp, a start or an end left blank being the tempo there would have been."""
    start = float(base if ramp.start is None else ramp.start)
    end = float(base if ramp.end is None else ramp.end)
    return round(start + (end - start) * float(share), TEMPO_PLACES)
