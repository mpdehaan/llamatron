# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The drums of a section as the song wizard writes them: each piece of the kit a part some bars long, the kind's own bar
decorated as the drummer decorates it, varied bar by bar through each phrase, and ended on a fill, a join's tail or a marker."""

import math
import random
from typing import NamedTuple

from llamatron.music_theory.composing import joins, notation
from llamatron.music_theory.composing.joins import drum_tail, pieces_of_tail
from llamatron.music_theory.composing.loudness import drum_levels
from llamatron.wizards.create_song import arranger, characters
from llamatron.wizards.create_song.arranger import break_of, choice_that_fits, cut_of, fill_named, laid_over, step_of, struck, values_of, widened
from llamatron.wizards.create_song.breaks import cut_up


class SongDrumming(NamedTuple):
    """What every section's drums are written from: the style, the band's roles, the meter, how many bars a phrase has, the
    song's seed, what each piece of the kit is played as, and whether the song chose its own fill."""
    style: dict
    roles: list
    meter: str
    phrase_bars: int
    seed: int = 0
    kit: dict = None
    own_fill: bool = False


class SectionToDrum(NamedTuple):
    """What a section asks of the drums: the picks that hold in it, how the drummer plays, how many bars it has, what it leaves
    with where it says, the fill and marker inside it, and bars given to a piece of their own."""
    picks: dict
    drummer: dict
    bars: int
    leaves: dict = None
    inside: dict = None
    over: dict = None


class SectionDrums:
    """Each drum a section's picks play, as a part some bars long: the kind's own bar, decorated as the drummer decorates it,
    a bar of the bars of each phrase that the drummer varies each a little different, and its last bar the fill. A drummer
    who says nothing plays the kind's bar and the song's fill at the end of every phrase. Where the picks name a break, the
    break's bar is the kind's, in place of every way but the percussion's, and each bar of a phrase after the first is the
    break cut up, its own way, by the seed.

    A section that says what it leaves with is written out whole: its last bar is the join's fill under the join's tail, and
    the small fill inside comes only as often as the section says.

    Bars given to a piece of their own, bar by bar of the section and round again, as a kick that follows a riff, are played
    as given, in place of the kind's bar and all the drummer adds to it, and a bar given as None is the kind's."""

    __slots__ = ('_drumming', '_asked', '_over', '_bars', '_cut_bars', '_length', '_fill_every', '_fill', '_silences',
                 '_last_fill', '_tail', '_inside_every', '_marker', '_marker_every', '_adds', '_varied', '_layers')

    def __init__(self, *, drumming, asked):
        self._drumming = drumming
        self._asked = asked
        self._over = asked.over or {}
        self._bars, self._cut_bars = self._kind_bars()
        self._length, self._fill_every = self._lengths()
        self._fill, self._silences, self._last_fill = self._fills()
        inside = asked.inside or {}
        leaves = asked.leaves or {}
        self._tail = leaves.get(joins.TAIL)
        self._inside_every = inside.get(arranger.FILL_INSIDE_EVERY) or self._length
        # A marker is a stroke or two laid over a phrase's last bar where no fill is played.
        self._marker = {}
        if asked.leaves is not None:
            self._marker = inside.get(arranger.MARKER) or {}
        self._marker_every = inside.get(arranger.MARKER_EVERY) or self._length
        self._adds, _ = choice_that_fits(choices=asked.drummer.get(characters.ADDS), picks=asked.picks)
        self._varied = self._variations()
        self._layers = self._every_layer()

    def _kind_bars(self):
        """Return the kind's own bar of each drum, a break's in place of all but what is kept beside one, and each bar of a
        phrase after the first that cuts the break up."""
        drumming = self._drumming
        picks = self._asked.picks
        bars = {}
        played_break = break_of(picks=picks, meter=drumming.meter)
        for role in drumming.roles:
            for trait in role.get(arranger.DRUMS, []):
                if played_break is None or trait == arranger.KEPT_BESIDE_A_BREAK:
                    ways = values_of(style=drumming.style, trait=trait)
                    bars.update(ways[picks[trait]].get(arranger.BAR, {}))
        cut_bars = {}
        if played_break is not None:
            bars.update(played_break)
            cut = cut_of(picks)
            for count in range(1, drumming.phrase_bars):
                dice = random.Random(arranger.CUT_SEED.format(drumming.seed, count))
                cut_bars[count] = cut_up(bars=played_break, cut=cut, dice=dice)
        return bars, cut_bars

    def _lengths(self):
        """Return how many bars the part lasts and how often its fill comes: the part no longer than divides the section, so
        that a section always ends on the fill, or the whole section where bars are given one by one or the section is planned."""
        asked = self._asked
        phrase_bars = self._drumming.phrase_bars
        length = math.gcd(asked.drummer.get(characters.FILL_EVERY, phrase_bars) or phrase_bars, asked.bars)
        fill_every = length
        if self._over:
            length = asked.bars
        if asked.leaves is not None:
            length = asked.bars
            fill_every = length
        return length, fill_every

    def _fills(self):
        """Return the fill the section plays, the drums it leaves silent there, and the fill of its last bar: in a planned
        section, the small fill the section names and the join's; else the drummer's, or the song's own, or none."""
        asked = self._asked
        style = self._drumming.style
        if asked.leaves is not None:
            inside = asked.inside or {}
            fill = fill_named(style=style, name=inside.get(arranger.FILL_INSIDE))
            return fill, [], fill_named(style=style, name=asked.leaves.get(joins.FILL_OF_JOIN))
        fill, silences = choice_that_fits(choices=asked.drummer.get(characters.FILL), picks=asked.picks)
        if not fill or self._drumming.own_fill:
            # The fill the song chose itself is played whatever the drummer would play, a song that chose none having none.
            fills = values_of(style=style, trait=arranger.FILLS)
            chosen = fills.get(asked.picks.get(arranger.FILLS), {})
            fill = chosen.get(characters.FILL, {})
            silences = []
        if asked.drummer.get(characters.FILL_EVERY) == 0:
            fill = {}
            silences = []
        return fill, silences, {}

    def _variations(self):
        """Return how the drummer varies some bars of each phrase: the bars, and the strokes laid over them."""
        varied = []
        for variation in self._asked.drummer.get(characters.VARIES, []):
            more, _ = choice_that_fits(choices=variation[arranger.CHOICES], picks=self._asked.picks)
            varied.append((variation[arranger.BARS], more))
        return varied

    def _every_layer(self):
        """Return every layer of strokes a drum may play in the section: the kind's bar, what the drummer adds, the fills, the
        marker, the rests a tail asks for, each variation and each bar given to a piece of its own."""
        tail_rests = {piece: [notation.NONE] for piece in pieces_of_tail(self._tail)}
        layers = [self._bars, self._adds, self._fill, self._last_fill, self._marker, tail_rests]
        for _, more in self._varied:
            layers.append(more)
        for piece, given_bars in self._over.items():
            for given in given_bars:
                if given is not None:
                    layers.append({piece: given})
        return layers

    def parts(self):
        """Return each drum's part, by the drum, in the order the drums first come in the layers."""
        parts = {}
        for layer in self._layers:
            for piece in layer:
                if piece not in parts:
                    parts[piece] = self._piece_part(piece)
        return parts

    def _piece_part(self, piece):
        """Return one drum's part: its hits bar by bar, on a grid fine enough for every layer it plays, at its levels."""
        lengths = [len(layer[piece]) for layer in self._layers if piece in layer]
        grid = math.lcm(*lengths)
        plain = widened(hits=self._bars.get(piece, [notation.NONE]), to=grid)
        plain = self._with_adds(piece=piece, played=plain, grid=grid)
        hits = []
        for bar in range(1, self._length + 1):
            hits += self._bar_hits(piece=piece, bar=bar, grid=grid, plain=plain)
        drumming = self._drumming
        loudness = drumming.style[arranger.LOUDNESS]
        # A style as written says a drum's normal stroke alone, and a song's style all four levels.
        levels = drum_levels(loudness.get(piece, loudness[arranger.DRUMS]))
        kit = drumming.kit or {}
        part = {notation.DRUM: kit.get(piece, piece), notation.STEP: step_of(meter=drumming.meter, grid=grid)}
        part.update(struck(levels=levels, hits=hits))
        part[notation.HITS] = hits
        return part

    def _with_adds(self, *, piece, played, grid):
        """Return a bar with what the drummer adds to a drum laid over it."""
        if piece not in self._adds:
            return played
        more = widened(hits=self._adds[piece], to=grid)
        return laid_over(bar=played, more=more)

    def _bar_hits(self, *, piece, bar, grid, plain):
        """Return a drum's hits in one bar of the part: the fill, or silence, at each fill's bar of a section that is not
        planned, and otherwise the bar as played."""
        if self._asked.leaves is None and bar % self._fill_every == 0:
            if piece in self._fill:
                return widened(hits=self._fill[piece], to=grid)
            if piece in self._silences:
                return [notation.NONE] * grid
        return self._bar_played(piece=piece, bar=bar, grid=grid, plain=plain)

    def _bar_played(self, *, piece, bar, grid, plain):
        """Return a bar a drum plays between fills: a bar given of its own, or the break cut up, or the kind's bar with what
        the drummer adds, varied as the drummer varies the phrase's bars, then ended as the section asks."""
        phrase_bar = (bar - 1) % self._drumming.phrase_bars
        own = None
        if piece in self._over:
            given_bars = self._over[piece]
            own = given_bars[(bar - 1) % len(given_bars)]
        played = plain
        if own is not None:
            played = widened(hits=own, to=grid)
        elif piece in self._cut_bars.get(phrase_bar, {}):
            cut = widened(hits=self._cut_bars[phrase_bar][piece], to=grid)
            played = self._with_adds(piece=piece, played=cut, grid=grid)
        if own is None:
            played = self._varied_bar(piece=piece, phrase_bar=phrase_bar, grid=grid, played=played)
        return self._bar_ended(piece=piece, bar=bar, grid=grid, played=played)

    def _varied_bar(self, *, piece, phrase_bar, grid, played):
        """Return a bar with each variation of the drummer's laid over it that falls on the bar's place in the phrase."""
        for which, more in self._varied:
            if piece in more and phrase_bar + 1 in which:
                varied = widened(hits=more[piece], to=grid)
                played = laid_over(bar=played, more=varied)
        return played

    def _bar_ended(self, *, piece, bar, grid, played):
        """Return a bar as the section ends it: a planned section's last bar under the join's tail or its fill, the small fill
        inside as often as the section says, and a marker laid over a phrase's last bar where no fill is played."""
        leaves = self._asked.leaves
        last = bar == self._length
        if leaves is not None and last and self._tail is not None:
            return drum_tail(piece=piece, plain=played, tail=self._tail, eighths=leaves.get(joins.TAIL_EIGHTHS, 0))
        if leaves is not None and last and piece in self._last_fill:
            return widened(hits=self._last_fill[piece], to=grid)
        if leaves is not None and not last and bar % self._inside_every == 0 and piece in self._fill:
            return widened(hits=self._fill[piece], to=grid)
        if not last and bar % self._marker_every == 0 and bar % self._inside_every != 0 and piece in self._marker:
            marker = widened(hits=self._marker[piece], to=grid)
            return laid_over(bar=played, more=marker)
        return played
