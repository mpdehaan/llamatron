# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""What every visualizer mode is: a name, and the frame it draws for an area at a moment."""

from llamatron.interface.visualizers import heard as heard_values
from llamatron.interface.visualizers.pixels import pixel_lines, pixel_size

# The longest a frame is taken to have lasted, in seconds, however late it comes.
LONGEST_FRAME_SECONDS = 0.2


class Visualizer:
    """One mode of the visualizer, which draws a frame for an area of terminal columns and rows at a moment, in seconds since it began.

    A mode works out only what fits the area it is given, which may change between frames when
    the terminal is resized, so it starts again for an area of another size (resized).
    """

    __slots__ = ('_size', '_last')

    # What the mode is called on screen and on the command line, and whether it goes dark when nothing plays, as most do.
    NAME = None
    OPTION = None
    DARK_IN_SILENCE = True

    def __init__(self):
        self._size = None
        self._last = None

    def frame(self, *, width, height, now, heard=heard_values.SILENCE):
        """Return the lines that draw the frame for an area width columns by height rows, at a moment in seconds, from what it hears (heard.py): none for an area with no room."""
        if not width or not height:
            return []
        return self.frame_of(width=width, height=height, now=now, heard=heard)

    def frame_of(self, *, width, height, now, heard):
        """Return the lines that draw the frame for an area that has room: the mode's big pixels painted, unless a mode draws its own lines."""
        size = pixel_size(width=width, height=height)
        if size != self._size:
            self._size = size
            self.resized(columns=size[0], rows=size[1])
        if not size[0] or not size[1]:
            return []
        return pixel_lines(pixels=self.pixels(now=now, heard=heard), width=width, height=height)

    @classmethod
    def made_for(cls, *, hidden=()):
        """Return a new mode of this kind, hidden being the names of the modes the set leaves out, which only a mode of modes heeds."""
        return cls()

    def shown_name(self):
        """Return the name of what the mode shows now, which the page shows for a while when it changes: the mode's own, or for a mode of modes, the one showing."""
        return self.NAME

    def seconds_since_last_frame(self, now):
        """Return the seconds from the frame before this one to now, none for the first frame and never more than LONGEST_FRAME_SECONDS, and take now as the last frame's moment.

        A frame that comes late, as after the page was covered, moves the picture on as one long frame would and no further, so that nothing jumps.
        """
        seconds = 0.0 if self._last is None else min(max(now - self._last, 0.0), LONGEST_FRAME_SECONDS)
        self._last = now
        return seconds

    def resized(self, *, columns, rows):
        """Start again for an area of this many big pixels, columns by rows."""

    def pixels(self, *, now, heard=heard_values.SILENCE):
        """Return the frame's big pixels at a moment, from what it hears: an array of rows by columns by three channels, red, green and blue, from 0 to 255."""
        raise NotImplementedError
