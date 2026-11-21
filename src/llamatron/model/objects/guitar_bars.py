# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The ready-made bars of strokes a Guitarify offers: each a name, the length of a cell, the strokes and which of them are accented.

Each bar is a way of playing known by its sound, not a song's part: a strummed folk rhythm, a
country bass and strum, a picked pattern for thumb and fingers, palm-muted chugging, a roll.
A bar may run longer than one bar of the song: its cells are counted, not its bars.
"""

from typing import NamedTuple

from llamatron.model.vocabulary.file_format import ReadyBar, Stroke

EIGHTH = '1/8'
SIXTEENTH = '1/16'
QUARTER = '1/4'
# A third of a beat, for a bar of triplets.
TRIPLET = '1/12'


class GuitarBar(NamedTuple):
    """One bar of strokes: how long a cell lasts, as a file writes a length, the stroke of each cell, and whether each is accented."""

    cell: str
    strokes: tuple
    accents: tuple


N = Stroke.NOTHING
D = Stroke.DOWN
U = Stroke.UP
M = Stroke.MUTE
S = Stroke.STAB
L = Stroke.MUTED_BASS
B = Stroke.BASS
A = Stroke.ALT_BASS
S1 = Stroke.STRING_1
S2 = Stroke.STRING_2
S3 = Stroke.STRING_3
S4 = Stroke.STRING_4
Y = True
O = False

READY_BARS = {
    ReadyBar.FOLK_STRUM: GuitarBar(cell=EIGHTH, strokes=(D, N, D, U, N, U, D, U), accents=(Y, O, O, O, O, O, Y, O)),
    ReadyBar.BOOM_CHICK: GuitarBar(cell=EIGHTH, strokes=(B, N, D, N, A, N, D, N), accents=(Y, O, O, O, Y, O, O, O)),
    ReadyBar.TRAVIS_PICK: GuitarBar(cell=EIGHTH, strokes=(B, S2, A, S1, B, S3, A, S2), accents=(O, O, O, O, O, O, O, O)),
    ReadyBar.CROSSPICK: GuitarBar(cell=EIGHTH, strokes=(S3, S2, S1, S3, S2, S1, S3, S2), accents=(Y, O, O, Y, O, O, Y, O)),
    ReadyBar.FOUR_TO_THE_BAR: GuitarBar(cell=QUARTER, strokes=(D, D, D, D), accents=(O, Y, O, Y)),
    # A short chord on beats two and four, and silence between.
    ReadyBar.BACKBEAT: GuitarBar(cell=EIGHTH, strokes=(N, N, S, N, N, N, S, N), accents=(O, O, Y, O, O, O, Y, O)),
    ReadyBar.BOOGIE: GuitarBar(cell=EIGHTH, strokes=(D, D, D, D, D, D, D, D), accents=(O, O, Y, O, O, O, Y, O)),
    # A shuffle: each beat a long stroke and a short one, the backbeats accented.
    ReadyBar.SHUFFLE: GuitarBar(cell=TRIPLET, strokes=(D, N, D) * 4, accents=(O, O, O, Y, O, O) * 2),
    ReadyBar.SCRATCH: GuitarBar(cell=SIXTEENTH, strokes=(D, M, M, U, M, M, D, M, M, U, D, M, M, U, M, M), accents=(Y, O, O, O, O, O, Y, O, O, O, Y, O, O, O, O, O)),
    ReadyBar.ALL_DOWN: GuitarBar(cell=EIGHTH, strokes=(D, D, D, D, D, D, D, D), accents=(O, O, O, O, O, O, O, O)),
    # Three strokes a bar left to ring, on the beat, the and of two and the and of three.
    ReadyBar.ARENA: GuitarBar(cell=EIGHTH, strokes=(D, N, N, D, N, D, N, N), accents=(Y, O, O, O, O, O, O, O)),
    # The low string muted, the chord on the backbeats.
    ReadyBar.CHUG: GuitarBar(cell=EIGHTH, strokes=(L, L, D, L, L, L, D, L), accents=(O, O, Y, O, O, O, Y, O)),
    ReadyBar.GALLOP: GuitarBar(cell=SIXTEENTH, strokes=(L, N, L, L, L, N, L, L, L, N, L, L, D, N, L, L), accents=(Y, O, O, O, Y, O, O, O, Y, O, O, O, Y, O, O, O)),
    ReadyBar.THRASH: GuitarBar(cell=SIXTEENTH, strokes=(D, L, L, L, L, L, D, L, L, L, D, L, L, L, L, L), accents=(Y, O, O, O, O, O, Y, O, O, O, Y, O, O, O, O, O)),
    ReadyBar.TREMOLO: GuitarBar(cell=SIXTEENTH, strokes=(S1,) * 16, accents=(Y, O, O, O) * 4),
    ReadyBar.CHIME: GuitarBar(cell=EIGHTH, strokes=(S4, S2, S1, S3, S2, S1, S3, S2), accents=(O, O, O, O, O, O, O, O)),
    ReadyBar.ROLL_UP: GuitarBar(cell=EIGHTH, strokes=(B, S4, S3, S2, S1, N, N, N), accents=(O, O, O, O, O, O, O, O)),
    ReadyBar.ROLL_DOWN: GuitarBar(cell=EIGHTH, strokes=(S1, S2, S3, S4, B, N, N, N), accents=(O, O, O, O, O, O, O, O)),
    ReadyBar.HELD: GuitarBar(cell=QUARTER, strokes=(D, N, N, N), accents=(O, O, O, O)),
    # A short chord on every off-beat.
    ReadyBar.SKANK: GuitarBar(cell=EIGHTH, strokes=(N, S, N, S, N, S, N, S), accents=(O, O, O, O, O, O, O, O)),
    # Sixteenths scratched, three of them a short chord let sound.
    ReadyBar.DISCO: GuitarBar(cell=SIXTEENTH, strokes=(M, M, S, M, M, M, M, S, M, M, S, M, M, M, M, M), accents=(O, O, Y, O, O, O, O, Y, O, O, Y, O, O, O, O, O)),
    # The low string muted in eighths under three chords.
    ReadyBar.PEDAL_RIFF: GuitarBar(cell=EIGHTH, strokes=(D, L, L, D, L, L, D, L), accents=(Y, O, O, Y, O, O, Y, O)),
    # Two bars of the low string with rests, the short chords pushed ahead of the beats and across the bar line.
    # Three hits and then two, on one chord.
    ReadyBar.FIVE_BEAT: GuitarBar(cell=SIXTEENTH, strokes=(D, N, N, D, N, N, D, N, N, N, D, N, D, N, N, N), accents=(O,) * 16),
    # Strums with a muted stroke between each, like a clock.
    ReadyBar.STRUM_AND_CLICK: GuitarBar(cell=EIGHTH, strokes=(D, M, U, M, D, M, U, M), accents=(Y, O, O, O, Y, O, O, O)),
    # A chord picked slowly, one string at a time, from the bass.
    ReadyBar.SLOW_PICK: GuitarBar(cell=EIGHTH, strokes=(B, S3, S2, S3, S1, S3, S2, S3), accents=(O,) * 8),
    ReadyBar.FOUR_STOMPS: GuitarBar(cell=QUARTER, strokes=(D, D, D, D), accents=(Y, O, Y, O)),
    ReadyBar.POWER_GROOVE: GuitarBar(
        cell=SIXTEENTH,
        strokes=(L, N, N, L, N, N, S, N, L, N, L, N, N, L, N, S, N, N, L, N, L, N, N, S, N, L, N, L, S, N, L, L),
        accents=(O, O, O, O, O, O, Y, O, O, O, O, O, O, O, O, Y, O, O, O, O, O, O, O, Y, O, O, O, O, Y, O, O, O),
    ),
}
# The bar a new Guitarify plays.
DEFAULT_BAR = ReadyBar.FOLK_STRUM


def ready_bar_matching(*, cell, strokes, accents):
    """Return the name of the ready-made bar that is exactly these cells, or None when they are a bar of someone's own."""
    for name, bar in READY_BARS.items():
        if bar.cell == cell and list(bar.strokes) == list(strokes) and list(bar.accents) == list(accents):
            return name
    return None
