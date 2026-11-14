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

"""The demo's name crossing the screen (tui/components/scroll_text.py), shown after the title when an example is recorded, the user's design."""

from llamatron.tui.components.scroll_text import banner, scroll_lines
from llamatron.tui.screens.set.splash import Splash


class DemoScroll(Splash):
    """The whole terminal, black, with the words crossing from right to left. Like the splash, it binds no keys and goes away when the launch says."""

    def __init__(self, *, text, **named):
        """text is the words that cross; seconds, as the splash's, is how long the launch shows the screen."""
        super().__init__(**named)
        self._rows = banner(text)

    def lines(self, *, width, height):
        """Return the screen's lines: the words where they are at this moment."""
        return scroll_lines(rows=self._rows, width=width, height=height, elapsed=self.elapsed())
