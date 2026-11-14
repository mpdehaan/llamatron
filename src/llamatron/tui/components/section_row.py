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

"""A section's row in the pattern editor: the heading of an accordion section, which opens and closes the rows under it.

The user's design of 2026-11-08, in place of the sets of rows that Tab cycled through: the rows
under Octave come in sections, each headed by a row of the grid with a rule above and below it,
whose label is a mark, + closed or - open, and the section's name. The cursor rests on the row
like any other, keeping its step, and the label is drawn in reverse video there, since the row
has no cells; Space or Enter opens or closes the section, and which sections are open is kept on
the app for the session.
"""

from llamatron.tui.components.pattern_row import PatternRow
from llamatron.tui.drawing import NOTHING
from llamatron.strings.labels import MSG_SECTION_LABEL, MSG_SECTION_NAMES
from llamatron.strings.marks import MSG_SECTION_CLOSED_MARK, MSG_SECTION_OPEN_MARK
from llamatron.tui import keybindings


class SectionRow(PatternRow):
    """The heading row of a section, named by the section it opens and closes."""

    KEYS = keybindings.SectionRow

    __slots__ = ()

    def is_open(self):
        return self.editor.rows_view.section_is_open(self.name)

    def label(self):
        mark = MSG_SECTION_OPEN_MARK if self.is_open() else MSG_SECTION_CLOSED_MARK
        return MSG_SECTION_LABEL.format(mark=mark, name=MSG_SECTION_NAMES[self.name])

    def rule_before(self):
        return True

    def rule_after(self):
        return True

    def marks_label(self):
        return True

    def blocked(self, *, step=None):
        return False

    def cell_text(self, *, step):
        return NOTHING

    def cell_lines(self, *, step):
        return [NOTHING]

    def keys(self):
        return [self.bind(self.KEYS.CLOSE if self.is_open() else self.KEYS.OPEN, action=self.toggle)]

    def toggle(self):
        self.editor.rows_view.toggle_section(self.name)
