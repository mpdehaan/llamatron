# llamatron: a Python language and framework for producing MIDI clips.
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

"""What every screen has in common: one drawing, and one table of keys.

A screen's keys are listed once, in keys(), and that list both handles them and draws them, so no
key can work without being shown. Everything is drawn with bold, dim, reverse video and box
characters instead of color, so that it suits any terminal background.
"""

from dataclasses import dataclass
from typing import Callable

from rich.text import Text
from textual.containers import Container
from textual.screen import ModalScreen, Screen
from textual.widgets import Static

from llamatron.tui.document import clock

KEY_NAMES = {
    'tab': 'Tab', 'enter': 'Enter', 'backspace': 'Bksp', 'space': 'Space',
    'up': '↑', 'down': '↓', 'left': '←', 'right': '→',
}
_NAMED_KEYS = {'tab', 'enter', 'backspace', 'up', 'down', 'left', 'right'}
ARROWS_UP_DOWN = ('up', 'down')
TITLE = 'llamatron'
# Shown at the bottom right of the main screen.
SITE = 'home.laserllama.net'
ARROWS = ('left', 'right', 'up', 'down')


@dataclass
class Key:
    """One key or group of keys, what it's called on screen, and what it does."""

    keys: tuple
    what: str
    action: Callable
    label: str = None
    wants_key: bool = False

    def shown_label(self):
        if self.label:
            return self.label
        return ''.join(KEY_NAMES.get(key, key.upper()) for key in self.keys)


def key(which, what, action, label=None, wants_key=False):
    keys = (which,) if isinstance(which, str) else tuple(which)
    return Key(keys, what, action, label, wants_key)


def pressed_key(event):
    """Return a key press as one name: upper and lower case are the same, and so are both deletes."""
    name = event.key
    if name == 'delete':
        return 'backspace'
    if name in _NAMED_KEYS:
        return name
    if name == 'space' or event.character == ' ':
        return 'space'
    if event.character and event.character.isprintable():
        return event.character.lower()
    return None


def fit(text, width, align='left'):
    """Return text cut or padded to exactly a width."""
    text = str(text)
    if len(text) > width:
        return text[:max(width - 1, 0)] + '…' if width > 0 else ''
    if align == 'right':
        return text.rjust(width)
    if align == 'center':
        return text.center(width)
    return text.ljust(width)


def columns(rows):
    """Return one line for each (name, description) pair, with the descriptions lined up."""
    widest = max((len(name) for name, _ in rows), default=0)
    return [f'{name.ljust(widest)}  {description}'.rstrip() for name, description in rows]


def legend(keys, width):
    """Return lines showing every key, each as a reversed label followed by what it does."""
    lines, line = [], Text(' ')
    for item in keys:
        label = f' {item.shown_label()} '
        size = len(label) + 1 + len(item.what) + 2
        if line.cell_len + size > width and line.cell_len > 1:
            lines.append(line)
            line = Text(' ')
        line.append(label, style='reverse')
        line.append(f' {item.what}  ')
    lines.append(line)
    return lines


class Page(Screen):
    """A full screen, drawn as one piece of text."""

    crumbs = ()
    # A screen that draws its keys itself turns this off.
    shows_legend = True
    # What the H key shows, as short lines that have to fit an 80 by 24 console.
    HELP = ()

    def __init__(self, document_holder):
        super().__init__()
        self.holder = document_holder
        self.status = ''

    @property
    def document(self):
        return self.holder.document

    def compose(self):
        yield Static(id='view')

    def on_mount(self):
        self.draw()

    def on_screen_resume(self):
        self.draw()

    def on_resize(self):
        self.draw()

    def keys(self):
        """Return this screen's keys, which can change with what's under the cursor."""
        return []

    def key_table(self):
        """Return this screen's keys, along with the help key that every page has."""
        return [*self.keys(), key('h', 'Help', self.show_help)]

    def show_help(self):
        self.tell(f"Help: {' › '.join(self.crumbs) or 'llamatron'}", *self.HELP)

    def body(self, width, height):
        """Return the lines between the header and the keys."""
        return []

    def duration(self):
        """Return the seconds to show in the header, None if unknown, or False to show nothing."""
        return False

    def on_key(self, event):
        event.stop()
        event.prevent_default()
        name = pressed_key(event)
        if name is None:
            return
        for item in self.key_table():
            if name in item.keys:
                self.status = ''
                if item.wants_key:
                    item.action(name)
                else:
                    item.action()
                self.draw()
                return

    def go_back(self):
        self.app.pop_screen()

    def show_page(self, page):
        self.app.push_screen(page)

    def ask(self, dialog, then):
        """Show a dialog, and pass its answer to a function unless it was cancelled."""
        def answered(result):
            if result is not None:
                then(result)
            self.draw()
        self.app.push_screen(dialog, answered)

    def tell(self, title, *lines):
        self.app.push_screen(MessageDialog(title, list(lines)))

    def header(self, width):
        crumbs = ' › '.join([TITLE, *self.crumbs])
        parts = []
        seconds = self.duration()
        if seconds is not False:
            parts.append(clock(seconds))
        parts.append(self.document.name + (' ● unsaved' if self.document.dirty else ''))
        right = ' │ '.join(parts) + ' '
        line = Text(no_wrap=True)
        line.append(' ' + fit(crumbs, max(width - len(right) - 2, 1)), style='bold')
        line.append(' ')
        line.append(right, style='bold')
        return [line, Text('━' * width)]

    def draw(self):
        if not self.is_attached or not self.query('#view'):
            return
        width, height = self.size
        if width <= 0 or height <= 0:
            return
        top = self.header(width)
        bottom = legend(self.key_table(), width) if self.shows_legend else []
        rule = [Text('─' * width, style='dim')] if bottom else []
        status = Text(' ' + fit(self.status, width - 1), style='bold')
        room = max(height - len(top) - len(rule) - len(bottom) - 1, 1)
        lines = self.body(width, room)[:room]
        lines += [Text('') for _ in range(room - len(lines))]
        # A line that wrapped would push the keys off the bottom of the screen.
        for line in lines:
            line.truncate(width, overflow='ellipsis')
        self.query_one('#view', Static).update(Text('\n').join([*top, *lines, status, *rule, *bottom]))


class Dialog(ModalScreen):
    """A box in the middle of the screen, with its keys inside it."""

    title = ''

    def compose(self):
        with Container(id='dialog'):
            yield Static(id='dialog-view')

    def on_mount(self):
        self.draw()

    def on_resize(self):
        self.draw()

    def keys(self):
        return []

    def key_table(self):
        return self.keys()

    def lines(self, width):
        return []

    def draw(self):
        if not self.is_attached or not self.query('#dialog-view'):
            return
        width = min(self.app.size.width - 4, 70)
        inner = width - 4
        result = [Text(self.title, style='bold'), Text('')]
        result += self.lines(inner)
        result += [Text(''), *legend(self.keys(), inner)]
        boxed = [Text('┏' + '━' * (width - 2) + '┓')]
        for line in result:
            padded = Text('┃ ')
            padded.append_text(line)
            padded.append(' ' * max(inner - line.cell_len, 0))
            padded.append(' ┃')
            boxed.append(padded)
        boxed.append(Text('┗' + '━' * (width - 2) + '┛'))
        self.query_one('#dialog-view', Static).update(Text('\n').join(boxed))

    def on_key(self, event):
        event.stop()
        event.prevent_default()
        name = pressed_key(event)
        if name is None:
            return
        for item in self.keys():
            if name in item.keys:
                if item.wants_key:
                    item.action(name)
                else:
                    item.action()
                if self.is_attached:
                    self.draw()
                return
        self.other_key(event)

    def other_key(self, event):
        pass



def _wrap(text, width):
    lines, line = [], ''
    for word in str(text).split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(Text(line))
            line = word
        else:
            line = f'{line} {word}' if line else word
    lines.append(Text(line))
    return lines


class MessageDialog(Dialog):

    def __init__(self, title, messages):
        super().__init__()
        self.title = title
        self.messages = messages

    def keys(self):
        return [key(('enter', 'tab'), 'close', lambda: self.dismiss(None), label='Enter')]

    def lines(self, width):
        result = []
        for message in self.messages:
            result += _wrap(message, width)
        return result


class ConfirmDialog(MessageDialog):
    """Answers True for yes. Anything else that closes it counts as no."""

    def keys(self):
        return [
            key('y', 'yes', lambda: self.dismiss(True)),
            key('n', 'no', lambda: self.dismiss(None)),
            key('tab', 'cancel', lambda: self.dismiss(None)),
        ]


class PromptDialog(Dialog):
    """Asks for a line of text, and answers with it."""

    def __init__(self, title, value=''):
        super().__init__()
        self.title = title
        self.value = str(value)

    def keys(self):
        return [
            key('enter', 'done', lambda: self.dismiss(self.value)),
            key('backspace', 'erase', self.erase),
            key('tab', 'cancel', lambda: self.dismiss(None)),
        ]

    def erase(self):
        self.value = self.value[:-1]

    def lines(self, width):
        line = Text('› ' + self.value[-(width - 3):])
        line.append(' ', style='reverse')
        return [line]

    def other_key(self, event):
        if event.character and event.character.isprintable():
            self.value += event.character
            self.draw()

    def on_key(self, event):
        # Letters are text here, so only the named keys are handled by the table.
        event.stop()
        event.prevent_default()
        name = pressed_key(event)
        for item in self.keys():
            if name in item.keys:
                item.action()
                if self.is_attached:
                    self.draw()
                return
        self.other_key(event)


class ChoiceDialog(Dialog):
    """Offers a list to pick from, and answers with the chosen item's place in it."""

    SHOWN = 12

    def __init__(self, title, options, current=0):
        super().__init__()
        self.title = title
        self.options = list(options)
        self.place = max(min(current, len(self.options) - 1), 0)

    def keys(self):
        return [
            key(ARROWS_UP_DOWN, 'move', self.move, wants_key=True),
            key('enter', 'choose', lambda: self.dismiss(self.place)),
            key('tab', 'cancel', lambda: self.dismiss(None)),
        ]

    def move(self, name):
        self.place = (self.place + (-1 if name == 'up' else 1)) % max(len(self.options), 1)

    def lines(self, width):
        start = max(min(self.place - self.SHOWN // 2, len(self.options) - self.SHOWN), 0)
        result = []
        for place in range(start, min(start + self.SHOWN, len(self.options))):
            style = 'reverse' if place == self.place else ''
            result.append(Text(fit(f' {self.options[place]}', width), style=style))
        return result


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
    """

    def __init__(self, title, options, grid, current=0, details=None, top=()):
        super().__init__(title, options, current)
        width = max((len(cells) for cells in grid), default=1)
        top_row = [*top, *[None] * (width - len(top))]
        # Navigation works on one grid, with the top line as its first row when there is one.
        self.top = list(top)
        self.cells = ([top_row] if top else []) + [list(cells) + [None] * (width - len(cells)) for cells in grid]
        self.grid = grid
        self.details = details

    def keys(self):
        return [
            key(ARROWS, 'move', self.move, label='←↑↓→', wants_key=True),
            key('enter', 'choose', lambda: self.dismiss(self.place)),
            key('tab', 'cancel', lambda: self.dismiss(None)),
        ]

    def option_at(self, row, column):
        cell = self.cells[row][column]
        return None if cell is None or isinstance(cell, Heading) else cell

    def where(self):
        for row in range(len(self.cells)):
            for column in range(len(self.cells[row])):
                if self.option_at(row, column) == self.place:
                    return row, column
        return 0, 0

    def move(self, name):
        row, column = self.where()
        width = len(self.cells[0])
        if name in ('up', 'down'):
            step = -1 if name == 'up' else 1
            others = list(range(row + step, -1 if step < 0 else len(self.cells), step))
            # Keep to the column, or else take the nearest option in any column, like the top line.
            for search in (column, *range(width)):
                for other in others:
                    found = self.option_at(other, search)
                    if found is not None:
                        self.place = found
                        return
            return
        step = -1 if name == 'left' else 1
        for offset in range(1, width + 1):
            target = (column + step * offset) % width
            nearest = sorted((abs(other - row), other) for other in range(len(self.cells)) if self.option_at(other, target) is not None)
            if nearest:
                self.place = self.option_at(nearest[0][1], target)
                return

    def column_widths(self):
        sizes = [0] * len(self.cells[0])
        for cells in self.grid:
            for column, cell in enumerate(cells):
                if cell is not None:
                    sizes[column] = max(sizes[column], len(cell if isinstance(cell, Heading) else str(self.options[cell])))
        return [size + 3 for size in sizes]

    def option_text(self, place, size):
        text = Text(no_wrap=True)
        text.append(f' {self.options[place]} ', style='reverse' if place == self.place else '')
        text.append(' ' * max(size - len(str(self.options[place])) - 2, 0))
        return text

    def lines(self, width):
        sizes = self.column_widths()
        result = []
        if self.top:
            line = Text(no_wrap=True)
            for place in self.top:
                line.append_text(self.option_text(place, 0))
                line.append(' ')
            result += [line, Text('')]
        for cells in self.grid:
            line = Text(no_wrap=True)
            for column, cell in enumerate(cells):
                size = sizes[column]
                if cell is None:
                    line.append(' ' * size)
                elif isinstance(cell, Heading):
                    line.append(fit(f' {cell}', size), style='bold')
                else:
                    line.append_text(self.option_text(cell, size))
            result.append(line)
        if self.details is not None:
            result += [Text(''), Text(fit(self.details(self.place), width))]
        return result
