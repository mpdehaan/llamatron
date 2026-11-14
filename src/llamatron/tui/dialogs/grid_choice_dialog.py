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

"""The Grid choice dialog: offers options laid out in a grid, with a line under it saying what the selected one is."""

from rich.text import Text

from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.drawing import fit, NOTHING, padded, SPACE, Style
from llamatron.tui.keys import ARROWS_UP_DOWN, Key
from llamatron.strings.marks import MSG_NEXT_PAGE_MARK, MSG_PAGE_TAB, MSG_PREVIOUS_PAGE_MARK
from llamatron.tui import keybindings


class Heading(str):
    """A column heading in a GridChoiceDialog, which can't be chosen."""


def grouped_grid(columns):
    """Return grid rows from columns of (heading, [option place, ...]) groups, with a gap
    between the groups in a column."""
    built = []
    for groups in columns:
        cells = []
        for heading, items in groups:
            if cells:
                cells.append(None)
            cells += [Heading(heading), *items]
        built.append(cells)
    height = max((len(cells) for cells in built), default=0)
    return [[cells[row] if row < len(cells) else None for cells in built] for row in range(height)]


class GridChoiceDialog(ChoiceDialog):
    """Offers options laid out in a grid, with a line under it saying what the selected one is.

    The grid is rows of cells, each an option's place in the list, a Heading, or None for a gap.
    Options in top go on a line of their own above it. Up and down move within a column, and up
    from the top of a column reaches the top line. Left and right go to the next column across,
    landing on the option nearest to the row the cursor was on. Each column is as wide as what's
    in it.

    Instead of one grid, pages can be a list of (name, grid) pairs. The top line names every page
    and says which key reaches the others. Tab and Shift+Tab change page, and so do left and right
    off the edge of a page, stopping at the first and last pages. It opens on the first page
    holding the current option. Every page is drawn as wide and as tall as the largest, so the
    dialog keeps its size when the page changes.
    """

    KEYS = keybindings.GridChoiceDialog

    def __init__(self, *, title, options, grid, current=0, details=None, top=(), pages=None):
        super().__init__(title=title, options=options, current=current)
        self.top = list(top)
        self.details = details
        self.pages = pages or [(None, grid)]
        self.page_cells = [self.padded(page_grid) for _, page_grid in self.pages]
        self.page = next((number for number, cells in enumerate(self.page_cells) if self.find(cells) is not None), 0)

    def padded(self, grid):
        """Return a grid with every row the same width, and the top line first when there is one."""
        width = max((len(cells) for cells in grid), default=1)
        top_row = [*self.top, *[None] * (width - len(self.top))]
        # Navigation works on one grid, with the top line as its first row when there is one.
        return ([top_row] if self.top else []) + [list(cells) + [None] * (width - len(cells)) for cells in grid]

    def grid(self):
        return self.pages[self.page][1]

    def cells(self):
        return self.page_cells[self.page]

    def takes_text(self):
        """A grid of choices keeps its own keys and doesn't search."""
        return False

    def keys(self):
        keys = [
            self.bind(self.KEYS.CANCEL, action=lambda: self.dismiss(None)),
            self.bind(self.KEYS.MOVE, action=self.move, wants_key=True),
            self.bind(self.KEYS.CHOOSE, action=lambda: self.dismiss(self.place)),
        ]
        if len(self.pages) > 1:
            keys.append(self.bind(self.KEYS.OTHER_PAGE, action=self.turn_key))
        return keys

    def heading(self, width):
        if len(self.pages) == 1:
            return Text(self.title, style=Style.BOLD)
        tabs = Text(no_wrap=True)
        if self.page > 0:
            tabs.append(MSG_PREVIOUS_PAGE_MARK, style=Style.BOLD)
        for number, (name, _) in enumerate(self.pages):
            tabs.append(MSG_PAGE_TAB.format(name=name), style=Style.REVERSE if number == self.page else Style.DIM)
            tabs.append(SPACE)
        if self.page < len(self.pages) - 1:
            tabs.append(MSG_NEXT_PAGE_MARK, style=Style.BOLD)
        tabs.rstrip()
        # The page names always fit, so the title is cut short rather than widening the dialog.
        line = Text(fit(text=self.title, width=max(width - tabs.cell_len - 2, 0)), style=Style.BOLD)
        line.append(SPACE * max(width - line.cell_len - tabs.cell_len, 0))
        line.append_text(tabs)
        return line

    def option_at(self, *, row, column, cells=None):
        cells = self.cells() if cells is None else cells
        cell = cells[row][column]
        return None if cell is None or isinstance(cell, Heading) else cell

    def find(self, cells):
        """Return the row and column of the selected option in a page's cells, or None."""
        for row in range(len(cells)):
            for column in range(len(cells[row])):
                if self.option_at(row=row, column=column, cells=cells) == self.place:
                    return row, column
        return None

    def where(self):
        return self.find(self.cells()) or (0, 0)

    def nearest(self, *, row, column):
        """Return the option in a column nearest to a row, or None if the column has none."""
        found = sorted((abs(other - row), other) for other in range(len(self.cells())) if self.option_at(row=other, column=column) is not None)
        return self.option_at(row=found[0][1], column=column) if found else None

    def turn(self, *, step, row, column):
        """Go to the next or previous page, landing near a row, starting from a column and moving
        inward when that column is empty."""
        self.page = (self.page + step) % len(self.pages)
        width = len(self.cells()[0])
        column = min(column, width - 1)
        inward = 1 if column == 0 else -1
        for search in (column, *range(column + inward, width if inward > 0 else -1, inward), *range(width)):
            found = self.nearest(row=row, column=search)
            if found is not None:
                self.place = found
                return

    def turn_key(self, step):
        """Turn to the next page, which Tab does, or the one before, which Shift+Tab does, stopping at the first and the last."""
        if 0 <= self.page + step < len(self.pages):
            row, column = self.where()
            self.turn(step=step, row=row, column=column)

    def move(self, name):
        row, column = self.where()
        width = len(self.cells()[0])
        if name in ARROWS_UP_DOWN:
            step = -1 if name == Key.UP else 1
            others = list(range(row + step, -1 if step < 0 else len(self.cells()), step))
            # Keep to the column, or else take the nearest option in any column, like the top line.
            for search in (column, *range(width)):
                for other in others:
                    found = self.option_at(row=other, column=search)
                    if found is not None:
                        self.place = found
                        return
            return
        step = -1 if name == Key.LEFT else 1
        for offset in range(1, width + 1):
            target = column + step * offset
            if not 0 <= target < width:
                if len(self.pages) > 1:
                    # Off the edge of a page goes to the edge of the next one across, but not
                    # from the last page round to the first.
                    if 0 <= self.page + step < len(self.pages):
                        self.turn(step=step, row=row, column=0 if step > 0 else width)
                    return
                target %= width
            found = self.nearest(row=row, column=target)
            if found is not None:
                self.place = found
                return

    def column_widths(self):
        """Return each column's width, as wide as that column on any page."""
        sizes = [0] * max(len(cells[0]) for cells in self.page_cells)
        for _, grid in self.pages:
            for cells in grid:
                for column, cell in enumerate(cells):
                    if cell is not None:
                        sizes[column] = max(sizes[column], len(cell if isinstance(cell, Heading) else str(self.options[cell])))
        return [size + 3 for size in sizes]

    def option_text(self, *, place, size):
        text = Text(no_wrap=True)
        text.append(padded(self.options[place]), style=Style.REVERSE if place == self.place else Style.PLAIN)
        text.append(SPACE * max(size - len(str(self.options[place])) - 2, 0))
        return text

    def lines(self, width):
        sizes = self.column_widths()
        result = []
        if self.top:
            line = Text(no_wrap=True)
            for place in self.top:
                line.append_text(self.option_text(place=place, size=0))
                line.append(SPACE)
            result += [line, Text(NOTHING)]
        for cells in self.grid():
            line = Text(no_wrap=True)
            for column, cell in enumerate(cells):
                size = sizes[column]
                if cell is None:
                    line.append(SPACE * size)
                elif isinstance(cell, Heading):
                    line.append(fit(text=SPACE + cell, width=size), style=Style.BOLD)
                else:
                    line.append_text(self.option_text(place=cell, size=size))
            result.append(line)
        # Shorter pages are padded to the height of the tallest.
        result += [Text(NOTHING)] * (max(len(grid) for _, grid in self.pages) - len(self.grid()))
        if self.details is not None:
            result += [Text(NOTHING), Text(fit(text=self.details(self.place), width=width))]
        return result
