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

"""The Help dialog, which F1 opens on every page: every key in one panel, and what the page is about in the other."""

from rich.text import Text

from llamatron.tui.dialogs.dialog import Dialog
from llamatron.tui.drawing import NOTHING, padded, SPACE, Style, wrapped
from llamatron.strings.labels import MSG_HELP_PANELS
from llamatron.strings.messages import MSG_HELP_TITLE
from llamatron.tui import keybindings


# The panel that opens first, listing the keys, and how many columns it lays them out in.
KEYS_PANEL = 0
COLUMNS = 2


class HelpDialog(Dialog):
    """Every key that works on a page, the everywhere keys above the page's own, with Tab turning to what the page is about.

    The keys panel lays each group out in two columns, filled down the first column and then the
    second, because the pattern editor's keys don't fit one column of an 80 by 24 console.
    """

    KEYS = keybindings.HelpDialog

    def __init__(self, *, where, everywhere, own, about):
        super().__init__()
        self.where = where
        self.everywhere = everywhere
        self.own = own
        self.about = about
        self.panel = KEYS_PANEL

    def heading(self, width):
        return Text(MSG_HELP_TITLE.format(where=self.where, panel=MSG_HELP_PANELS[self.panel]), style=Style.BOLD)

    def keys(self):
        return [
            self.bind(self.KEYS.CLOSE, action=lambda: self.dismiss(None)),
            self.bind(self.KEYS.OTHER_PANEL, action=self.turn),
        ]

    def turn(self):
        self.panel = (self.panel + 1) % len(MSG_HELP_PANELS)

    def lines(self, width):
        if self.panel == KEYS_PANEL:
            return [*key_columns(items=self.everywhere, width=width), Text(NOTHING), *key_columns(items=self.own, width=width)]
        return [wrapped_line for line in self.about for wrapped_line in wrapped(text=line, width=width)]


def key_columns(*, items, width):
    """Return the keys as lines of COLUMNS columns, filled down one column and then the next, each key as the main menu draws one."""
    rows = -(-len(items) // COLUMNS)
    column_width = width // COLUMNS
    lines = []
    for row in range(rows):
        line = Text(no_wrap=True)
        for column in range(COLUMNS):
            at = row + column * rows
            if at < len(items):
                line.append_text(key_cell(item=items[at], width=column_width))
        lines.append(line)
    return lines


def key_cell(*, item, width):
    """Return one key as a cell of the given width: its label in reverse video, then what it does."""
    cell = Text(no_wrap=True)
    cell.append(padded(item.shown_label()), style=Style.REVERSE)
    cell.append(SPACE + item.what)
    cell.truncate(width)
    cell.append(SPACE * (width - cell.cell_len))
    return cell
