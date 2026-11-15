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

"""The wizard's Start branch: how a run starts when the current song was made by the wizard."""

from llamatron.strings.labels import MSG_WIZARD_START_BRANCH, MSG_WIZARD_START_NAMES
from llamatron.strings.legends import What
from llamatron.strings.marks import MSG_TOGGLE_ON, MSG_WIZARD_NEEDS_START
from llamatron.tui.drawing import NOTHING
from llamatron.tui.screens.shared.field import Field
from llamatron.tui.screens.wizard.branch import Branch
from llamatron.tui.screens.wizard.starts import STARTS


class StartBranch(Branch):
    """Four ways to start, none chosen at first, the user's design: every other branch waits until one is."""

    __slots__ = ()

    def name(self):
        return MSG_WIZARD_START_BRANCH

    def note(self):
        return MSG_WIZARD_NEEDS_START if self.page().start() is None else NOTHING

    def waits_for_start(self):
        return False

    def fields(self):
        return [self.start_field(start) for start in STARTS]

    def start_field(self, start):
        """Return one way of starting as a row that ENTER selects, with the dot of a thing that is on beside the one selected."""
        page = self.page()
        return Field(label=MSG_WIZARD_START_NAMES[start], value=lambda: MSG_TOGGLE_ON if page.start() == start else NOTHING, enter=lambda: page.start_with(start), enter_what=What.SELECT)
