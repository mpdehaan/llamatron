# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A bar that shows how long something lasts against something longer, in character cells.

The Arrange page draws one under each scene, against the longest scene, and under each clip,
against its scene, so that how the parts of a song fit together can be seen without reading the
times. The bar fills from the left in eighths of a cell, and the rest is hatched or blank.
"""

from llamatron.tui import drawing


FULL_BLOCK = '█'
HATCHING = '░'
# What is still to play of a scene's bar while it plays, the read head having filled the bar up to where the scene is.
TO_PLAY = '▒'
# The left-aligned partial blocks, from an eighth of a cell to seven eighths.
PARTIAL_BLOCKS = '▏▎▍▌▋▊▉'
EIGHTHS = 8


class LengthBar:
    """Draws lengths as bars of one width, hatched or blank where the bar doesn't reach."""

    __slots__ = ('_width', '_hatched')

    def __init__(self, *, width, hatched):
        self._width = width
        self._hatched = hatched

    def get_width(self):
        return self._width

    def blank(self):
        """Return the bar for a length that can't be worked out: nothing drawn."""
        return drawing.SPACE * self._width

    def full(self):
        return FULL_BLOCK * self._width

    def draw(self, *, amount, total, played=None):
        """Return the bar for an amount of a total, which fills the width when they're equal, or blank when either is unknown.

        With played, the seconds of the amount played so far, the bar is a read head: full up to
        where the amount is, and the rest of the amount shaded, so that a playing scene's bar fills
        from the left as it plays.
        """
        if amount is None or total is None or not total:
            return self.blank()
        bar = self._filled(amount=amount, total=total)
        if played is not None:
            head = self._filled(amount=min(max(played, 0), amount), total=total)
            bar = head + TO_PLAY * (len(bar) - len(head))
        return bar + (HATCHING if self._hatched else drawing.SPACE) * (self._width - len(bar))

    def _filled(self, *, amount, total):
        """Return the blocks for an amount of the total, the last one partial."""
        eighths = min(round(amount * self._width * EIGHTHS / total), self._width * EIGHTHS)
        whole, part = divmod(eighths, EIGHTHS)
        return FULL_BLOCK * whole + (PARTIAL_BLOCKS[part - 1] if part else drawing.NOTHING)
