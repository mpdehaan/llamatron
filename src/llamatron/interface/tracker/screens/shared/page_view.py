# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The widget a page shows its lines in, which sends the terminal only the lines that changed.

A page draws all of its lines after every key and, while a song plays, ten times a second. Shown in one Static, every line was
turned into Textual's styles again and sent to the terminal whole each time, about 29 KB a frame on a 160 by 50 console, which
took most of the time a key or a tick costs. The view keeps each line it showed, as Textual's Strip, while the page draws the
same line again, and refreshes only the lines that changed, so a key that changes three lines sends three."""

from rich.segment import Segment
from rich.style import Style as RichStyle
from textual.geometry import Region
from textual.strip import Strip
from textual.widget import Widget

# How many lines the view keeps made, of any it has shown: a page's cursor moving back and forth, its blank lines and its rules
# draw the same few lines again and again, and each made once is a dictionary's look-up after. Past this, it starts over.
MOST_LINES_KEPT = 1000


def line_key(line):
    """Return what tells two drawn lines apart: the text, its base style and every span's style, since Rich's own equality
    leaves out the base style, which would keep a dim status line dim after it turned to a refusal."""
    return (line.plain, line.style, tuple(line.spans))


class PageView(Widget):
    """A page's lines as shown: the key of each line and its strip, the width and base style they were made at, and which lines
    a draw changed, so that a test can see that an unchanged line was not made again."""

    def __init__(self, **named):
        super().__init__(**named)
        self._keys = []
        self._strips = []
        self._made_for = None
        self._changed = ()
        # Every line made at the width and base style now, by its key, so that a line drawn again anywhere is not made again.
        self._made = {}

    def show(self, lines):
        """Show a page's lines, making again and refreshing only those that differ from the lines shown, or every line when the
        width or the base style changed since."""
        width = self.size.width
        # Textual works the widget's style out afresh each time it is asked, which a page of changed lines would ask once a line.
        base = self.rich_style
        self._start_over_unless_made_for(width=width, base=base)
        changed = []
        for y, line in enumerate(lines):
            key = line_key(line)
            if y < len(self._keys) and self._keys[y] == key:
                continue
            self._put(y=y, key=key, strip=self._kept_strip(key=key, line=line, width=width, base=base))
            changed.append(y)
        changed += range(len(lines), len(self._keys))
        del self._keys[len(lines):]
        del self._strips[len(lines):]
        self._changed = tuple(changed)
        for y in changed:
            self.refresh(Region(0, y, width, 1))

    def shown(self):
        """Return what the view shows, to compare before and after a key: two are equal when every line's text and styles are."""
        return tuple(self._keys)

    def changed_lines(self):
        """Return the places of the lines the last show made again."""
        return self._changed

    def render_line(self, y):
        if y < len(self._strips):
            return self._strips[y]
        return Strip.blank(self.size.width, self.rich_style)

    def _start_over_unless_made_for(self, *, width, base):
        """Forget every line made, where the width or the base style has changed, or the lines kept have grown past their room."""
        made_for = (width, base)
        if made_for != self._made_for or len(self._made) > MOST_LINES_KEPT:
            self._keys = []
            self._strips = []
            self._made = {}
            self._made_for = made_for

    def _kept_strip(self, *, key, line, width, base):
        """Return a line's strip, made the first time the line is shown and kept by its key after."""
        strip = self._made.get(key)
        if strip is None:
            strip = self._strip_of(line=line, width=width, base=base)
            self._made[key] = strip
        return strip

    def _put(self, *, y, key, strip):
        if y < len(self._keys):
            self._keys[y] = key
            self._strips[y] = strip
        else:
            self._keys.append(key)
            self._strips.append(strip)

    def _strip_of(self, *, line, width, base):
        console = self.app.console
        # Rich leaves a line's own style out of its segments where the line has no spans, so it is laid under them here; under
        # a line with spans, where Rich has laid it already, laying it again changes nothing.
        segments = Segment.apply_style(line.render(console), console.get_style(line.style, default=RichStyle.null()))
        strip = Strip(list(segments)).apply_style(base)
        # The room after a line's text takes the background alone, as Textual pads a widget's content.
        return strip.adjust_cell_length(width, RichStyle(bgcolor=base.bgcolor))
