# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Grid choice dialog: offers options laid out in a grid, with a line under it saying what the selected one is."""

from rich.text import Text

from llamatron.interface.forms import dialogs, moves
from llamatron.interface.forms.cursor import NoSuchPlace
from llamatron.interface.forms.dialogs import blank, GridCell, said_across
from llamatron.interface.tracker import drawing, keybindings, keys as keys_values
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.drawing import fit, Style
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.renderers import dialogs as dialog_renderer
from llamatron.user_strings import marks


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
    return [row_across(columns=built, row=row) for row in range(height)]


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
            self.bind(self.KEYS.MOVE, action=self.move_cursor, wants_key=True),
            self.bind(self.KEYS.CHOOSE, action=lambda: self.dismiss(self.cursor.get_place())),
        ]
        if len(self.pages) > 1:
            keys.append(self.bind(self.KEYS.OTHER_PAGE, action=self.turn_key))
        return keys

    def heading(self, width):
        if len(self.pages) == 1:
            return Text(self.title, style=Style.BOLD)
        tabs = Text(no_wrap=True)
        if self.page > 0:
            tabs.append(marks.MSG_PREVIOUS_PAGE_MARK, style=Style.BOLD)
        for number, (name, _) in enumerate(self.pages):
            tabs.append(marks.MSG_PAGE_TAB.format(name=name), style=Style.REVERSE if number == self.page else Style.DIM)
            tabs.append(drawing.SPACE)
        if self.page < len(self.pages) - 1:
            tabs.append(marks.MSG_NEXT_PAGE_MARK, style=Style.BOLD)
        tabs.rstrip()
        # The page names always fit, so the title is cut short rather than widening the dialog.
        line = Text(fit(text=self.title, width=max(width - tabs.cell_len - 2, 0)), style=Style.BOLD)
        line.append(drawing.SPACE * max(width - line.cell_len - tabs.cell_len, 0))
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
                if self.option_at(row=row, column=column, cells=cells) == self.cursor.get_place():
                    return row, column
        return None

    def place_in_pages(self, place):
        """Return the page, row and column an option is drawn at."""
        for page, cells in enumerate(self.page_cells):
            for row in range(len(cells)):
                for column in range(len(cells[row])):
                    if self.option_at(row=row, column=column, cells=cells) == place:
                        return page, row, column
        raise NoSuchPlace(screen=self, target=place)

    def key_toward_place(self, place):
        """Return the key that brings the cursor nearer an option: Tab to its page, Up or Down to its row, then Left or Right to its column."""
        if self.cursor.is_on(place):
            return None
        page, target_row, target_column = self.place_in_pages(place)
        if page != self.page:
            return Key.TAB
        row, column = self.where()
        return moves.toward(here=row, there=target_row) or moves.toward(here=column, there=target_column, back=Key.LEFT, forward=Key.RIGHT)

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
                self.cursor.set_place(found)
                return

    def turn_key(self, step):
        """Turn to the next page, which Tab does, or the one before, which Shift+Tab does, stopping at the first and the last."""
        if 0 <= self.page + step < len(self.pages):
            row, column = self.where()
            self.turn(step=step, row=row, column=column)

    def move_cursor(self, name):
        row, column = self.where()
        width = len(self.cells()[0])
        if name in keys_values.ARROWS_UP_DOWN:
            step = -1 if name == Key.UP else 1
            others = list(range(row + step, -1 if step < 0 else len(self.cells()), step))
            # Keep to the column, or else take the nearest option in any column, like the top line.
            for search in (column, *range(width)):
                for other in others:
                    found = self.option_at(row=other, column=search)
                    if found is not None:
                        self.cursor.set_place(found)
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
                self.cursor.set_place(found)
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

    def option_cell(self, *, place, size):
        """Return the cell of a choice in a column of a size, under the cursor where it is the cursor's."""
        return GridCell(kind=dialogs.CHOICE_CELL, text=str(self.options[place]), width=size, selected=place == self.cursor.get_place())

    def lines(self, width):
        sizes = self.column_widths()
        result = []
        if self.top:
            top = []
            for place in self.top:
                top += [self.option_cell(place=place, size=0), GridCell(kind=dialogs.GAP_CELL, width=1)]
            result += [dialog_renderer.grid_cells_line(top), *dialog_renderer.said_lines(paragraphs=[blank()], width=width)]
        for cells in self.grid():
            result.append(dialog_renderer.grid_cells_line([self.grid_cell(cell=cell, size=sizes[column]) for column, cell in enumerate(cells)]))
        # Shorter pages are padded to the height of the tallest.
        result = dialog_renderer.filled(lines=result, height=len(result) + max(len(grid) for _, grid in self.pages) - len(self.grid()))
        if self.details is not None:
            result += dialog_renderer.said_lines(paragraphs=[blank(), said_across(self.details(self.cursor.get_place()))], width=width)
        return result

    def grid_cell(self, *, cell, size):
        """Return a place of the grid as a cell: a gap, a column's heading, or a choice."""
        if cell is None:
            return GridCell(kind=dialogs.GAP_CELL, width=size)
        if isinstance(cell, Heading):
            return GridCell(kind=dialogs.HEADING_CELL, text=cell, width=size)
        return self.option_cell(place=cell, size=size)

def row_across(*, columns, row):
    """Return one row of the grid across its columns, None where a column is shorter."""
    return [cells[row] if row < len(cells) else None for cells in columns]
