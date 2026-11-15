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
"""One section of the wizard's form, under the Form branch: how long the section lasts and who plays in it, to read."""

from llamatron.strings.labels import MSG_WIZARD_BARS_LABEL, MSG_WIZARD_PLAYS_LABEL
from llamatron.strings.marks import MSG_NONE_SHOWN, MSG_WIZARD_PLAYERS_JOIN
from llamatron.tui.screens.shared.field import Field
from llamatron.tui.screens.wizard.branch import Branch

# What two sections of one name are told apart by: the section's name and its number in the form.
SECTION_KEY = '{number} {name}'


class SectionBranch(Branch):
    """A section of the form, by its place in the form and its name."""

    __slots__ = ('_number', '_name')

    def __init__(self, *, page, number, name):
        super().__init__(page=page)
        self._number = number
        self._name = name

    def key(self):
        return SECTION_KEY.format(number=self._number, name=self._name)

    def name(self):
        return self._name

    def fields(self):
        bars, plays = self.choices().section_facts(self._name)
        return [
            Field(label=MSG_WIZARD_BARS_LABEL, value=lambda: bars),
            Field(label=MSG_WIZARD_PLAYS_LABEL, value=lambda: MSG_WIZARD_PLAYERS_JOIN.join(plays) or MSG_NONE_SHOWN),
        ]
