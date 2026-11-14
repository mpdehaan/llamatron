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

"""The Main page: a grid of cells, one per page and one per action, each boxed in its page's colour, with a double-lined box around the cell the cursor is on.

The user's design. Arrange, where most of the work happens, has the first row to itself, with the
Real Time switch beside it; a blank line, then the pages of the things a song is made from and the
song's settings, two rows of four; a blank line, then the Set File page and the actions, Save, Open,
Export, Import and Quit. Each page's cell is boxed in its page's theme colour (tui/themes.py), every
colour toned to one brightness so that none looks stronger than another, and the rest in a dim box;
the selected cell's box is double-lined and bright. A cell says how many of its things the set has
where that means something, and the one sentence shown is the selected cell's, under the grid. Undo
and Redo have no cell, since they're Ctrl+Z and Ctrl+Y everywhere, and F1 and F2 are in the footer,
so that this screen is the one place that reminds of them.
"""

from rich.text import Text

from llamatron.composition.sections import GENERATOR_KINDS, Section
from llamatron.tui.drawing import Box, Canvas, INDENT, NOTHING, padded, SPACE, Style
from llamatron.strings.help import HELP_MAIN_PAGE
from llamatron.tui.keys import ARROWS_LEFT_RIGHT, Key
from llamatron.tui.screens.arrange_page import ArrangePage
from llamatron.tui.screens.everywhere import everywhere_actions, everywhere_key, quit_key
from llamatron.tui.screens.file_page import FilePage
from llamatron.tui.screens.chains_page import ChainsPage
from llamatron.tui.screens.generators_page import GeneratorsPage
from llamatron.tui.screens.grooves_page import GroovesPage
from llamatron.tui.screens.importing import import_midi
from llamatron.tui.screens.instruments_page import InstrumentsPage
from llamatron.tui.screens.page import Page
from llamatron.tui.screens.patterns_page import PatternsPage
from llamatron.tui.screens.registers_page import RegistersPage
from llamatron.tui.screens.scales_page import ScalesPage
from llamatron.tui.screens.songs_page import SongsPage
from llamatron.strings.errors import ERR_ADD_INSTRUMENT_FIRST, ERR_NO_INSTRUMENTS_TITLE
from llamatron.strings.labels import Crumb, MSG_ABOUT, PageName
from llamatron.strings.marks import MSG_REAL_TIME_OFF_MARK, MSG_REAL_TIME_ON_MARK
from llamatron.strings.messages import MSG_REAL_TIME_OFF, MSG_REAL_TIME_OFF_STOPPED, MSG_REAL_TIME_ON
from llamatron.tui import keybindings
from llamatron.tui import themes
from rich.color import Color
from rich.style import Style as RichStyle


# The grid's width, four cells of CELL_WIDTH across an 80-column console; a row's cells share it, each at least as wide as it needs,
# the spare columns spread evenly, and Arrange's cell taking all its row leaves beside the Real Time switch.
CELL_COLUMNS = 4
CELL_WIDTH = 20
GRID_WIDTH = CELL_COLUMNS * CELL_WIDTH
CELL_GAP = 0
# Between the box's left edge and the key, and between the key and the name, and the borders either side.
EDGE_GAP = SPACE
NAME_GAP = SPACE
BORDERS = 2
# A cell's three lines: its top edge, its key and name, and its bottom edge.
CELL_LINES = 3
# Blank lines over Arrange's row, between it and the pages, and between the pages and the file's row, so that the three groups read apart.
LINES_ABOVE_ARRANGE = 1
LINES_ABOVE_PAGES = 1
LINES_ABOVE_FILE = 1
# The colour each page's cell is boxed in, its page's theme toned to the edges' one brightness; a cell with none is boxed dim.
CELL_THEMES = {
    PageName.SONGS: themes.SONGS, PageName.PATTERNS: themes.PATTERNS, PageName.CHAINS: themes.CHAINS, PageName.GENERATORS: themes.GENERATORS,
    PageName.SCALES: themes.SCALES, PageName.GROOVES: themes.GROOVES, PageName.INSTRUMENTS: themes.INSTRUMENTS, PageName.REGISTERS: themes.REGISTERS,
    PageName.FILE: themes.SET_FILE,
}
# The pages whose cell counts the set's things, by the section counted. Generators and Grooves are counted on their own.
COUNTED_SECTIONS = {
    PageName.SONGS: Section.SONGS, PageName.PATTERNS: Section.PATTERNS, PageName.CHAINS: Section.CHAINS, PageName.SCALES: Section.SCALES,
    PageName.INSTRUMENTS: Section.INSTRUMENTS,
}
# What each action cell in the row under the pages is called: Save by its everywhere key, Open and Export by the main screen's own letters.
ACTION_NAMES = {
    keybindings.Page.SAVE: PageName.SAVE, keybindings.MainPage.OPEN_SET_HERE: PageName.OPEN, keybindings.MainPage.EXPORT_HERE: PageName.EXPORT,
    keybindings.MainPage.IMPORT_HERE: PageName.IMPORT, keybindings.MainPage.QUIT: PageName.QUIT,
}


def cell_name(item):
    """Return what a cell is called: the page its key opens, or the name of the action."""
    return ACTION_NAMES.get(item.binding, item.what)


def cell_opened_by(key):
    """Return the name of the cell a key opens on the main screen, a page or an action, or None for a key that opens none."""
    for binding in [*keybindings.MainPage.PAGES, *ACTION_NAMES]:
        if binding[0] == key:
            return ACTION_NAMES.get(binding, binding[2])
    return None


class MainPage(Page):
    """The menu: a grid of cells, the pages and then the actions, with a cursor the arrows move and Enter follows, beside the letters."""

    THEME = themes.MAIN_SCREEN
    KEYS = keybindings.MainPage

    # The header's second line is the crumbs, and the main screen is the start of every trail, so the line says so rather than standing blank.
    crumbs = (Crumb.MAIN_SCREEN,)
    HELP = HELP_MAIN_PAGE
    ABOUT = MSG_ABOUT

    def __init__(self, holder):
        super().__init__(holder)
        # The cell the cursor is on, counted along the rows, which stays put while a page is open over this one.
        self.place = 0

    def keys(self):
        return [
            self.bind(self.KEYS.FILE, action=lambda: self.show_page(FilePage(self.holder))),
            self.bind(self.KEYS.SONGS, action=lambda: self.show_page(SongsPage(self.holder))),
            self.bind(self.KEYS.PATTERNS, action=lambda: self.show_page(PatternsPage(self.holder))),
            self.bind(self.KEYS.CHAINS, action=lambda: self.show_page(ChainsPage(self.holder))),
            self.bind(self.KEYS.GENERATORS, action=lambda: self.show_page(GeneratorsPage(self.holder))),
            self.bind(self.KEYS.SCALES, action=lambda: self.show_page(ScalesPage(self.holder))),
            self.bind(self.KEYS.GROOVES, action=lambda: self.show_page(GroovesPage(self.holder))),
            self.bind(self.KEYS.INSTRUMENTS, action=lambda: self.show_page(InstrumentsPage(self.holder))),
            self.bind(self.KEYS.REGISTERS, action=lambda: self.show_page(RegistersPage(self.holder))),
            self.bind(self.KEYS.ARRANGE, action=lambda: self.show_page(ArrangePage(self.holder))),
            # The Real Time switch sits among the pages as a cell of its own, with its mark where a page's cell has its count.
            self.bind(self.KEYS.REAL_TIME, action=self.toggle_real_time),
        ]

    def toggle_real_time(self):
        """Turn real-time playback on or off, which needs an instrument to play through, and say which on the status line."""
        document = self.document()
        if not document.setlist().get_instrument_names():
            self.tell(ERR_NO_INSTRUMENTS_TITLE, ERR_ADD_INSTRUMENT_FIRST)
            return
        on = not document.setlist().is_real_time()
        document.set_real_time(on)
        if not on and self.app.transport.is_playing():
            # Arrange shows no stop with Real Time off, so turning it off stops what plays (a bug the user found).
            self.app.transport.stop_all()
            self.say(MSG_REAL_TIME_OFF_STOPPED)
            return
        self.say(MSG_REAL_TIME_ON if on else MSG_REAL_TIME_OFF)

    def cursor_keys(self):
        return [
            self.bind(self.KEYS.SELECT, action=self.move_cursor, wants_key=True),
            self.bind(self.KEYS.OPEN, action=self.open_selected),
        ]

    def page_key_table(self):
        """The pages, the action cells' keys (Save among them is an everywhere key, listed above), and the cursor's own keys."""
        return self.in_order([*self.keys(), *self.actions()[1:], *self.cursor_keys()])

    def shown_keys(self):
        """The footer: the cursor's keys, then Help and About, the two keys that work everywhere and have no cell, so that this screen reminds of them."""
        return [*self.cursor_keys(), self.bind(self.KEYS.FOOTER_HELP, action=self.show_help), self.bind(self.KEYS.FOOTER_ABOUT, action=self.show_about)]

    def actions(self):
        """Return the cells of the row after the pages: Save by its everywhere key, Open and Export by this screen's letters, doing what Ctrl+O and Ctrl+X do, Import, then Quit."""
        does = everywhere_actions(self)
        return [
            everywhere_key(page=self, binding=self.KEYS.SAVE),
            self.bind(self.KEYS.OPEN_SET_HERE, action=does[self.KEYS.OPEN_SET]),
            self.bind(self.KEYS.EXPORT_HERE, action=does[self.KEYS.EXPORT]),
            self.bind(self.KEYS.IMPORT_HERE, action=lambda: import_midi(self)),
            quit_key(self),
        ]

    def rows(self):
        """Return the grid's rows of cells, the user's order: Arrange with the Real Time switch; Songs, Scales, Patterns and Grooves;
        Generators, Chains, Instruments and Registers; then the Set File page and the actions."""
        pages = {item.binding: item for item in self.keys()}
        keys = self.KEYS
        return [
            [pages[keys.ARRANGE], pages[keys.REAL_TIME]],
            [pages[keys.SONGS], pages[keys.SCALES], pages[keys.PATTERNS], pages[keys.GROOVES]],
            [pages[keys.GENERATORS], pages[keys.CHAINS], pages[keys.INSTRUMENTS], pages[keys.REGISTERS]],
            [pages[keys.FILE], *self.actions()],
        ]

    def menu_items(self):
        """Return every cell the cursor can be on, along the rows."""
        return [item for row in self.rows() for item in row]

    def selected(self):
        return self.menu_items()[self.place]

    def select_open(self):
        """Put the cursor on the Open cell, as the tracker started with no set named does, the user's ask."""
        self.place = next(place for place, item in enumerate(self.menu_items()) if item.binding is self.KEYS.OPEN_SET_HERE)

    def row_and_column(self):
        """Return which row of the grid the cursor is on, and which cell along it."""
        place = self.place
        for number, row in enumerate(self.rows()):
            if place < len(row):
                return number, place
            place -= len(row)
        return 0, 0

    def move_cursor(self, name):
        """Left and Right step along the cells, row to row, and Up and Down move between rows, staying in the column where the row has one; none of them goes past an edge, the user's choice of 2026-11-08 over going round."""
        rows = self.rows()
        if name in ARROWS_LEFT_RIGHT:
            self.place = max(min(self.place + (1 if name == Key.RIGHT else -1), len(self.menu_items()) - 1), 0)
            return
        row, column = self.row_and_column()
        row = max(min(row + (1 if name == Key.DOWN else -1), len(rows) - 1), 0)
        self.place = sum(len(earlier) for earlier in rows[:row]) + min(column, len(rows[row]) - 1)

    def open_selected(self):
        """Do what the selected cell's key does."""
        self.selected().action()

    def duration(self):
        return self.document().lengths().song_seconds()

    def count(self, item):
        """Return what a cell shows at its right: how many of its things a page has, the Real Time switch's mark, or None where a count means nothing: File, Registers, Arrange and the actions."""
        setlist = self.document().setlist()
        name = cell_name(item)
        if name == PageName.REAL_TIME:
            return MSG_REAL_TIME_ON_MARK if setlist.is_real_time() else MSG_REAL_TIME_OFF_MARK
        if name == PageName.GENERATORS:
            return sum(len(setlist.get_item_names(section)) for section in GENERATOR_KINDS)
        if name == PageName.GROOVES:
            # The set's own grooves: the factory ones are always there, so counting them would say nothing.
            return len(setlist.get_own_groove_names())
        if name in COUNTED_SECTIONS:
            return len(setlist.get_item_names(COUNTED_SECTIONS[name]))
        return None

    def needed_width(self, item):
        """Return how wide a cell must be to hold its key, its name and its count inside its box."""
        count = self.count(item)
        return BORDERS + len(EDGE_GAP) + len(padded(item.shown_label())) + len(NAME_GAP) + len(self.shown_name(item)) + (len(NAME_GAP) + len(str(count)) if count is not None else 0) + len(EDGE_GAP)

    def cell_widths(self, row):
        """Return each cell's width in a row: what each needs, the spare columns spread evenly, or all of them to Arrange's cell on its row."""
        needs = [self.needed_width(item) for item in row]
        # A row too wide gives up the space before the right edge of each cell with no count, the file's row on an 80-column console.
        for place, item in enumerate(row):
            if sum(needs) <= GRID_WIDTH:
                break
            if self.count(item) is None:
                needs[place] -= len(EDGE_GAP)
        spare = max(GRID_WIDTH - sum(needs), 0)
        if row and row[0].binding is self.KEYS.ARRANGE:
            return [needs[0] + spare, *needs[1:]]
        widths = [need + spare // len(row) for need in needs]
        widths[-1] += GRID_WIDTH - sum(widths) if sum(widths) < GRID_WIDTH else 0
        return widths

    def shown_name(self, item):
        """Return the name drawn on a cell: its own, but Arrange/Play on the Arrange cell while the set's Real Time switch is on,
        the user's design, so that the cell says where a song is played."""
        if item.binding is self.KEYS.ARRANGE and self.document().setlist().is_real_time():
            return PageName.ARRANGE_PLAY
        return cell_name(item)

    def edge_style(self, item):
        """Return the style a cell's box is drawn in: its page's theme toned to the edges' brightness, or dim for a cell with none."""
        theme = CELL_THEMES.get(cell_name(item))
        if theme is None:
            return Style.DIM
        return RichStyle(color=Color.from_rgb(*themes.balanced(theme)))

    def draw_cell(self, *, canvases, left, item, selected, width):
        """Draw one cell, width wide, onto a row's three lines: its box, double-lined and bright when selected and otherwise in its colour, the key reversed, the name, bold when selected, and the count; Arrange's key and name centred."""
        right = left + width - 1
        inner = width - 2
        top, middle, bottom = canvases
        if selected:
            corners = (Box.DOUBLE_TOP_LEFT, Box.DOUBLE_RULE, Box.DOUBLE_TOP_RIGHT, Box.DOUBLE_BOTTOM_LEFT, Box.DOUBLE_BOTTOM_RIGHT, Box.DOUBLE_BAR)
            style = Style.BOLD
        else:
            corners = (Box.TOP_LEFT, Box.RULE, Box.TOP_RIGHT, Box.BOTTOM_LEFT, Box.BOTTOM_RIGHT, Box.BAR)
            style = self.edge_style(item)
        top_left, rule, top_right, bottom_left, bottom_right, bar = corners
        top.write(column=left, text=top_left + rule * inner + top_right, style=style)
        bottom.write(column=left, text=bottom_left + rule * inner + bottom_right, style=style)
        middle.write(column=left, text=bar, style=style)
        middle.write(column=right, text=bar, style=style)
        label = padded(item.shown_label())
        name = self.shown_name(item)
        start = left + 1 + len(EDGE_GAP)
        if item.binding is self.KEYS.ARRANGE:
            start = left + max((width - len(label) - len(NAME_GAP) - len(name)) // 2, 1)
        middle.write(column=start, text=label, style=Style.REVERSE)
        middle.write(column=start + len(label), text=NAME_GAP + name, style=Style.BOLD if selected else Style.PLAIN)
        count = self.count(item)
        if count is not None:
            # Right-aligned, with one space before the box's edge, or against the edge when a long name leaves no room for the space.
            name_end = start + len(label) + len(NAME_GAP) + len(name)
            middle.write(column=max(right - 1 - len(str(count)), min(name_end + len(NAME_GAP), right - len(str(count)))), text=str(count))

    def row_lines(self, *, row, width):
        """Return the three lines of one row of cells."""
        canvases = [Canvas(width) for _ in range(CELL_LINES)]
        selected = self.selected()
        left = CELL_GAP
        for item, cell_width in zip(row, self.cell_widths(row)):
            self.draw_cell(canvases=canvases, left=left, item=item, selected=item.keys == selected.keys, width=cell_width)
            left += cell_width + CELL_GAP
        return [canvas.text() for canvas in canvases]

    def body(self, *, width, height):
        # Nothing above the cells: the crumbs name the set and the song, and the cells count what the set holds.
        lines = []
        rows = self.rows()
        gaps = {0: LINES_ABOVE_ARRANGE, 1: LINES_ABOVE_PAGES, len(rows) - 1: LINES_ABOVE_FILE}
        for number, row in enumerate(rows):
            # Room above Arrange, again above the pages and again above the file's row, so that the three groups read apart.
            lines += [Text(NOTHING) for _ in range(gaps.get(number, 0))]
            lines += self.row_lines(row=row, width=width)
        # The one sentence shown: what the selected cell is for.
        lines.append(Text(INDENT + self.ABOUT[cell_name(self.selected())], style=Style.DIM))
        return lines
