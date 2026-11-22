# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A song's heavy riff: power chords at accents drawn off the beat, muted roots or rests between them, and a tail of single
notes, the third and the seventh flattened where the scale has them major."""

import random
from typing import NamedTuple

from llamatron.wizards.create_song import melody, notation, riffs, wizard_names


def riff_note(*, place, steps, flattened, **more):
    """Return a note of a heavy riff at a place of the ladder, its third and seventh flattened where the scale has them major."""
    degree, octave, *mark = place
    note = {notation.DEGREE: degree, notation.STEPS: steps}
    if octave:
        note[notation.OCTAVE] = octave
    note.update(more)
    if mark or degree in flattened:
        note[notation.ACCIDENTAL] = notation.FLAT
    return note


def is_root(note):
    return note.get(notation.DEGREE) == riffs.HOME[0] and not note.get(notation.OCTAVE) and notation.ACCIDENTAL not in note


def heavy_bar(*, accents, eighths, between, flattened, tail):
    """One bar of a heavy riff: a chord at each accent, lasting to the next place where it can, the root short and quiet
    or a rest at every other place, and the tail's single notes in the bar's last places."""
    bar = []
    body = eighths - len(tail)
    at = 0
    while at < body:
        if at in accents:
            # An accent off the beat rings on through the beat after it, where nothing else starts there.
            steps = 2 if at % 2 and at + 1 < body and at + 1 not in accents else 1
            bar.append(riff_note(place=accents[at], steps=steps, flattened=flattened, **{notation.CHORD: riffs.POWER_CHORD, notation.LEVEL: wizard_names.ACCENT}))
            at += steps
        elif between == riffs.MUTED_ROOTS:
            bar.append(riff_note(place=riffs.HOME, steps=1, flattened=flattened, **{riffs.GATE: riffs.MUTED_GATE, notation.LEVEL: wizard_names.GHOST}))
            at += 1
        else:
            if bar and notation.REST in bar[-1]:
                bar[-1] = {notation.REST: bar[-1][notation.REST] + 1}
            else:
                bar.append({notation.REST: 1})
            at += 1
    return bar + [riff_note(place=place, steps=1, flattened=flattened) for place in tail]


def heavy_line(*, seed, take, eighths, bars=riffs.RIFF_BARS, between=riffs.MUTED_ROOTS, flattened=(), gap=False):
    """Return a song's heavy riff as one line, drawn from the song's seed and the riff's take: the bars alike but for the tail
    the last ends on, and, where a gap is asked of a riff of two bars, the first bar's second half left empty."""
    dice = random.Random(riffs.HEAVY_SEED.format(seed, take))
    tail = dice.choice(riffs.TAILS)
    shape = HeavyShape(eighths=eighths, between=between, flattened=flattened, bars=bars, gap=gap)
    # The accents fall in the same places of every bar; the last bar's give way to the tail.
    offbeats = [place for place in range(1, eighths) if place % 2]
    ladder = _accent_ladder()
    # The accents that are left once the last bar's tail, and the gap, have taken their places.
    limit = eighths - len(tail)
    if gap and bars > 1:
        limit = eighths // 2
    kept = [place for place in offbeats if place < limit]
    for _ in range(riffs.TRIES):
        accents = _drawn_accents(dice=dice, offbeats=offbeats, ladder=ladder)
        line = _heavy_bars(shape=shape, accents=accents, tail=tail)
        if _accents_heard(line=line, accents=accents, kept=kept):
            return line
    # An accent off the beat that is sure to be heard, and every accent on the root, which half the notes or more then are.
    sure = {place: riffs.HOME for place in (0, kept[0], *accents)}
    return _heavy_bars(shape=shape, accents=sure, tail=tail)


class HeavyShape(NamedTuple):
    """The shape of a heavy riff, the same for every try at its accents: how many eighths a bar has, what is played between
    the accents, the degrees flattened, how many bars, and whether the first bar leaves a gap for the voice."""
    eighths: int
    between: str
    flattened: tuple
    bars: int
    gap: bool


def _accent_ladder():
    """Return the places of the ladder an accent may take, each as often as its share."""
    ladder = []
    for place, share in riffs.ACCENT_LADDER:
        ladder.extend([place] * share)
    return ladder


def _drawn_accents(*, dice, offbeats, ladder):
    """Return a try at a riff's accents: home on the first eighth, and a few eighths off the beat drawn, each at a place of the ladder."""
    count = dice.randint(min(riffs.FEWEST_ACCENTS, len(offbeats)), min(riffs.MOST_ACCENTS, len(offbeats)))
    places = sorted(dice.sample(offbeats, count))
    accents = {0: riffs.HOME}
    for place in places:
        accents[place] = dice.choice(ladder)
    return accents


def _heavy_bars(*, shape, accents, tail):
    """Return the bars of a heavy riff with its accents: the last ends on the tail, and the first, in a riff of two bars, may leave a gap."""
    last = heavy_bar(accents=accents, eighths=shape.eighths, between=shape.between, flattened=shape.flattened, tail=tail)
    if shape.bars == 1:
        return last
    first = heavy_bar(accents=accents, eighths=shape.eighths, between=shape.between, flattened=shape.flattened, tail=())
    if shape.gap:
        first = riffs.with_gap(bar=first, eighths=shape.eighths)
    return first + last


def _accents_heard(*, line, accents, kept):
    """Return whether a try at a riff is heard as one: an accent off the beat where the tail and the gap leave room, and half
    the notes or more on the root."""
    heard = False
    for place in kept:
        if place in accents:
            heard = True
    if not heard:
        return False
    sounding = [note for note in line if notation.REST not in note]
    roots = 0
    for note in sounding:
        if is_root(note):
            roots += 1
    return 2 * roots >= len(sounding)


def flattened_in(scale_type):
    """Return the degrees a heavy riff flattens over a scale: the third and the seventh where the scale has them major."""
    steps = melody.HALF_STEPS.get(scale_type, melody.HALF_STEPS[melody.MAJOR])
    major = melody.HALF_STEPS[melody.MAJOR]
    flattened = []
    for degree in riffs.FLATTENED:
        if steps[degree - 1] == major[degree - 1]:
            flattened.append(degree)
    return tuple(flattened)
