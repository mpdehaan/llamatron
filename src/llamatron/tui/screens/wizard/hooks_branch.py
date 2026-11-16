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
"""The wizard's Hooks branch, under Composition: whether the song has a hook, which is made apart from the melody style."""

from llamatron.strings.labels import MSG_WIZARD_HOOK_LABEL, MSG_WIZARD_HOOK_OFF, MSG_WIZARD_HOOK_ON, MSG_WIZARD_HOOKS_BRANCH
from llamatron.tui.screens.shared.field import Toggle
from llamatron.tui.screens.wizard.song_ways_branch import SongWaysBranch


class HooksBranch(SongWaysBranch):
    """The Hook switch, shown where a hook changes the song; the hook's kind, picture, variations and editing are to come."""

    __slots__ = ()

    def name(self):
        return MSG_WIZARD_HOOKS_BRANCH

    def traits(self):
        return []

    def offers_a_hook(self):
        return self.choices().is_ready() and self.choices().can_have_hook()

    def summary(self):
        if not self.offers_a_hook():
            return None
        return MSG_WIZARD_HOOK_ON if self.choices().has_hook() else MSG_WIZARD_HOOK_OFF

    def fields(self):
        if not self.offers_a_hook():
            return []
        choices = self.choices()
        return [Toggle(label=MSG_WIZARD_HOOK_LABEL, on=choices.has_hook(), set=self.page().choosing(choices.set_hook))]
