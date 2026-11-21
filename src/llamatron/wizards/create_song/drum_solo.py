# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A drum solo: the drummer alone for a section, written as a solo is built.

It states a short theme on the snare over the kick, moves the theme round the toms and off the beat, builds as the strokes
come twice as often, peaks in a run round the kit, and in its last bar goes back to the beat and plays the band in. The
theme is drawn from the song's seed, so the same song has the same solo.
"""

import random

from llamatron.wizards.create_song import notation

KICK = 'kick'
SNARE = 'snare'
TOM_HIGH = 'tom high'
TOM_LOW = 'tom low'
CRASH = 'crash'
PIECES = (KICK, SNARE, TOM_HIGH, TOM_LOW, CRASH)
# A bar's steps, sixteenths in four, and what a solo's dice are seeded by.
GRID = 16
STEP = '1/16'
SOLO_SEED = '{} drum solo'
# The parts of a solo, as shares of its bars: the theme, the theme moved about, the build; the bar before the last is the peak.
THEME_SHARE = 0.25
MOVED_SHARE = 0.5
# The eighths a theme's strokes may fall on, how many it has, and the strokes it always has: the first beat and the backbeats.
THEME_PLACES = (0, 2, 3, 4, 6, 7, 8, 10, 11, 12, 14)
THEME_STROKES = 5
THEME_ALWAYS = (0, 4, 12)
BEATS = (0, 4, 8, 12)
HALF_BAR = 8
EIGHTH = 2
QUARTER = 4
# The toms a moved theme goes round, the strokes of the last bar's fill and the pieces a run goes round, a beat each.
RUN = (SNARE, TOM_HIGH, TOM_LOW, SNARE)
CUE_BEAT = (0, 4)
CUE_FILL = {SNARE: (8, 9, 10), TOM_HIGH: (11, 12), TOM_LOW: (13, 14, 15)}


def theme_of(dice):
    """A theme: the sixteenths of a bar its strokes fall on."""
    free = [place for place in THEME_PLACES if place not in THEME_ALWAYS]
    return sorted(set(THEME_ALWAYS) | set(dice.sample(free, THEME_STROKES - len(THEME_ALWAYS))))


def empty_bar():
    return {piece: [notation.NONE] * GRID for piece in PIECES}


def theme_bar(*, theme, answered):
    """The theme on the snare over a kick on one and three; answered, its second half is on the high tom."""
    bar = empty_bar()
    for place in theme:
        bar[TOM_HIGH if answered and place >= HALF_BAR else SNARE][place] = notation.LOUD
    for place in (BEATS[0], BEATS[2]):
        bar[KICK][place] = notation.LOUD
    return bar


def moved_bar(*, theme, late):
    """The theme round the toms, high in the bar's first half and low in its second, and, late, an eighth off the beat."""
    bar = empty_bar()
    for place in theme:
        at = (place + EIGHTH) % GRID if late else place
        bar[TOM_HIGH if at < HALF_BAR else TOM_LOW][at] = notation.LOUD
    for place in BEATS:
        bar[KICK][place] = notation.LOUD
    return bar


def build_bar(*, theme, fast):
    """The snare on every eighth, or every sixteenth, loud on the theme's strokes and soft between, over a kick on every beat."""
    bar = empty_bar()
    for place in range(0, GRID, 1 if fast else EIGHTH):
        bar[SNARE][place] = notation.LOUD if place in theme else notation.SOFT
    for place in BEATS:
        bar[KICK][place] = notation.LOUD
    return bar


def peak_bar():
    """A run of sixteenths round the kit, a beat on each piece, a crash on the first."""
    bar = empty_bar()
    for beat, piece in enumerate(RUN):
        for place in range(beat * QUARTER, (beat + 1) * QUARTER):
            bar[piece][place] = notation.LOUD
    bar[CRASH][0] = notation.LOUD
    bar[KICK][0] = notation.LOUD
    bar[KICK][HALF_BAR] = notation.LOUD
    return bar


def cue_bar():
    """The beat again for half a bar, then a fill down the toms that plays the band in."""
    bar = empty_bar()
    bar[KICK][CUE_BEAT[0]] = notation.LOUD
    bar[SNARE][CUE_BEAT[1]] = notation.LOUD
    for piece, places in CUE_FILL.items():
        for place in places:
            bar[piece][place] = notation.LOUD
    return bar


def solo_bars(*, bars, seed):
    """A solo of so many bars, each bar the hits of every piece."""
    theme = theme_of(random.Random(SOLO_SEED.format(seed)))
    made = []
    for count in range(bars):
        through = count / bars
        if count == bars - 1:
            made.append(cue_bar())
        elif count == bars - 2 and bars > 2:
            made.append(peak_bar())
        elif through < THEME_SHARE:
            made.append(theme_bar(theme=theme, answered=count % 2 == 1))
        elif through < MOVED_SHARE:
            made.append(moved_bar(theme=theme, late=count % 2 == 1))
        else:
            made.append(build_bar(theme=theme, fast=count % 2 == 1 or through >= (THEME_SHARE + MOVED_SHARE)))
    return made


def solo_hits(*, bars, seed):
    """A solo as each piece's hits through the whole section, a piece that never sounds left out."""
    made = solo_bars(bars=bars, seed=seed)
    hits = {piece: _hits_through(bars=made, piece=piece) for piece in PIECES}
    return {piece: played for piece, played in hits.items() if _sounds(played)}


def _hits_through(*, bars, piece):
    """Return a piece's hits through every bar of the solo."""
    return [hit for bar in bars for hit in bar[piece]]


def _sounds(hits):
    """Return whether any of a piece's hits sounds."""
    return any(hit != notation.NONE for hit in hits)
