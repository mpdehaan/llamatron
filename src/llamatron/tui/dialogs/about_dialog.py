# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The About dialog, which F2 opens on every page: the cow, the version and build date, the links, a quote and the license."""

import random
from rich.text import Text

from llamatron.model.file import version
from llamatron.model.file.version import build_year
from llamatron.tui import drawing, keybindings
from llamatron.tui.dialogs.dialog import Dialog
from llamatron.tui.drawing import wrapped
from llamatron.user_strings import about


# What the speech bubble is drawn with: its top and bottom rules, as wide as the text and the space either side of it.
BUBBLE_TOP_CHARACTER = '_'
BUBBLE_BOTTOM_CHARACTER = '-'
BUBBLE_MARGIN = 2


def cow_saying(text):
    """Return the lines of the cowsay cow with text in its speech bubble, drawn here rather than by the cowsay program."""
    rule_width = len(text) + BUBBLE_MARGIN
    return [
        about.MSG_COW_BUBBLE_TOP.format(rule=BUBBLE_TOP_CHARACTER * rule_width),
        about.MSG_COW_BUBBLE_TEXT.format(text=text),
        about.MSG_COW_BUBBLE_BOTTOM.format(rule=BUBBLE_BOTTOM_CHARACTER * rule_width),
        *about.MSG_COW,
    ]


# How often the magic eight ball answers in place of a quote.
EIGHT_BALL_CHANCE = 1 / 3
# How many lines a quote may wrap onto; up to three keep the dialog on an 80 by 24 console.
QUOTE_LINES = 4


def random_quote():
    """Return the magic eight ball's answer a third of the time, and otherwise one of the quotes, drawn from Python's own random since it isn't music."""
    if random.random() < EIGHT_BALL_CHANCE:
        return about.MSG_EIGHT_BALL.format(answer=random.choice(about.MSG_EIGHT_BALL_ANSWERS))
    return random.choice(about.MSG_ABOUT_QUOTES)


class AboutDialog(Dialog):
    """The cow saying the program's name, the version and when it was built, the links, a quote chosen as it opens, and the license.

    The lines are laid out in this order: the cow with its caption and the version
    straight under it, the links, and the quote set off by a blank line above and below, which is
    all that fits an 80 by 24 console.
    """

    KEYS = keybindings.AboutDialog

    def __init__(self, *, name):
        super().__init__()
        # The title is set after Textual's own set-up, which gives every screen a blank one.
        self.title = about.MSG_ABOUT_TITLE
        # Textual's screens have a name of their own, so the one the cow says is kept apart.
        self.shown_name = name
        self.quote = random_quote()

    def keys(self):
        return [self.bind(self.KEYS.CLOSE, action=lambda: self.dismiss(None))]

    def quote_lines(self, width):
        """Return the quote wrapped to the dialog's width, on up to QUOTE_LINES lines."""
        return [line.plain for line in wrapped(text=self.quote, width=width)[:QUOTE_LINES]]

    def lines(self, width):
        quote = self.quote_lines(width)
        # The dialog is exactly 24 lines with a one-line quote, so the blank line below the quote gives way when the quote wraps onto two lines, and the one above when it wraps onto three.
        above = [drawing.NOTHING] if len(quote) <= 2 else []
        below = [drawing.NOTHING] if len(quote) == 1 else []
        words = [
            *cow_saying(self.shown_name),
            about.MSG_ABOUT_POWERED,
            about.MSG_ABOUT_VERSION.format(version=version.VERSION, date=version.BUILD_DATE, time=version.BUILD_TIME),
            about.MSG_ABOUT_WEB,
            about.MSG_ABOUT_BLOG,
            about.MSG_ABOUT_MORE.format(site=about.MSG_SITE),
            *above,
            *quote,
            *below,
            about.MSG_ABOUT_LICENSE,
            about.MSG_ABOUT_COPYRIGHT.format(year=build_year()),
        ]
        return [Text(line, no_wrap=True) for line in words]
