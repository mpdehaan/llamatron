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

"""Draws the pattern editor's rows: the header, the step grid of the rows showing, and the description of the step under the cursor.

The header, the window of steps and the rules come from GridDrawing, which the piano roll's
drawing shares; this draws the pinned rows and the scrolled rows between them, with a rule over
and under each section's heading, two neighbouring rules drawn as one.
"""

from rich.text import Text

from llamatron.composition.file_format import Row
from llamatron.tui.drawing import Align, Box, fit, SPACE, Style
from llamatron.tui.screens.grid_drawing import CELL_WIDTH, GridDrawing
from llamatron.strings.labels import MSG_SECTION_HINTS

# The lines around the rows: the two header lines, the top rule, the Step row, the bottom rule and the description.
LINES_AROUND_GRID = 6
# What the page draws around the body besides its header (the status line and the rule above the legend) and how many lines the
# editor's legend takes on an 80-column console on its longest row, which the gauge's height is worked out against with the header's.
LINES_UNDER_BODY = 2
LEGEND_LINES = 4


class PatternDrawing(GridDrawing):
    """Draws a PatternEditor's rows from what the editor knows about its pattern and what its rows view (PatternRows) knows about the rows and their cursor.

    The grid is the Step row, the pinned rows (the Degree gauge with its number and a rule under
    it, then Octave) and as many of the scrolled rows as fit, from the rows view's first_row, moved
    so that the cursor's row is always on screen; on a tall enough terminal nothing scrolls. The
    gauge is drawn with as many of its rows as leave room for one scrolled row.
    """

    __slots__ = ()

    def rows(self):
        """Return the editor's rows view, which holds the rows, their cursor and how far they've scrolled."""
        return self._editor.rows_view

    def widest_label(self):
        """Return the label column's width for the rows, sized for every row the editor could show, open or closed, so that nothing moves when a section opens."""
        rows = self.rows()
        editor = self._editor
        document = editor.document()
        # The labels come from the set, and from how tall the Degree gauge is and which sections are open, which the screen and the session decide.
        key = (PatternDrawing.widest_label.__name__, editor.item, rows.gauge_rows, frozenset(editor.holder.open_sections))
        return document.remembered(key=key, on=(document,), compute=self.widest_row_label)

    def widest_row_label(self):
        """Return the width of the longest label of every row there could be, with a space either side."""
        rows = self.rows()
        return max(len(label) for name in rows.all_row_names() for label in rows.row_for(name).labels()) + 2

    def header_extra(self):
        """Return the second header line's cells after Time: the hint of the section the cursor is in, where one has something to say, and otherwise the scale."""
        rows = self.rows()
        return [MSG_SECTION_HINTS.get(rows.section_of(rows.row_name()), self.scale_header())]

    # How tall everything is.

    def fixed_lines(self):
        """Return the lines the grid always has besides the gauge's rows and the scrolled rows: the rules, the Step row, the number row and the octave."""
        rows = self.rows()
        degree = rows.row_for(Row.DEGREE)
        pinned = self.rows_height(rows.pinned_rows())
        # The gauge's rows are counted apart, since they give way first.
        gauge = degree.rows_shown() if degree.has_gauge() else 0
        return LINES_AROUND_GRID + pinned - gauge

    def fit_gauge(self):
        """Set how many rows the gauge is drawn with: all of them when there's room, and otherwise what leaves room for the tallest scrolled row.

        The room is worked out from the whole screen with the legend's usual height, not from the
        lines the legend happens to leave, so that the gauge keeps one height as the cursor moves
        between rows whose legends differ by a line.
        """
        view = self.rows()
        degree = view.row_for(Row.DEGREE)
        # The first scrolled row is a section's heading, so the room is for a heading with its rule and the tallest row under one, so that a row shows beneath the heading before anything scrolls.
        scrolled = view.scrolled_rows()
        tallest = max((self.window_height([scrolled[0], row]) for row in scrolled), default=1)
        view.gauge_rows = degree.full_rows()
        room = self._editor.screen_height - self._editor.header_lines() - LINES_UNDER_BODY - LEGEND_LINES - self.fixed_lines() - tallest
        view.gauge_rows = max(min(degree.full_rows(), room), 0)

    def scrolled_rows_shown(self, height):
        """Return the scrolled rows that fit under the pinned ones, moving the window so that the cursor's row is on it."""
        view = self.rows()
        rows = view.scrolled_rows()
        degree = view.row_for(Row.DEGREE)
        room = max(height - self.fixed_lines() - (degree.rows_shown() if degree.has_gauge() else 0), 1)
        place = view.scrolled_row()
        if place is not None:
            view.first_row = min(view.first_row, place)
        view.first_row = max(min(view.first_row, len(rows) - 1), 0)
        while place is not None and self.window_height(rows[view.first_row:place + 1]) > room and view.first_row < place:
            view.first_row += 1
        shown = []
        for row in rows[view.first_row:]:
            if self.window_height([*shown, row]) > room and shown:
                break
            shown.append(row)
        return shown

    def row_blocks(self, rows, *, after_rule=False):
        """Return each row with whether a rule is drawn over it: where it asks for one, unless the row before ended with one, or a rule was just drawn."""
        blocks = []
        for row in rows:
            blocks.append((row, row.rule_before() and not after_rule))
            after_rule = row.rule_after()
        return blocks

    def rows_height(self, rows):
        """Return how many lines some rows take in a run, with the rules over and under them."""
        return sum(row.height() + (1 if rule_before else 0) + (1 if row.rule_after() else 0) for row, rule_before in self.row_blocks(rows))

    def window_height(self, rows):
        """Return how many lines the scrolled rows shown take: they're drawn under the pinned rows' rule and over the bottom rule, so the first needs no rule of its own over it and the last none under it."""
        return self.rows_height(rows) - (1 if rows and rows[0].rule_before() else 0) - (1 if rows and rows[-1].rule_after() else 0)

    # The grid.

    def label_style(self, *, row, on_row, number):
        """Return a label's style: reverse video for the cursor on a section's heading, bold on the cursor's row, and plain elsewhere."""
        if not (on_row and number == row.cursor_line()):
            return Style.PLAIN
        return Style.REVERSE if row.marks_label() else Style.BOLD

    def row_lines(self, *, row, first, last):
        """Return a row's lines, drawn once and kept until the set changes, unless the cursor is on the row or the row is a section's heading.

        Only the cursor's row shows where the cursor is, and only a heading shows whether its
        section is open, so every other row's lines come from the set, the steps shown, the label
        column's width and how tall the Degree gauge is. Moving the cursor draws the row the
        cursor left and the row the cursor reached. Nothing changes a line once it's drawn.
        """
        if self.rows().current_row() is row or row.marks_label():
            return self.drawn_row_lines(row=row, first=first, last=last)
        editor = self._editor
        document = editor.document()
        key = (PatternDrawing.row_lines.__name__, editor.item, row.name, first, last, self.label_width(), self.rows().gauge_rows)
        return document.remembered(key=key, on=(document,), compute=lambda: self.drawn_row_lines(row=row, first=first, last=last))

    def drawn_row_lines(self, *, row, first, last):
        """Draw a row's lines: its labels, bold on the cursor's row, and each step's cells, the cursor's reversed on the line that holds the value."""
        editor = self._editor
        on_row = self.rows().current_row() is row
        labels = row.labels()
        cells = [row.cell_lines(step=step) for step in range(first, last)]
        lines = []
        beats = self.beat_steps()
        for number, label in enumerate(labels):
            line = Text(no_wrap=True)
            line.append(Box.BAR, style=Style.DIM)
            line.append(fit(text=SPACE + label, width=self.label_width()), style=self.label_style(row=row, on_row=on_row, number=number))
            if row.marks_label():
                # A section heading has no cells, so no divider crosses it: the dividers above end in the rule over it and the ones below start in the rule under it, the user's ask of 2026-11-09.
                line.append(SPACE * ((last - first) * (CELL_WIDTH + 1)))
                line.append(Box.BAR, style=Style.DIM)
                lines.append(line)
                continue
            for step in range(first, last):
                self.append_edge(line=line, step=step, beats=beats, single=Box.BAR, double=Box.DOUBLE_BAR, replaced=row.edge_text(step=step))
                text = fit(text=cells[step - first][number], width=CELL_WIDTH, align=Align.CENTER)
                selected = on_row and not row.marks_label() and step == editor.step and number == row.cursor_line()
                # A blocked cell's mark is dim, so that the values stand out from the places that can't hold one.
                line.append(text, style=Style.REVERSE if selected else (Style.DIM if row.blocked(step=step) else Style.PLAIN))
            line.append(Box.BAR, style=Style.DIM)
            lines.append(line)
        return lines

    def grid_lines(self, *, first, last, rows=None):
        """Return the grid: the rules, the Step row, the pinned rows and the scrolled rows given, or all of them, with a rule where a row asks for one and never two together."""
        view = self.rows()
        if rows is None:
            rows = view.scrolled_rows()
        lines = [self.top_rule(first=first, last=last), self.step_line(first=first, last=last)]
        blocks = self.row_blocks([*view.pinned_rows(), *rows])
        for number, (row, rule_before) in enumerate(blocks):
            if rule_before:
                lines.append(self.rule_between(above=blocks[number - 1][0] if number else None, below=row, first=first, last=last))
            lines += self.row_lines(row=row, first=first, last=last)
            # The bottom rule closes the last row, so a rule under it would double up.
            if row.rule_after() and number < len(blocks) - 1:
                lines.append(self.rule_between(above=row, below=blocks[number + 1][0], first=first, last=last))
        lines.append(self.bottom_rule(first=first, last=last, joints=not (blocks and blocks[-1][0].marks_label())))
        return lines

    def rule_between(self, *, above, below, first, last):
        """Return the rule between two rows: crosses where both have dividers, bottom tees over a section heading, top tees under one, and an unbroken line between two headings."""
        heading_above = above is not None and above.marks_label()
        heading_below = below.marks_label()
        if heading_above and heading_below:
            return self.plain_rule(first=first, last=last)
        if heading_below:
            return self.closing_rule(first=first, last=last)
        if heading_above:
            return self.opening_rule(first=first, last=last)
        return self.inner_rule(first=first, last=last)

    def body(self, *, width, height):
        self._editor.clamp()
        first, last = self.scroll_to_cursor(width)
        self.fit_gauge()
        rows = self.scrolled_rows_shown(height)
        lines = self.header_lines(width=width, first=first, last=last) + self.grid_lines(first=first, last=last, rows=rows)
        return self.with_description(lines=lines, width=width, height=height)
