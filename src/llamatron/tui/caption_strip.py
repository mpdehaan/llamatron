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

"""The caption strip, the user's design: what the video tutorial says, shown at the foot of the screen as a film's captions are.

The tracker's pages move up two lines to make room, so that nothing is covered. The first of the two
lines is the caption, bold black on white and centred; the second is white, so that the words stand
clear of the bottom of the frame where a video player puts its controls. A sentence too long for one
line is shown a part at a time (parts), which the tutorial's runner times. Only the tutorial makes a
strip; without one the tracker draws as ever.
"""

import textwrap

from rich.color import Color
from rich.style import Style as RichStyle
from rich.text import Text

from llamatron.tui.drawing import NOTHING, SPACE

# The lines the strip takes at the foot of the screen, the spaces kept clear at either end of a caption, and the narrowest a part is ever wrapped to.
CAPTION_LINES = 2
CAPTION_MARGIN = 2
FEWEST_COLUMNS = 20
CAPTION_STYLE = RichStyle(bold=True, color=Color.from_rgb(0, 0, 0), bgcolor=Color.from_rgb(255, 255, 255))


class CaptionStrip:
    """The caption showing now, or nothing."""

    __slots__ = ('_text',)

    def __init__(self):
        self._text = NOTHING

    def show(self, text):
        self._text = text

    def text(self):
        return self._text

    def lines(self, width):
        """Return the strip's two lines at a width: the caption centred, then a white line."""
        shown = self._text[:max(width - 2 * CAPTION_MARGIN, 0)]
        return [Text(shown.center(width), style=CAPTION_STYLE, no_wrap=True), Text(SPACE * width, style=CAPTION_STYLE)]


def parts(*, text, width):
    """Return a sentence as the parts that each fit one caption at a width, broken between words."""
    return textwrap.wrap(text, max(width - 2 * CAPTION_MARGIN, FEWEST_COLUMNS)) or [NOTHING]
