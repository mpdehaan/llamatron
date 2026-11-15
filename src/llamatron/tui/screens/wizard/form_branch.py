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
"""The wizard's Form branch: which of the subgenre's forms the song takes, with a branch under it for each section in order."""

from rich.text import Text

from llamatron.strings.labels import MSG_WIZARD_FORM_BRANCH, MSG_WIZARD_FORM_LABEL
from llamatron.strings.marks import MSG_WIZARD_SECTION_LINE
from llamatron.strings.messages import MSG_WIZARD_CHOOSE_FIRST
from llamatron.tui.drawing import INDENT, Style
from llamatron.tui.screens.shared.field import ChoiceField
from llamatron.tui.screens.wizard.branch import Branch
from llamatron.tui.screens.wizard.section_branch import SectionBranch

# Sections are counted from 1, as they are shown.
FIRST_SECTION_NUMBER = 1


class FormBranch(Branch):
    """The song's form, and its sections as branches."""

    __slots__ = ()

    def name(self):
        return MSG_WIZARD_FORM_BRANCH

    def sections(self):
        return self.choices().form_sections()

    def children(self):
        return [SectionBranch(page=self.page(), number=number, name=name) for number, name in enumerate(self.sections(), start=FIRST_SECTION_NUMBER)]

    def fields(self):
        choices = self.choices()
        if not choices.is_ready():
            return []
        return [ChoiceField(page=self.page(), label=MSG_WIZARD_FORM_LABEL, choices=choices.forms(), current=choices.get_form(), set=self.page().choosing(choices.set_form))]

    def notes(self, width):
        """Return the form's sections in order, each with its bars, so that the whole form reads at a glance; or what to choose first."""
        choices = self.choices()
        if not choices.is_ready():
            return [Text(INDENT + MSG_WIZARD_CHOOSE_FIRST, style=Style.DIM)]
        sections = self.sections()
        longest = max((len(name) for name in sections), default=0)
        return [Text(INDENT + MSG_WIZARD_SECTION_LINE.format(number=number, name=name, width=longest, bars=choices.section_facts(name)[0]))
                for number, name in enumerate(sections, start=FIRST_SECTION_NUMBER)]
