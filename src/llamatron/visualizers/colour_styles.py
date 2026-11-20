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

"""The styles that draw a colour in a visualizer or a view, each made once and kept for good: a frame asks for the style of every
cell, a style depends on its colours alone, and a mode draws with a palette of colours it comes back to frame after frame."""

import functools
from rich.color import Color
from rich.style import Style

@functools.cache
def rgb_style(colour):
    """Return the style that draws a colour, an (r, g, b) of 0 to 255, on the terminal's own background."""
    return Style(color=Color.from_rgb(*colour))


@functools.cache
def colour_style(*, colour, background=None):
    """Return the style that draws a colour, an (r, g, b) of 0 to 255 or None for the terminal's own, on a background colour or the
    terminal's own."""
    return Style(color=Color.from_rgb(*colour) if colour else None, bgcolor=Color.from_rgb(*background) if background else None)


@functools.cache
def packed_style(number):
    """Return the style that draws a colour packed as one number, which is looked up faster than three, on the terminal's own background."""
    return Style(color=Color.from_rgb(*unpacked(number)))


@functools.cache
def packed_style_on(*, number, background):
    """Return the style that draws a colour packed as one number on a packed background."""
    return Style(color=Color.from_rgb(*unpacked(number)), bgcolor=Color.from_rgb(*unpacked(background)))


def unpacked(number):
    """Return a colour packed as one number as red, green and blue."""
    return (number >> 16) & 0xFF, (number >> 8) & 0xFF, number & 0xFF
