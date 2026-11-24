# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Help dialog, which F1 opens on every page: every key in one panel, and what the page is about in the other."""

from rich.text import Text

from llamatron.interface.forms.dialogs import said
from llamatron.interface.tracker import drawing, keybindings
from llamatron.interface.tracker.dialogs.dialog import Dialog
from llamatron.interface.tracker.drawing import padded, Style
from llamatron.interface.tracker.renderers import dialogs as dialog_renderer
from llamatron.user_strings import labels, messages


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
        return Text(messages.MSG_HELP_TITLE.format(where=self.where, panel=labels.MSG_HELP_PANELS[self.panel]), style=Style.BOLD)

    def keys(self):
        return [
            self.bind(self.KEYS.CLOSE, action=lambda: self.dismiss(None)),
            self.bind(self.KEYS.OTHER_PANEL, action=self.turn),
        ]

    def turn(self):
        self.panel = (self.panel + 1) % len(labels.MSG_HELP_PANELS)

    def lines(self, width):
        if self.panel == KEYS_PANEL:
            return [*key_columns(items=self.everywhere, width=width), Text(drawing.NOTHING), *key_columns(items=self.own, width=width)]
        return dialog_renderer.said_lines(paragraphs=[said(line) for line in self.about], width=width)


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
    cell.append(drawing.SPACE + item.what)
    cell.truncate(width)
    cell.append(drawing.SPACE * (width - cell.cell_len))
    return cell
