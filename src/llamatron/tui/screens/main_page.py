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

"""The Main page: the cells of every page and the file's actions, the user's design, with a double-lined box around what the cursor is on.

It has two layouts, chosen by the room the console has. On a console too short for the second, the grid of three columns
described below. On a console tall enough, the smart fit layout: Arrange's cell at the left, as tall as the console and as wide
as the rest leaves, and at the right two columns as narrow as their names: the Real Time switch across both, the pages in pairs,
and the file's actions in one box, three rows of two. In it, Arrange's cell shows a small map of the song under the song's
details, a line for each track with its light and a block for each scene where the track has a clip, and a clip that plays
glows in a brighter colour, fading in and out slowly, never flashing.

The grid of three columns:

Arrange, where most of the work happens, has the first column and is three cells tall, drawn as a
small monitor, green on dark green: its name, the clock while the song plays, the current song's
scale, tempo and time signature, how many scenes and tracks it has, and while the set's Real Time
switch is on, a light for each track, green while a note sounds on it. Under it is the Real Time
switch, and beside both, two columns of the pages a song is made from. Under the grid one bar, as
wide as the grid, holds the file's six actions in two rows on the grid's own columns, with no lines
between them. The first column is as wide as Arrange's name and the clock need, the other two share
the rest of the console's width. Each page's cell is boxed in its page's theme colour
(tui/themes.py), toned to one brightness, and the rest in a dim box; the selected cell's box is
double-lined and bright, and in the bar the selected action is in reverse video inside the bar's
double-lined box. A cell says how many of its things the set has where that means something, and the
status line, right above the legend, says what the selected cell is for. The arrows move by the geometry drawn and
stop at every edge. Undo and Redo have no cell, since they're Ctrl+Z and Ctrl+Y everywhere, and F1
and F3 are in the footer, so that this screen is the one place that reminds of them.
"""

from collections import deque
from time import monotonic

from rich.text import Text

from llamatron.composition.sections import GENERATOR_KINDS, Section
from llamatron.tui.drawing import Align, Box, Canvas, fit, NOTHING, padded, SPACE, Style
from llamatron.strings.help import HELP_MAIN_PAGE
from llamatron.tui.keys import Key
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
from llamatron.tui.text import clock, tempo_text
from llamatron.strings.marks import (
    MSG_MAIN_CLOCK, MSG_MAIN_MAP_CLIP, MSG_MAIN_MAP_CUT, MSG_MAIN_MAP_EMPTY, MSG_MAIN_MORE_TRACKS, MSG_MAIN_ONE_SCENE, MSG_MAIN_ONE_TRACK,
    MSG_MAIN_SCENES, MSG_MAIN_TEMPO, MSG_MAIN_TRACKS,
    MSG_REAL_TIME_OFF_MARK, MSG_REAL_TIME_ON_MARK,
)
from llamatron.strings.messages import MSG_NO_SCALE, MSG_REAL_TIME_OFF, MSG_REAL_TIME_OFF_STOPPED, MSG_REAL_TIME_ON
from llamatron.tui import keybindings
from llamatron.tui import themes
from rich.color import Color
from rich.style import Style as RichStyle


# The grid: three columns, a space between them, on a console at least this wide; a wider console widens every column.
COLUMNS = 3
MINIMUM_WIDTH = 80
CELL_GAP = 1
# Between the box's left edge and the key, and between the key and the name, and the borders either side.
EDGE_GAP = SPACE
NAME_GAP = SPACE
BORDERS = 2
# A cell's three lines: its top edge, its key and name, and its bottom edge.
CELL_LINES = 3
# Arrange's cell is this many cells tall, and the grid this many; the bar under it holds this many rows of actions.
ARRANGE_ROWS = 3
GRID_ROWS = 4
BAR_ROWS = 2
# The row of the grid the cursor is taken to be on when it reaches Arrange from above or below, or by starting there: its top.
ARRANGE_TOP = 0
# Blank lines over the grid.
LINES_ABOVE_GRID = 1
# Inside Arrange's cell, which line holds what: the name and the clock, the song's scale, tempo and time signature, its scenes
# and tracks, and the first line of the track lights, each group after a blank line (the user's design).
NAME_LINE = 0
DETAILS_LINE = 2
COUNTS_LINE = 3
LIGHTS_LINE = 5
# Between two details on a line, and between the name and the clock.
DETAIL_GAP = SPACE * 2
# The track lights go in columns at least this wide, two columns at least, a wider cell holding more (the user's design).
LIGHT_COLUMN_WIDTH = 13
FEWEST_LIGHT_COLUMNS = 2
# How far each arrow moves the cursor over the grid, in rows and columns.
ARROW_STEPS = {Key.UP: (-1, 0), Key.DOWN: (1, 0), Key.LEFT: (0, -1), Key.RIGHT: (0, 1)}
# The smart fit layout, the user's design. Its right side is the Real Time switch, four rows of two pages, and the bar of the
# file's actions, three rows in one box: this many lines, which the console must have under the blank line for the layout to be used.
PAGE_PAIRS = 4
SMART_BAR_ROWS = 3
SMART_RIGHT_COLUMNS = 2
SMART_RIGHT_LINES = CELL_LINES + PAGE_PAIRS * CELL_LINES + SMART_BAR_ROWS + BORDERS
# In its Arrange cell, the map of the song starts on the line the lights start on in the grid. A track's name takes this many
# columns at most, after its light and a space, and the scenes' blocks start after a gap.
MAP_LINE = LIGHTS_LINE
MAP_NAME_WIDTH = 10
LIGHT_WIDTH = 2
# A playing clip's block glows: over this many steps, each this long, from the monitor's green to the glow's colour and back, so
# that the light fades in and out slowly and never flashes (the user's rule). The colours are red, green and blue.
GLOW_FULL = 12
GLOW_STEP_SECONDS = 0.125
MONITOR_GREEN = (60, 220, 90)
MONITOR_BACKGROUND = (0, 48, 16)
GLOW_COLOR = (255, 236, 140)
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


def cell_positions(*, rows, binding):
    """Return every row and column of the geometry that a binding's cell covers, in reading order."""
    return [(row, column) for row, cells in enumerate(rows) for column, item in enumerate(cells) if item.binding is binding]


def moved(*, rows, position, key):
    """Return the row and column an arrow takes the cursor to from a row and column of the geometry, or None where the arrow stops at
    an edge. The arrow passes over the rest of the cell the cursor is on, which may cover several rows or columns. A cell entered
    across the way it stretches remembers where, so that the arrow back returns to the cell the cursor came from: Arrange, several
    rows tall, entered from its side. Entered along the way it stretches, as Arrange from below, it forgets, and the cursor is at
    its first row and column."""
    row, column = position
    here = rows[row][column]
    row_step, column_step = ARROW_STEPS[key]
    while True:
        row += row_step
        column += column_step
        if not (0 <= row < len(rows) and 0 <= column < len(rows[row])):
            return None
        there = rows[row][column]
        if there.binding is not here.binding:
            break
    places = cell_positions(rows=rows, binding=there.binding)
    tall = len({place[0] for place in places}) > 1
    wide = len({place[1] for place in places}) > 1
    if (row_step and tall) or (column_step and wide):
        return places[0]
    return row, column


def arrows_between(*, rows, position, binding):
    """Return the fewest arrows that take the cursor from a row and column of the geometry to a binding's cell, for the video
    tutorial, which walks to a cell as a person would, whichever layout is drawn. None when no arrows reach it."""
    seen = {position}
    waiting = deque([(position, [])])
    while waiting:
        place, keys = waiting.popleft()
        if rows[place[0]][place[1]].binding is binding:
            return keys
        for key in ARROW_STEPS:
            there = moved(rows=rows, position=place, key=key)
            if there is not None and there not in seen:
                seen.add(there)
                waiting.append((there, [*keys, key]))
    return None


def glow_style(level):
    """Return the style of a clip's block on the map at a level of glow, from none, the monitor's green, to full, the glow's colour."""
    mixed = [round(green + (glow - green) * level / GLOW_FULL) for green, glow in zip(MONITOR_GREEN, GLOW_COLOR)]
    return RichStyle(color=Color.from_rgb(*mixed), bgcolor=Color.from_rgb(*MONITOR_BACKGROUND))


# The style of each level of glow, worked out once.
GLOW_STYLES = [glow_style(level) for level in range(GLOW_FULL + 1)]


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
        # The binding of the cell the cursor is on, which stays put while a page is open over this one and when the layout changes.
        self.chosen = self.KEYS.ARRANGE
        # The row and column of the geometry the cursor is at inside its cell, where the cell covers several: for Arrange, the row
        # it was reached from at its side, which Right goes back to. None is the cell's first row and column.
        self.position = None
        # Whether the last draw had the room for the smart fit layout, which the arrows then move over.
        self.smart_fit = False
        # How far each playing clip's block on the map glows, by its scene's number and its track, and when the glows last stepped.
        self.glow = {}
        self.glow_time = monotonic()

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
        """Return the cells by the geometry drawn, of the layout the last draw had room for."""
        return self.smart_fit_rows() if self.smart_fit else self.grid_rows()

    def grid_rows(self):
        """Return the grid layout's geometry, six rows of three, the user's layout: Arrange in the first column of the first
        three rows, with Songs and Patterns, Scales and Generators, and Grooves and Chains beside it; the Real Time switch with
        Instruments and Registers; then the bar's two rows, File/Global, Save and Open over Export, Import and Quit."""
        pages = {item.binding: item for item in self.keys()}
        keys = self.KEYS
        save, open_set, export, import_midi_here, quit_here = self.actions()
        arrange = pages[keys.ARRANGE]
        return [
            [arrange, pages[keys.SONGS], pages[keys.PATTERNS]],
            [arrange, pages[keys.SCALES], pages[keys.GENERATORS]],
            [arrange, pages[keys.GROOVES], pages[keys.CHAINS]],
            [pages[keys.REAL_TIME], pages[keys.INSTRUMENTS], pages[keys.REGISTERS]],
            [pages[keys.FILE], save, open_set],
            [export, import_midi_here, quit_here],
        ]

    def smart_fit_rows(self):
        """Return the smart fit layout's geometry, eight rows of three, the user's layout: Arrange in the first column of every row;
        beside it the Real Time switch across both of the other columns, then Songs and Patterns, Scales and Generators, Grooves and
        Chains, Instruments and Registers, then the bar's three rows, File/Global, Save and Open beside Export, Import and Quit."""
        pages = {item.binding: item for item in self.keys()}
        keys = self.KEYS
        save, open_set, export, import_midi_here, quit_here = self.actions()
        arrange = pages[keys.ARRANGE]
        return [
            [arrange, pages[keys.REAL_TIME], pages[keys.REAL_TIME]],
            [arrange, pages[keys.SONGS], pages[keys.PATTERNS]],
            [arrange, pages[keys.SCALES], pages[keys.GENERATORS]],
            [arrange, pages[keys.GROOVES], pages[keys.CHAINS]],
            [arrange, pages[keys.INSTRUMENTS], pages[keys.REGISTERS]],
            [arrange, pages[keys.FILE], export],
            [arrange, save, import_midi_here],
            [arrange, open_set, quit_here],
        ]

    def menu_items(self):
        """Return every cell the cursor can be on, each once, along the rows."""
        items = []
        for row in self.rows():
            for item in row:
                if all(item.binding is not other.binding for other in items):
                    items.append(item)
        return items

    def selected(self):
        return next(item for item in self.menu_items() if item.binding is self.chosen)

    def select(self, binding):
        """Put the cursor on the cell of a binding, at the cell's first row and column."""
        self.chosen = binding
        self.position = None

    def select_open(self):
        """Put the cursor on the Open cell, as the tracker started with no set named does, the user's ask."""
        self.select(self.KEYS.OPEN_SET_HERE)

    def row_and_column(self):
        """Return the row and column of the geometry the cursor is at: where an arrow left it inside its cell, while the layout still
        has the cell there, or else the first row and column the cell covers."""
        places = cell_positions(rows=self.rows(), binding=self.chosen)
        return self.position if self.position in places else places[0]

    def on_arrange(self):
        return self.chosen is self.KEYS.ARRANGE

    def in_bar(self):
        """Return whether the cursor is on one of the bar's actions."""
        return self.chosen is self.KEYS.FILE or any(item.binding is self.chosen for item in self.actions())

    def move_cursor(self, name):
        """Move by the geometry drawn, the user's rule: an arrow goes to the cell beside, above or below, and none goes past an edge.
        Arrange is several rows tall, so Up and Down pass through all of it, and Right from it goes back to the cell the cursor came
        from, or to the top one."""
        rows = self.rows()
        there = moved(rows=rows, position=self.row_and_column(), key=name)
        if there is None:
            return
        self.chosen = rows[there[0]][there[1]].binding
        self.position = there

    def arrows_to(self, binding):
        """Return the arrows that take the cursor to a binding's cell over the layout drawn, the fewest there are."""
        return arrows_between(rows=self.rows(), position=self.row_and_column(), binding=binding)

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

    def clock_text(self):
        """Return where the song is while it plays, for Arrange's cell, or None while it doesn't."""
        position = self.app.transport.song_position()
        return None if position is None else MSG_MAIN_CLOCK.format(at=clock(position))

    def clock_room(self):
        """Return the room Arrange's cell keeps for the clock, the longer of where the song is and how long it is, so that the cell
        is wide enough for any time and doesn't change width as the song plays (the user's rule)."""
        shown = [MSG_MAIN_CLOCK.format(at=clock(self.duration()))]
        if self.clock_text() is not None:
            shown.append(self.clock_text())
        return max(len(text) for text in shown)

    def arrange_needed_width(self, item):
        """Return how wide Arrange's cell must be: its key and name, a gap, the clock and a space before the edge."""
        return BORDERS + len(EDGE_GAP) + len(padded(item.shown_label())) + len(NAME_GAP) + len(self.shown_name(item)) + len(DETAIL_GAP) + self.clock_room() + len(EDGE_GAP)

    def column_widths(self, width):
        """Return the three columns' widths: a third of the room each, the first never narrower than Arrange's name and clock or the
        Real Time switch need, the other two sharing what the first leaves."""
        rows = self.grid_rows()
        room = max(width, MINIMUM_WIDTH) - CELL_GAP * (COLUMNS - 1)
        first = max(room // COLUMNS, self.arrange_needed_width(rows[ARRANGE_TOP][0]), *[self.needed_width(row[0]) for row in rows[ARRANGE_ROWS:]])
        other = (room - first) // (COLUMNS - 1)
        return [room - other * (COLUMNS - 1), other, other]

    def column_lefts(self, widths):
        """Return the column each of the grid's columns starts at."""
        lefts = []
        left = 0
        for width in widths:
            lefts.append(left)
            left += width + CELL_GAP
        return lefts

    def shown_name(self, item):
        """Return the name drawn on a cell: its own, but Arrange/Play on the Arrange cell while the set's Real Time switch is on,
        so that the cell says where a song is played (the user's design)."""
        if item.binding is self.KEYS.ARRANGE and self.document().setlist().is_real_time():
            return PageName.ARRANGE_PLAY
        return cell_name(item)

    def edge_style(self, item):
        """Return the style a cell's box is drawn in: its page's theme toned to the edges' brightness, or dim for a cell with none."""
        theme = CELL_THEMES.get(cell_name(item))
        if theme is None:
            return Style.DIM
        return RichStyle(color=Color.from_rgb(*themes.balanced(theme)))

    def draw_box(self, *, canvases, left, width, selected, style, fill=None):
        """Draw a box over some lines, double-lined when selected, its inside filled in a style where one is given."""
        if selected:
            top_left, rule, top_right, bottom_left, bottom_right, bar = (Box.DOUBLE_TOP_LEFT, Box.DOUBLE_RULE, Box.DOUBLE_TOP_RIGHT, Box.DOUBLE_BOTTOM_LEFT, Box.DOUBLE_BOTTOM_RIGHT, Box.DOUBLE_BAR)
        else:
            top_left, rule, top_right, bottom_left, bottom_right, bar = (Box.TOP_LEFT, Box.RULE, Box.TOP_RIGHT, Box.BOTTOM_LEFT, Box.BOTTOM_RIGHT, Box.BAR)
        inner = width - BORDERS
        canvases[0].write(column=left, text=top_left + rule * inner + top_right, style=style)
        canvases[-1].write(column=left, text=bottom_left + rule * inner + bottom_right, style=style)
        for canvas in canvases[1:-1]:
            canvas.write(column=left, text=bar, style=style)
            if fill is not None:
                canvas.write(column=left + 1, text=SPACE * inner, style=fill)
            canvas.write(column=left + width - 1, text=bar, style=style)

    def draw_cell(self, *, canvases, left, item, selected, width):
        """Draw one cell, width wide, onto its three lines: its box, double-lined and bright when selected and otherwise in its colour, the key bold and reversed, the name, bold when selected, and the count."""
        self.draw_box(canvases=canvases, left=left, width=width, selected=selected, style=Style.BOLD if selected else self.edge_style(item))
        middle = canvases[1]
        right = left + width - 1
        label = padded(item.shown_label())
        name = self.shown_name(item)
        start = left + 1 + len(EDGE_GAP)
        middle.write(column=start, text=label, style=Style.KEY)
        middle.write(column=start + len(label), text=NAME_GAP + name, style=Style.BOLD if selected else Style.PLAIN)
        count = self.count(item)
        if count is not None:
            # Right-aligned, with one space before the box's edge, or against the edge when a long name leaves no room for the space.
            name_end = start + len(label) + len(NAME_GAP) + len(name)
            middle.write(column=max(right - 1 - len(str(count)), min(name_end + len(NAME_GAP), right - len(str(count)))), text=str(count))

    def song_details(self):
        """Return the current song's scale, tempo and time signature, as Arrange's cell says them on one line."""
        song = self.document().song()
        signature = song.get_time_signature()
        return DETAIL_GAP.join([
            song.get_scale_name() or MSG_NO_SCALE,
            MSG_MAIN_TEMPO.format(tempo=tempo_text(song.get_tempo())),
            signature.to_text(),
        ])

    def song_counts(self):
        """Return how many scenes and tracks the current song has, as Arrange's cell says them."""
        song = self.document().song()
        scenes = len(song.get_scenes())
        tracks = len(song.get_track_names())
        return DETAIL_GAP.join([
            MSG_MAIN_ONE_SCENE if scenes == 1 else MSG_MAIN_SCENES.format(count=scenes),
            MSG_MAIN_ONE_TRACK if tracks == 1 else MSG_MAIN_TRACKS.format(count=tracks),
        ])

    def track_lights(self, *, lines, width):
        """Return the track lights of Arrange's cell as lines of (track or None, text): the tracks in their order, never moving, in as
        many columns as fit, two at least, and when not every track fits, how many more there are in the last place (the user's design)."""
        tracks = self.document().song().get_track_names()
        columns = max(width // LIGHT_COLUMN_WIDTH, FEWEST_LIGHT_COLUMNS)
        places = lines * columns
        shown = [(track, track) for track in tracks]
        if len(tracks) > places:
            shown = [*shown[:places - 1], (None, MSG_MAIN_MORE_TRACKS.format(count=len(tracks) - places + 1))]
        return [shown[start:start + columns] for start in range(0, len(shown), columns)], width // columns

    def bar_needed_width(self, items):
        """Return how wide a column of the bar's actions must be: the longest key, the longest name with the space that follows the
        selected one in reverse video, and the room at either side."""
        key_room = max(len(padded(item.shown_label())) for item in items)
        name_room = max(len(self.shown_name(item)) for item in items)
        return BORDERS + len(EDGE_GAP) + key_room + len(NAME_GAP) + name_room + len(EDGE_GAP)

    def smart_right_widths(self):
        """Return the widths of the smart fit layout's two columns at the right, each as narrow as its longest cell, name and count,
        or its actions in the bar, the second widened where the Real Time switch across both needs more."""
        rows = self.smart_fit_rows()
        pairs = rows[1:1 + PAGE_PAIRS]
        bar = rows[1 + PAGE_PAIRS:]
        widths = []
        for column in range(1, 1 + SMART_RIGHT_COLUMNS):
            widths.append(max(*[self.needed_width(row[column]) for row in pairs], self.bar_needed_width([row[column] for row in bar])))
        short = self.needed_width(rows[0][1]) - sum(widths) - CELL_GAP
        widths[-1] += max(short, 0)
        return widths

    def smart_arrange_width(self, width):
        """Return the width Arrange's cell has in the smart fit layout: all that the two columns at the right leave."""
        return max(width, MINIMUM_WIDTH) - sum(self.smart_right_widths()) - CELL_GAP * SMART_RIGHT_COLUMNS

    def has_room_for_smart_fit(self, *, width, height):
        """Return whether the console has the lines for the smart fit layout's right side and the width for Arrange's name and clock."""
        if height < LINES_ABOVE_GRID + SMART_RIGHT_LINES:
            return False
        return self.smart_arrange_width(width) >= self.arrange_needed_width(self.smart_fit_rows()[0][0])

    def draw_arrange(self, *, canvases, left, item, selected, width, with_map):
        """Draw Arrange's cell as a small monitor, green on dark green (the user's design): its key and name with the clock at the right
        while the song plays, the song's details and counts, and then the map of the song, in the smart fit layout, or a light for
        each track."""
        self.draw_box(canvases=canvases, left=left, width=width, selected=selected, style=Style.MONITOR_BRIGHT if selected else Style.MONITOR, fill=Style.MONITOR)
        inside = canvases[1:-1]
        start = left + 1 + len(EDGE_GAP)
        room = width - BORDERS - len(EDGE_GAP) * 2
        label = padded(item.shown_label())
        inside[NAME_LINE].write(column=start, text=label, style=Style.MONITOR_KEY)
        inside[NAME_LINE].write(column=start + len(label), text=NAME_GAP + self.shown_name(item), style=Style.MONITOR_BRIGHT)
        shown_clock = self.clock_text()
        if shown_clock is not None:
            inside[NAME_LINE].write(column=left + width - 1 - len(EDGE_GAP) - len(shown_clock), text=shown_clock, style=Style.MONITOR_BRIGHT)
        # The details start under the name, past the key.
        inside[DETAILS_LINE].write(column=start, text=fit(text=self.song_details(), width=room), style=Style.MONITOR)
        inside[COUNTS_LINE].write(column=start, text=fit(text=self.song_counts(), width=room), style=Style.MONITOR)
        if with_map:
            self.draw_map(canvases=inside[MAP_LINE:], start=start, room=room)
        else:
            self.draw_lights(canvases=inside[LIGHTS_LINE:], start=start, room=room)

    def draw_light(self, *, canvas, column, track):
        """Draw a track's light: a bright dot while a note sounds on the track, and otherwise a hollow circle, which is all a light
        is while the set's Real Time switch is off (the user's design)."""
        sounding = self.app.transport.is_track_sounding(track)
        canvas.write(column=column, text=MSG_REAL_TIME_ON_MARK if sounding else MSG_REAL_TIME_OFF_MARK, style=Style.MONITOR_BRIGHT if sounding else Style.MONITOR_DIM)

    def draw_lights(self, *, canvases, start, room):
        """Draw the grid layout's light and name for each track, in columns."""
        lights, light_width = self.track_lights(lines=len(canvases), width=room)
        for line, row in zip(canvases, lights):
            for place, (track, text) in enumerate(row):
                column = start + place * light_width
                if track is None:
                    line.write(column=column, text=fit(text=text, width=light_width), style=Style.MONITOR_DIM)
                    continue
                self.draw_light(canvas=line, column=column, track=track)
                line.write(column=column + 1, text=fit(text=NAME_GAP + text, width=light_width - LIGHT_WIDTH), style=Style.MONITOR)

    def glow_steps_due(self):
        """Return how many steps the glows should move since they last did, by the clock."""
        steps = int((monotonic() - self.glow_time) / GLOW_STEP_SECONDS)
        self.glow_time += steps * GLOW_STEP_SECONDS
        return steps

    def fade_glow(self, *, steps):
        """Move every clip's glow some steps towards full while the clip plays and towards none while it doesn't, so that a clip lights
        up and goes out slowly (the user's rule). Once nothing plays, the screen is no longer drawn again and again, so every glow is out."""
        transport = self.app.transport
        if not transport.is_playing():
            self.glow = {}
            return
        document = self.document()
        song = document.song()
        glow = {}
        for index in range(len(song.get_scenes())):
            for track in song.get_track_names():
                level = self.glow.get((index, track), 0)
                playing = transport.is_clip_playing(index=index, track=track)
                level = min(level + steps, GLOW_FULL) if playing else max(level - steps, 0)
                if level:
                    glow[(index, track)] = level
        self.glow = glow

    def glow_level(self, *, index, track):
        """Return how far the block of a track's clip in a scene glows, from 0 to GLOW_FULL."""
        return self.glow.get((index, track), 0)

    def draw_map(self, *, canvases, start, room):
        """Draw the map of the song, the user's design: a line for each track, its light and its name, then a block for each scene
        where the track has a clip and a dot where it has none, a playing clip's block glowing. A map too large shows what fits:
        the first tracks and how many more there are, and the first scenes with a mark that the line was cut."""
        self.fade_glow(steps=self.glow_steps_due())
        document = self.document()
        song = document.song()
        tracks = song.get_track_names()
        scenes = len(song.get_scenes())
        shown_tracks = tracks if len(tracks) <= len(canvases) else tracks[:len(canvases) - 1]
        name_width = min(max([len(track) for track in tracks], default=0), MAP_NAME_WIDTH)
        blocks_start = start + LIGHT_WIDTH + name_width + len(DETAIL_GAP)
        blocks_room = max(start + room - blocks_start, 0)
        shown_scenes = scenes if scenes <= blocks_room else max(blocks_room - 1, 0)
        for canvas, track in zip(canvases, shown_tracks):
            self.draw_light(canvas=canvas, column=start, track=track)
            canvas.write(column=start + LIGHT_WIDTH, text=fit(text=track, width=name_width), style=Style.MONITOR)
            for index in range(shown_scenes):
                if document.clip_slot(index=index, track=track) is None:
                    canvas.write(column=blocks_start + index, text=MSG_MAIN_MAP_EMPTY, style=Style.MONITOR_DIM)
                else:
                    canvas.write(column=blocks_start + index, text=MSG_MAIN_MAP_CLIP, style=GLOW_STYLES[self.glow_level(index=index, track=track)])
            if shown_scenes < scenes and blocks_room:
                canvas.write(column=blocks_start + shown_scenes, text=MSG_MAIN_MAP_CUT, style=Style.MONITOR_DIM)
        if len(shown_tracks) < len(tracks) and canvases:
            canvases[len(shown_tracks)].write(column=start, text=fit(text=MSG_MAIN_MORE_TRACKS.format(count=len(tracks) - len(shown_tracks)), width=room), style=Style.MONITOR_DIM)

    def draw_bar(self, *, canvases, rows, lefts, left, width):
        """Draw the bar of the file's actions: one box, double-lined while the cursor is in it, its actions in rows on the layout's
        columns with no lines between them, each column's keys ending at one place so that no key runs into a name below, and the
        selected action's name in reverse video (the user's design)."""
        selected = self.selected()
        self.draw_box(canvases=canvases, left=left, width=width, selected=self.in_bar(), style=Style.BOLD if self.in_bar() else Style.DIM)
        for column, column_left in enumerate(lefts):
            labels = [padded(row[column].shown_label()) for row in rows]
            key_room = max(len(label) for label in labels)
            start = column_left + 1 + len(EDGE_GAP)
            for canvas, row, label in zip(canvases[1:-1], rows, labels):
                item = row[column]
                canvas.write(column=start, text=fit(text=label, width=key_room, align=Align.RIGHT)[:key_room - len(label)])
                canvas.write(column=start + key_room - len(label), text=label, style=Style.KEY)
                chosen = item.binding is selected.binding
                canvas.write(column=start + key_room, text=NAME_GAP + self.shown_name(item) + (SPACE if chosen else NOTHING), style=Style.REVERSE if chosen else Style.PLAIN)

    def grid_lines(self, width):
        """Return the lines of the grid layout and the bar under it."""
        rows = self.grid_rows()
        widths = self.column_widths(width)
        lefts = self.column_lefts(widths)
        total = lefts[-1] + widths[-1]
        selected = self.selected()
        grid = [Canvas(total) for _ in range(GRID_ROWS * CELL_LINES)]
        self.draw_arrange(canvases=grid[:ARRANGE_ROWS * CELL_LINES], left=lefts[0], item=rows[ARRANGE_TOP][0], selected=self.on_arrange(), width=widths[0], with_map=False)
        for number, row in enumerate(rows[:GRID_ROWS]):
            for column, item in enumerate(row):
                if item.binding is self.KEYS.ARRANGE:
                    continue
                lines = grid[number * CELL_LINES:(number + 1) * CELL_LINES]
                self.draw_cell(canvases=lines, left=lefts[column], item=item, selected=item.binding is selected.binding, width=widths[column])
        bar = [Canvas(total) for _ in range(BAR_ROWS + BORDERS)]
        self.draw_bar(canvases=bar, rows=rows[GRID_ROWS:], lefts=lefts, left=0, width=total)
        return [canvas.text() for canvas in [*grid, *bar]]

    def smart_fit_lines(self, *, width, height):
        """Return the lines of the smart fit layout: Arrange's cell down all the height at the left, and at the right the Real Time
        switch across both columns, the pages in pairs, and the bar of the file's actions."""
        rows = self.smart_fit_rows()
        right = self.smart_right_widths()
        widths = [self.smart_arrange_width(width), *right]
        lefts = self.column_lefts(widths)
        total = lefts[-1] + widths[-1]
        selected = self.selected()
        canvases = [Canvas(total) for _ in range(max(height, SMART_RIGHT_LINES))]
        self.draw_arrange(canvases=canvases, left=lefts[0], item=rows[0][0], selected=self.on_arrange(), width=widths[0], with_map=True)
        switch = rows[0][1]
        self.draw_cell(canvases=canvases[:CELL_LINES], left=lefts[1], item=switch, selected=switch.binding is selected.binding, width=sum(right) + CELL_GAP)
        for number, row in enumerate(rows[1:1 + PAGE_PAIRS], start=1):
            lines = canvases[number * CELL_LINES:(number + 1) * CELL_LINES]
            for column in range(1, 1 + SMART_RIGHT_COLUMNS):
                self.draw_cell(canvases=lines, left=lefts[column], item=row[column], selected=row[column].binding is selected.binding, width=widths[column])
        bar_top = (1 + PAGE_PAIRS) * CELL_LINES
        bar_rows = [row[1:] for row in rows[1 + PAGE_PAIRS:]]
        self.draw_bar(canvases=canvases[bar_top:bar_top + SMART_BAR_ROWS + BORDERS], rows=bar_rows, lefts=lefts[1:], left=lefts[1], width=sum(right) + CELL_GAP)
        return [canvas.text() for canvas in canvases]

    def body(self, *, width, height):
        # Nothing above the cells: the crumbs name the set and the song, and the cells count what the set holds.
        lines = [Text(NOTHING) for _ in range(LINES_ABOVE_GRID)]
        self.smart_fit = self.has_room_for_smart_fit(width=width, height=height)
        if self.smart_fit:
            return lines + self.smart_fit_lines(width=width, height=height - LINES_ABOVE_GRID)
        return lines + self.grid_lines(width)

    def resting_status(self):
        """The status line, right above the legend as on every page, says what the selected cell is for while nothing else is said (the user's design)."""
        return self.ABOUT[cell_name(self.selected())]
