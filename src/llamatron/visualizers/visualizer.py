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
"""What every visualizer mode is: a name, and the frame it draws for an area at a moment."""

from llamatron.visualizers.heard import SILENCE
from llamatron.visualizers.pixels import PixelPainter, pixel_size


class Visualizer:
    """One mode of the visualizer, which draws a frame for an area of terminal columns and rows at a moment, in seconds since it began.

    A mode works out only what fits the area it is given, which may change between frames when
    the terminal is resized, so it starts again for an area of another size (resized).
    """

    __slots__ = ('_painter', '_size')

    # What the mode is called on screen and on the command line, and whether it goes dark when nothing plays, as most do.
    NAME = None
    OPTION = None
    DARK_IN_SILENCE = True

    def __init__(self):
        self._painter = PixelPainter()
        self._size = None

    def frame(self, *, width, height, now, heard=SILENCE):
        """Return the lines that draw the frame for an area width columns by height rows, at a moment in seconds, from what it hears (heard.py)."""
        size = pixel_size(width=width, height=height)
        if size != self._size:
            self._size = size
            self.resized(columns=size[0], rows=size[1])
        if not size[0] or not size[1]:
            return []
        return self._painter.lines(pixels=self.pixels(now=now, heard=heard), width=width, height=height)

    @classmethod
    def made_for(cls, *, hidden=()):
        """Return a new mode of this kind, hidden being the names of the modes the set leaves out, which only a mode of modes heeds."""
        return cls()

    def shown_name(self):
        """Return the name of what the mode shows now, which the page shows for a while when it changes: the mode's own, or for a mode of modes, the one showing."""
        return self.NAME

    def resized(self, *, columns, rows):
        """Start again for an area of this many big pixels, columns by rows."""

    def pixels(self, *, now, heard=SILENCE):
        """Return the frame's big pixels at a moment, from what it hears: an array of rows by columns by three channels, red, green and blue, from 0 to 255."""
        raise NotImplementedError
