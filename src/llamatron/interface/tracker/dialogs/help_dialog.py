# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Help dialog, which F1 opens on every page: every key in one panel, and what the page is about in the other."""

from rich.text import Text

from llamatron.interface.forms.dialogs import blank, said
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.dialogs.dialog import Dialog
from llamatron.interface.tracker.drawing import Style
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
            return [*dialog_renderer.key_columns(items=self.everywhere, width=width, columns=COLUMNS), *dialog_renderer.said_lines(paragraphs=[blank()], width=width),
                    *dialog_renderer.key_columns(items=self.own, width=width, columns=COLUMNS)]
        return dialog_renderer.said_lines(paragraphs=[said(line) for line in self.about], width=width)
