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
"""The group of the song's melodies in the wizard's tree: its hook, then a melody for each kind of section that has one.

The hook comes first, since the chorus is written around it and every other melody stays under it.
"""

from llamatron.strings import labels
from llamatron.tui.screens.wizard.branch import Branch
from llamatron.tui.screens.wizard.hooks_branch import HooksBranch
from llamatron.tui.screens.wizard.section_melody_branch import SectionMelodyBranch


class MelodiesBranch(Branch):
    """The branches Hook and one for each kind of section that has a melody."""

    __slots__ = ()

    def name(self):
        return labels.MSG_WIZARD_MELODIES_BRANCH

    def summary(self):
        """Return how many melodies the song has, the hook among them, for the overview of Composition."""
        return str(len(self.children())) if self.choices().is_ready() else None

    def children(self):
        page = self.page()
        choices = self.choices()
        if not choices.is_ready():
            return []
        hook = [HooksBranch(page=page)] if choices.can_have_hook() else []
        return [*hook, *(SectionMelodyBranch(page=page, kind=kind) for kind in choices.tune_kinds())]
