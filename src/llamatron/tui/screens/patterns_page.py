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

"""The Patterns page."""

from llamatron.composition.file_format import Section
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.composition.naming import unique_name
from llamatron.tui.text import clock
from llamatron.tui.drawing import Align
from llamatron.strings.help import HELP_PATTERNS_PAGE
from llamatron.tui.screens.listening import pattern_listen_keys
from llamatron.tui.screens.named_list_page import NamedListPage
from llamatron.tui.screens.pattern_editor import PatternEditor
from llamatron.strings.errors import ERR_NAME_EMPTY_OR_IN_USE
from llamatron.strings.labels import Column, Crumb, MSG_DRUM_KIND, MSG_NOTES_KIND
from llamatron.strings.legends import MSG_PATTERN_WHAT
from llamatron.strings.messages import MSG_NEW_PATTERN_PROMPT, MSG_RENAME_PATTERN_PROMPT
from llamatron.strings.names import MSG_NEW_PATTERN_NAME
from llamatron.tui import keybindings


class PatternsPage(NamedListPage):

    KEYS = keybindings.PatternsPage
    LISTED_SECTION = Section.PATTERNS
    RENAME_PROMPT = MSG_RENAME_PATTERN_PROMPT
    WHAT = MSG_PATTERN_WHAT
    crumbs = (Crumb.PATTERNS,)
    HELP = HELP_PATTERNS_PAGE
    columns = (
        (Column.SELECT_PATTERN, None, Align.LEFT), (Column.TYPE, 5, Align.LEFT), (Column.STEPS, 5, Align.RIGHT), (Column.TIME, 6, Align.RIGHT),
        (Column.USED, 4, Align.RIGHT),
    )

    def rows(self):
        document = self.document()
        song = self.document().song()
        return [(name, self.row_of(name=name, pattern=song.get_pattern(name), document=document)) for name in self.names()]

    def row_of(self, *, name, pattern, document):
        kind = MSG_DRUM_KIND if pattern.is_drum() else MSG_NOTES_KIND
        return [name, kind, pattern.get_steps(), clock(document.lengths().pattern_seconds(name)), len(self.uses(name))]

    def item_keys(self):
        """Return the list's keys and Listen, which plays the selected pattern at once and stops it (the user's design)."""
        return [*super().item_keys(), *pattern_listen_keys(page=self, pattern=self.current())]

    def open_item(self):
        self.show_page(PatternEditor(holder=self.holder, name=self.current()))

    def add(self):
        patterns = self.names()
        default = unique_name(base=MSG_NEW_PATTERN_NAME.format(number=len(patterns) + 1), taken=patterns)

        def named(text):
            text = text.strip()
            if not text or text in patterns:
                self.refuse(ERR_NAME_EMPTY_OR_IN_USE)
                return
            self.document().add_pattern(name=text)
            self.put_cursor_on(text)
            self.show_page(PatternEditor(holder=self.holder, name=text))
        self.ask(dialog=PromptDialog(title=MSG_NEW_PATTERN_PROMPT, value=default), then=named)
