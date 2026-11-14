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
"""The status line: one message the whole tracker shares, drawn dim above the keys of every page.

A page says something with `say`, like what was saved and where, what an undo undid, or why a key
did nothing, and the line keeps it until the next key press clears it, even across a change of
page, so that a message set as a page closes is still read on the page underneath. Its messages
are lower-case fragments with no full stop, as `.claude/STYLE.md` says, since they aren't sentences.
"""

from llamatron.tui.drawing import NOTHING


class StatusLine:
    """The one message shown above the keys."""

    __slots__ = ('_text', '_refusal')

    def __init__(self):
        self._text = NOTHING
        self._refusal = False

    def say(self, text, *, refusal=False):
        """Show a message, a refusal or problem drawn in amber and anything else dim, the user's design."""
        self._text = text
        self._refusal = refusal

    def is_refusal(self):
        return self._refusal

    def text(self):
        return self._text

    def clear(self):
        self._text = NOTHING
        self._refusal = False

    def is_empty(self):
        return not self._text
