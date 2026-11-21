# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The status line: one message the whole tracker shares, drawn dim above the keys of every page.

A page says something with `say`, like what was saved and where, what an undo undid, or why a key
did nothing, and the line keeps it until the next key press clears it, even across a change of
page, so that a message set as a page closes is still read on the page underneath. Its messages
are lower-case fragments with no full stop, as `.claude/STYLE.md` says, since they aren't sentences.
"""

from llamatron.tui import drawing


class StatusLine:
    """The one message shown above the keys."""

    __slots__ = ('_text', '_refusal')

    def __init__(self):
        self._text = drawing.NOTHING
        self._refusal = False

    def say(self, text, *, refusal=False):
        """Show a message, a refusal or problem drawn in amber and anything else dim."""
        self._text = text
        self._refusal = refusal

    def is_refusal(self):
        return self._refusal

    def get_text(self):
        return self._text

    def clear(self):
        self._text = drawing.NOTHING
        self._refusal = False

    def is_empty(self):
        return not self._text
