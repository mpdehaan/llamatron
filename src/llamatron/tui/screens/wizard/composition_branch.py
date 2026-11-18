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
"""The wizard's Composition branch: what the song is written from, each a branch under it: its chords, its melody and its hooks."""

from rich.text import Text

from llamatron.strings import errors, labels, marks, messages
from llamatron.tui.drawing import INDENT, Style
from llamatron.tui.screens.wizard.branch import Branch
from llamatron.tui.screens.wizard.chords_branch import ChordsBranch
from llamatron.tui.screens.wizard.melody_branch import MelodyBranch
from llamatron.tui.screens.wizard.riff_assign_branch import RiffAssignBranch
from llamatron.tui.screens.wizard.riffs_branch import RiffsBranch
from llamatron.tui.screens.wizard.section_melody_branch import SectionMelodyBranch
from llamatron.tui.screens.wizard.section_players_branch import SectionPlayersBranch


class CompositionBranch(Branch):
    """The branches Chords, Melody, one for each kind of section that has a melody, Riffs, Riff Assign and Section Players, with what each is set to shown at a glance."""

    __slots__ = ()

    def name(self):
        return labels.MSG_WIZARD_COMPOSITION_BRANCH

    def refusal(self):
        return None if self.choices().is_ready() else errors.ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE

    def children(self):
        page = self.page()
        choices = self.choices()
        melodies = [SectionMelodyBranch(page=page, kind=kind) for kind in choices.tune_kinds()] if choices.is_ready() else []
        return [ChordsBranch(page=page), MelodyBranch(page=page), *melodies, RiffsBranch(page=page), RiffAssignBranch(page=page), SectionPlayersBranch(page=page)]

    def notes(self, width):
        """Return each branch under this one with what it is set to, leaving out a branch the subgenre has nothing to choose in; or what to choose first."""
        if not self.choices().is_ready():
            return [Text(INDENT + messages.MSG_WIZARD_CHOOSE_FIRST, style=Style.DIM)]
        shown = [(child.name(), child.summary()) for child in self.children() if child.summary() is not None]
        longest = max((len(name) for name, _ in shown), default=0)
        return [Text(INDENT + marks.MSG_WIZARD_COMPOSITION_LINE.format(name=name, width=longest, value=value)) for name, value in shown]
