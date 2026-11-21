# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Main page: a button for every page and the file's actions, with a double-lined box around what the cursor is on.

One block of buttons, the same size on every console and at the top left, never stretched to the window:
Arrange, where most of the work happens, is a bar across the top, as wide as the three columns under it. Under it, three rows
of three, in the order a song is made: Songs, Patterns and Scales; Generators, Chains and Grooves; Instruments, Registers and
the Real Time switch. Then a blank line, and one bar as wide as the grid with the file's six actions in two rows on the grid's
own columns, with no lines between them: Open over Save, Import over Export, File/Global over Quit, each column's keys under
the keys of the buttons above and its names starting at one place. Each page's button is boxed in its page's theme colour
(tui/themes.py), toned to one brightness, and the rest in a dim box; the selected button's box is double-lined and bright,
and in the bar the selected action is in reverse video inside the bar's double-lined box. A button says how many of its
things the set has where that means something. The status line stays empty here but for a refusal or a warning, and the
theme's stripe carries no caption, since the crumbs already name the screen. While the song plays, the header's second line
shows the play mark and the clock beside the song's length. The arrows move by the geometry drawn and stop at every edge.
Undo and Redo have no button, since they're Ctrl+Z and Ctrl+Y everywhere, and F1 and F3 are in the footer, so that this
screen is the one place that reminds of them.
"""

from collections import deque
from rich.color import Color
from rich.style import Style as RichStyle
from rich.text import Text

from llamatron.model.objects.sections import Section
from llamatron.tui import drawing, keybindings, themes
from llamatron.tui.drawing import Box, Canvas, padded, Style
from llamatron.tui.keys import Key
from llamatron.tui.screens.arrange.arrange_page import ArrangePage
from llamatron.tui.screens.generators.generators_page import GeneratorsPage
from llamatron.tui.screens.pattern.patterns_page import PatternsPage
from llamatron.tui.screens.set.file_page import FilePage
from llamatron.tui.screens.set.grooves_page import GroovesPage
from llamatron.tui.screens.set.importing import import_midi
from llamatron.tui.screens.set.instruments_page import InstrumentsPage
from llamatron.tui.screens.set.registers_page import RegistersPage
from llamatron.tui.screens.set.scales_page import ScalesPage
from llamatron.tui.screens.set.songs_page import SongsPage
from llamatron.tui.screens.shared.everywhere import everywhere_actions, everywhere_key, quit_key
from llamatron.tui.screens.shared.page import Page
from llamatron.user_strings import errors, help as help_text, labels as labels_text, marks, messages


# The grid: three columns, a space between them, this wide in all on every console, never widened to the window.
COLUMNS = 3
GRID_WIDTH = 80
CELL_GAP = 1
# Between the box's left edge and the key, and between the key and the name, and the borders either side.
EDGE_GAP = drawing.SPACE
NAME_GAP = drawing.SPACE
BORDERS = 2
# A cell's three lines: its top edge, its key and name, and its bottom edge.
CELL_LINES = 3
# The rows of the geometry: Arrange's bar, three rows of buttons, and the two rows of actions in the bar under them.
ARRANGE_ROW = 0
BUTTON_ROWS = 3
BAR_ROWS = 2
# Blank lines over the buttons, and between the buttons and the bar of the file's actions.
LINES_ABOVE_GRID = 1
LINES_ABOVE_BAR = 1
# How far each arrow moves the cursor over the grid, in rows and columns.
ARROW_STEPS = {Key.UP: (-1, 0), Key.DOWN: (1, 0), Key.LEFT: (0, -1), Key.RIGHT: (0, 1)}
# The colour each page's cell is boxed in, its page's theme toned to the edges' one brightness; a cell with none is boxed dim.
CELL_THEMES = {
    labels_text.PageName.SONGS: themes.SONGS, labels_text.PageName.PATTERNS: themes.PATTERNS, labels_text.PageName.GENERATORS: themes.GENERATORS,
    labels_text.PageName.SCALES: themes.SCALES, labels_text.PageName.GROOVES: themes.GROOVES, labels_text.PageName.INSTRUMENTS: themes.INSTRUMENTS, labels_text.PageName.REGISTERS: themes.REGISTERS, labels_text.PageName.DRAWS: themes.DRAWS,
    labels_text.PageName.FILE: themes.SET_FILE,
}
# The pages whose cell counts the set's things, by the section counted. Generators and Grooves are counted on their own.
COUNTED_SECTIONS = {
    labels_text.PageName.SONGS: Section.SONGS, labels_text.PageName.PATTERNS: Section.PATTERNS, labels_text.PageName.SCALES: Section.SCALES,
    labels_text.PageName.INSTRUMENTS: Section.INSTRUMENTS,
}
# What each action cell in the row under the pages is called: Save by its everywhere key, Open and Export by the main screen's own letters.
ACTION_NAMES = {
    keybindings.Page.SAVE: labels_text.PageName.SAVE, keybindings.MainPage.OPEN_SET_HERE: labels_text.PageName.OPEN, keybindings.MainPage.EXPORT_HERE: labels_text.PageName.EXPORT,
    keybindings.MainPage.IMPORT_HERE: labels_text.PageName.IMPORT, keybindings.MainPage.QUIT: labels_text.PageName.QUIT,
}


def cell_name(item):
    """Return what a cell is called: the page its key opens, or the name of the action."""
    return ACTION_NAMES.get(item.binding, item.what)


class EmptyCell:
    """A place in the grid with no button: drawn as nothing, never selected, and passed over by the arrows."""

    __slots__ = ()

    # No key opens it.
    binding = None


# The one empty cell of the grid, where a page may go later.
EMPTY_CELL = EmptyCell()


def cell_opened_by(key):
    """Return the name of the cell a key opens on the main screen, a page or an action, or None for a key that opens none."""
    for binding in [*keybindings.MainPage.PAGES, *ACTION_NAMES]:
        if binding.keys == key:
            return ACTION_NAMES.get(binding, binding.what)
    return None


def cell_positions(*, rows, binding):
    """Return every row and column of the geometry that a binding's cell covers, in reading order."""
    return [(row, column) for row, cells in enumerate(rows) for column, item in enumerate(cells) if item.binding is binding]


def moved(*, rows, position, key):
    """Return the row and column an arrow takes the cursor to from a row and column of the geometry, or None where the arrow stops at
    an edge. The arrow passes over the rest of the cell the cursor is on, which may cover several rows or columns. A cell entered
    across the way it stretches remembers where, so that the arrow back returns to the cell the cursor came from: Arrange, three
    columns wide, entered from below. Entered along the way it stretches it forgets, and the cursor is at its first row and
    column."""
    row, column = position
    here = rows[row][column]
    row_step, column_step = ARROW_STEPS[key]
    while True:
        row += row_step
        column += column_step
        if not (0 <= row < len(rows) and 0 <= column < len(rows[row])):
            return None
        there = rows[row][column]
        # An empty cell is passed over, as if the cells either side of it touched.
        if there.binding is not here.binding and there is not EMPTY_CELL:
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


class MainPage(Page):
    """The menu: a grid of cells, the pages and then the actions, with a cursor the arrows move and Enter follows, beside the letters."""

    THEME = themes.MAIN_SCREEN
    KEYS = keybindings.MainPage

    # The header's second line is the crumbs, and the main screen is the start of every trail, so the line says so rather than standing blank.
    crumbs = (labels_text.Crumb.MAIN_SCREEN,)
    HELP = help_text.HELP_MAIN_PAGE

    def __init__(self, holder):
        super().__init__(holder)
        # The binding of the cell the cursor is on, which stays put while a page is open over this one and when the layout changes.
        self.chosen = self.KEYS.ARRANGE
        # The row and column of the geometry the cursor is at inside its cell, where the cell covers several: for Arrange, the
        # column it was reached from below, which Down goes back to. None is the cell's first row and column.
        self.position = None

    def keys(self):
        return [
            self.bind(self.KEYS.FILE, action=lambda: self.show_page(FilePage(self.holder))),
            self.bind(self.KEYS.SONGS, action=lambda: self.show_page(SongsPage(self.holder))),
            self.bind(self.KEYS.PATTERNS, action=lambda: self.show_page(PatternsPage(self.holder))),
            self.bind(self.KEYS.GENERATORS, action=lambda: self.show_page(GeneratorsPage(self.holder))),
            self.bind(self.KEYS.SCALES, action=lambda: self.show_page(ScalesPage(self.holder))),
            self.bind(self.KEYS.GROOVES, action=lambda: self.show_page(GroovesPage(self.holder))),
            self.bind(self.KEYS.INSTRUMENTS, action=lambda: self.show_page(InstrumentsPage(self.holder))),
            self.bind(self.KEYS.REGISTERS, action=lambda: self.show_page(RegistersPage(self.holder))),
            self.bind(self.KEYS.DRAWS, action=lambda: self.show_page(self.app.section_page_of(Section.DRAWS)(self.holder))),
            self.bind(self.KEYS.ARRANGE, action=lambda: self.show_page(ArrangePage(self.holder))),
            # The Real Time switch sits among the pages as a cell of its own, with its mark where a page's cell has its count.
            self.bind(self.KEYS.REAL_TIME, action=self.toggle_real_time),
        ]

    def toggle_real_time(self):
        """Turn real-time playback on or off, which needs an instrument to play through, and say which on the status line."""
        document = self.document()
        if not document.get_setlist().get_instrument_names():
            self.tell(errors.ERR_NO_INSTRUMENTS_TITLE, errors.ERR_ADD_INSTRUMENT_FIRST)
            return
        on = not document.get_setlist().is_real_time()
        document.change(document.get_setlist().set_real_time, on)
        if not on and self.app.transport.is_playing():
            # Arrange shows no stop with Real Time off, so turning it off stops what plays, which was once a bug.
            self.app.transport.stop_all()
            self.say(messages.MSG_REAL_TIME_OFF_STOPPED)
            return
        self.say(messages.MSG_REAL_TIME_ON if on else messages.MSG_REAL_TIME_OFF)

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
        """Return the cells by the geometry drawn, six rows of three: Arrange across the first row; Songs,
        Patterns and Scales; Generators, Draws and Grooves; Instruments, Registers and the Real Time switch; then the bar's two
        rows, Open, Import and File/Global over Save, Export and Quit."""
        pages = {item.binding: item for item in self.keys()}
        keys = self.KEYS
        save, open_set, export, import_midi_here, quit_here = self.actions()
        arrange = pages[keys.ARRANGE]
        return [
            [arrange, arrange, arrange],
            [pages[keys.SONGS], pages[keys.PATTERNS], pages[keys.SCALES]],
            [pages[keys.GENERATORS], pages[keys.DRAWS], pages[keys.GROOVES]],
            [pages[keys.INSTRUMENTS], pages[keys.REGISTERS], pages[keys.REAL_TIME]],
            [open_set, import_midi_here, pages[keys.FILE]],
            [save, export, quit_here],
        ]

    def menu_items(self):
        """Return every cell the cursor can be on, each once, along the rows."""
        items = []
        for row in self.rows():
            for item in row:
                if item is not EMPTY_CELL and all(item.binding is not other.binding for other in items):
                    items.append(item)
        return items

    def selected(self):
        return next(item for item in self.menu_items() if item.binding is self.chosen)

    def select(self, binding):
        """Put the cursor on the cell of a binding, at the cell's first row and column."""
        self.chosen = binding
        self.position = None

    def select_open(self):
        """Put the cursor on the Open cell, as the tracker started with no set named does."""
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
        """Move by the geometry drawn: an arrow goes to the cell beside, above or below, and none goes past an edge.
        Arrange is three columns wide, so Left and Right stay on it, and Down from it goes back to the button the cursor came
        from, or to the first one."""
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

    def time_text(self):
        """Return the time at the right of the header: where the song is while it plays, and how long it is, or its length alone,
        the one thing here that says a song plays on."""
        return self.playing_clock() or super().time_text()

    def caption(self):
        """The theme's stripe carries no words here: the crumbs already name the main screen, and the name shows once."""
        return drawing.NOTHING

    def count(self, item):
        """Return what a cell shows at its right: how many of its things a page has, the Real Time switch's mark, or None where a count means nothing: File, Registers, Arrange and the actions."""
        setlist = self.document().get_setlist()
        name = cell_name(item)
        if name == labels_text.PageName.REAL_TIME:
            return marks.MSG_REAL_TIME_ON_MARK if setlist.is_real_time() else marks.MSG_REAL_TIME_OFF_MARK
        if name == labels_text.PageName.GENERATORS:
            return len(setlist.every_generator_name())
        if name == labels_text.PageName.GROOVES:
            # The set's own grooves: the factory ones are always there, so counting them would say nothing.
            return len(setlist.get_own_groove_names())
        if name in COUNTED_SECTIONS:
            return len(setlist.get_item_names(COUNTED_SECTIONS[name]))
        return None

    def column_widths(self):
        """Return the three columns' widths, which share the grid's width, the first taking what a division leaves over."""
        room = GRID_WIDTH - CELL_GAP * (COLUMNS - 1)
        other = room // COLUMNS
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
        so that the cell says where a song is played."""
        if item.binding is self.KEYS.ARRANGE and self.document().get_setlist().is_real_time():
            return labels_text.PageName.ARRANGE_PLAY
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
                canvas.write(column=left + 1, text=drawing.SPACE * inner, style=fill)
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

    def draw_bar(self, *, canvases, rows, lefts, left, width):
        """Draw the bar of the file's actions: one box, double-lined while the cursor is in it, its actions in rows on the grid's
        columns with no lines between them, each column's keys starting under the keys of the buttons above and its names starting
        at one place, past the column's longest key, and the selected action's name in reverse video."""
        selected = self.selected()
        self.draw_box(canvases=canvases, left=left, width=width, selected=self.in_bar(), style=Style.BOLD if self.in_bar() else Style.DIM)
        for column, column_left in enumerate(lefts):
            labels = [padded(row[column].shown_label()) for row in rows]
            key_room = max(len(label) for label in labels)
            start = column_left + 1 + len(EDGE_GAP)
            for canvas, row, label in zip(canvases[1:-1], rows, labels):
                item = row[column]
                canvas.write(column=start, text=label, style=Style.KEY)
                chosen = item.binding is selected.binding
                canvas.write(column=start + key_room, text=NAME_GAP + self.shown_name(item) + (drawing.SPACE if chosen else drawing.NOTHING), style=Style.REVERSE if chosen else Style.PLAIN)

    def body(self, *, width, height):
        """Return the block of buttons, the same on every console: Arrange's bar, the three rows of buttons, a blank line and the bar of the file's actions."""
        rows = self.rows()
        widths = self.column_widths()
        lefts = self.column_lefts(widths)
        total = lefts[-1] + widths[-1]
        selected = self.selected()
        grid = [Canvas(total) for _ in range((1 + BUTTON_ROWS) * CELL_LINES)]
        self.draw_cell(canvases=grid[:CELL_LINES], left=0, item=rows[ARRANGE_ROW][0], selected=self.on_arrange(), width=total)
        for number, row in enumerate(rows[1:1 + BUTTON_ROWS], start=1):
            lines = grid[number * CELL_LINES:(number + 1) * CELL_LINES]
            for column, item in enumerate(row):
                if item is not EMPTY_CELL:
                    self.draw_cell(canvases=lines, left=lefts[column], item=item, selected=item.binding is selected.binding, width=widths[column])
        bar = [Canvas(total) for _ in range(BAR_ROWS + BORDERS)]
        self.draw_bar(canvases=bar, rows=rows[1 + BUTTON_ROWS:], lefts=lefts, left=0, width=total)
        blank = [Text(drawing.NOTHING)]
        return blank * LINES_ABOVE_GRID + [canvas.text() for canvas in grid] + blank * LINES_ABOVE_BAR + [canvas.text() for canvas in bar]
