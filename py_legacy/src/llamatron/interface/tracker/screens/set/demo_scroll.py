# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The demo's name crossing the screen (interface/tracker/components/scroll_text.py), shown after the title when an example is recorded."""

from llamatron.interface.tracker.components.scroll_text import banner, scroll_lines
from llamatron.interface.tracker.screens.set.splash import Splash


class DemoScroll(Splash):
    """The whole terminal, black, with the words crossing from right to left. Like the splash, it binds no keys and goes away when the launch says."""

    def __init__(self, *, text, **named):
        """text is the words that cross; seconds, as the splash's, is how long the launch shows the screen."""
        super().__init__(**named)
        self._rows = banner(text)

    def lines(self, *, width, height):
        """Return the screen's lines: the words where they are at this moment."""
        return scroll_lines(rows=self._rows, width=width, height=height, elapsed=self.elapsed())
