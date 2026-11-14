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

"""The ready-made bars of strokes a Guitarify offers: each a name, the length of a cell, the strokes and which of them are accented.

Each bar is a way of playing known by its sound, not a song's part: a strummed folk rhythm, a
country bass and strum, a picked pattern for thumb and fingers, palm-muted chugging, a roll.
"""

from typing import NamedTuple

from llamatron.composition.file_format import ReadyBar, Stroke

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
    ReadyBar.BACKBEAT: GuitarBar(cell=EIGHTH, strokes=(N, N, U, M, N, N, U, M), accents=(O, O, Y, O, O, O, Y, O)),
    ReadyBar.BOOGIE: GuitarBar(cell=EIGHTH, strokes=(D, D, D, D, D, D, D, D), accents=(O, O, Y, O, O, O, Y, O)),
    # A shuffle, the user's choice to offer: each beat a long stroke and a short one, the backbeats accented.
    ReadyBar.SHUFFLE: GuitarBar(cell=TRIPLET, strokes=(D, N, D) * 4, accents=(O, O, O, Y, O, O) * 2),
    ReadyBar.SCRATCH: GuitarBar(cell=SIXTEENTH, strokes=(D, M, M, U, M, M, D, M, M, U, D, M, M, U, M, M), accents=(Y, O, O, O, O, O, Y, O, O, O, Y, O, O, O, O, O)),
    ReadyBar.ALL_DOWN: GuitarBar(cell=EIGHTH, strokes=(D, D, D, D, D, D, D, D), accents=(O, O, O, O, O, O, O, O)),
    # Three strokes a bar left to ring, on the beat, the and of two and the and of three, the user's choice to offer.
    ReadyBar.ARENA: GuitarBar(cell=EIGHTH, strokes=(D, N, N, D, N, D, N, N), accents=(Y, O, O, O, O, O, O, O)),
    ReadyBar.CHUG: GuitarBar(cell=EIGHTH, strokes=(M, M, D, M, M, M, D, M), accents=(O, O, Y, O, O, O, Y, O)),
    ReadyBar.GALLOP: GuitarBar(cell=SIXTEENTH, strokes=(M, N, M, M, M, N, M, M, M, N, M, M, D, N, M, M), accents=(Y, O, O, O, Y, O, O, O, Y, O, O, O, Y, O, O, O)),
    ReadyBar.THRASH: GuitarBar(cell=SIXTEENTH, strokes=(D, M, M, M, M, M, D, M, M, M, D, M, M, M, M, M), accents=(Y, O, O, O, O, O, Y, O, O, O, Y, O, O, O, O, O)),
    ReadyBar.TREMOLO: GuitarBar(cell=SIXTEENTH, strokes=(S1,) * 16, accents=(Y, O, O, O) * 4),
    ReadyBar.CHIME: GuitarBar(cell=EIGHTH, strokes=(S4, S2, S1, S3, S2, S1, S3, S2), accents=(O, O, O, O, O, O, O, O)),
    ReadyBar.ROLL_UP: GuitarBar(cell=EIGHTH, strokes=(B, S4, S3, S2, S1, N, N, N), accents=(O, O, O, O, O, O, O, O)),
    ReadyBar.ROLL_DOWN: GuitarBar(cell=EIGHTH, strokes=(S1, S2, S3, S4, B, N, N, N), accents=(O, O, O, O, O, O, O, O)),
    ReadyBar.HELD: GuitarBar(cell=QUARTER, strokes=(D, N, N, N), accents=(O, O, O, O)),
}
# The bar a new Guitarify plays.
DEFAULT_BAR = ReadyBar.FOLK_STRUM


def ready_bar_matching(*, cell, strokes, accents):
    """Return the name of the ready-made bar that is exactly these cells, or None when they are a bar of someone's own."""
    for name, bar in READY_BARS.items():
        if bar.cell == cell and list(bar.strokes) == list(strokes) and list(bar.accents) == list(accents):
            return name
    return None
