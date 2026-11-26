# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A section's row in the pattern editor: the heading of an accordion section, which opens and closes the rows under it.

In place of the sets of rows that Tab cycled through: the rows
under Octave come in sections, each headed by a row of the grid with a rule above and below it,
whose label is a mark, + closed or - open, and the section's name. The cursor rests on the row
like any other, keeping its step, and the label is drawn in reverse video there, since the row
has no cells; Space or Enter opens or closes the section, and which sections are open is kept on
the app for the session.
"""

from llamatron.interface.tracker import drawing, keybindings
from llamatron.interface.tracker.components.pattern_row import PatternRow
from llamatron.user_strings import labels, marks


class SectionRow(PatternRow):
    """The heading row of a section, named by the section it opens and closes."""

    KEYS = keybindings.SectionRow

    __slots__ = ()

    def is_open(self):
        return self.editor.rows_view.section_is_open(self.name)

    def label(self):
        mark = marks.MSG_SECTION_OPEN_MARK if self.is_open() else marks.MSG_SECTION_CLOSED_MARK
        return labels.MSG_SECTION_LABEL.format(mark=mark, name=labels.MSG_SECTION_NAMES[self.name])

    def rule_before(self):
        return True

    def rule_after(self):
        return True

    def marks_label(self):
        return True

    def blocked(self, *, step=None):
        return False

    def cell_text(self, *, step):
        return drawing.NOTHING

    def cell_lines(self, *, step):
        return [drawing.NOTHING]

    def keys(self):
        return [self.bind(self.KEYS.CLOSE if self.is_open() else self.KEYS.OPEN, action=self.toggle)]

    def toggle(self):
        self.editor.rows_view.toggle_section(self.name)
