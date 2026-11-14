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

"""The splash: the title on black (tui/components/title_card.py), shown for a few seconds when the tracker is launched for recording, fading to black at its end.

The user's design: the title replaced the word that waved letter by letter, keeping its sine waves
as the way the block letters come in. The start screen (start_screen.py) is the same title with its
prompt, waiting for Enter.
"""

import time

from rich.text import Text
from textual.screen import Screen
from textual.widgets import Static

from llamatron.tui.components.title_card import title_lines
from llamatron.tui.drawing import LINE_BREAK, NOTHING
from llamatron.tui.key_table import pressed_key, quits_at_once

SPLASH_VIEW_ID = 'splash-view'
# How often the picture is drawn.
FRAME_SECONDS = 1 / 30


class Splash(Screen):
    """The whole terminal, with the title in the middle. It binds no keys: it goes away by itself when the launch says."""

    PROMPT = False

    def __init__(self, *, seconds, clock=time.monotonic):
        """seconds is how long the splash shows, fading to black over its last moments, or None to show until something closes it; clock is for the tests, which move time themselves."""
        super().__init__()
        self._seconds = seconds
        self._clock = clock
        self._started = clock()
        self._timer = None

    def compose(self):
        yield Static(id=SPLASH_VIEW_ID)

    def on_mount(self):
        self._timer = self.set_interval(FRAME_SECONDS, self.draw)
        self.draw()

    def on_unmount(self):
        if self._timer is not None:
            self._timer.stop()

    def on_resize(self):
        self.draw()

    def on_key(self, event):
        """Quit at once on Ctrl+C, the one key the splash answers."""
        if quits_at_once(pressed_key(event)):
            event.stop()
            self.app.exit()

    def elapsed(self):
        return self._clock() - self._started

    def lines(self, *, width, height):
        """Return the screen's lines: the title at this moment."""
        return title_lines(width=width, height=height, elapsed=self.elapsed(), prompt=self.PROMPT, seconds=self._seconds)

    def draw(self):
        if not self.is_attached:
            return
        lines = self.lines(width=self.app.size.width, height=self.app.size.height)
        text = Text(NOTHING)
        for place, line in enumerate(lines):
            text.append_text(line)
            if place < len(lines) - 1:
                text.append(LINE_BREAK)
        self.query_one(Static).update(text)
