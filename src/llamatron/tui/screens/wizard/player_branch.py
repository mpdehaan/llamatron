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

"""A player of the wizard's band: how the player plays, and how busy the player is."""

from llamatron.macro_composer.wizard_choices import LEAST_BUSY, MOST_BUSY
from llamatron.strings.labels import MSG_WIZARD_BUSY_LABEL, MSG_WIZARD_PLAYS_LABEL
from llamatron.strings.marks import MSG_WIZARD_BUSY_SHOWN, MSG_WIZARD_GAUGE_EMPTY, MSG_WIZARD_GAUGE_FULL
from llamatron.tui.screens.shared.field import ChoiceField, NumberField
from llamatron.tui.screens.wizard.branch import Branch


class PlayerBranch(Branch):
    """One player, by the name the genre gives the player."""

    __slots__ = ('_role',)

    def __init__(self, *, page, role):
        super().__init__(page=page)
        self._role = role

    def name(self):
        return self._role

    def fields(self):
        choices = self.choices()
        traits = choices.role_traits(self._role)
        # A player of notes plays one way, called Plays; the drums have a way for each of their parts, each called by the part's name.
        fields = [self.way_field(trait=trait, label=MSG_WIZARD_PLAYS_LABEL if len(traits) == 1 else trait.capitalize()) for trait in traits]
        if choices.has_busy(self._role) and choices.get_busy(self._role) is not None:
            fields.append(self.busy_field())
        return fields

    def way_field(self, *, trait, label):
        choices = self.choices()
        page = self.page()
        return ChoiceField(page=page, label=label, choices=choices.ways(role=self._role, trait=trait), current=choices.get_way(trait),
                           set=page.choosing(lambda value: choices.set_way(trait=trait, value=value)))

    def busy_field(self):
        """Return the Busy field: a number stepped or typed, drawn as a horizontal Busy gauge beside the number."""
        choices = self.choices()
        page = self.page()
        level = choices.get_busy(self._role)
        gauge = MSG_WIZARD_GAUGE_FULL * level + MSG_WIZARD_GAUGE_EMPTY * (MOST_BUSY - level)
        return NumberField(page=page, label=MSG_WIZARD_BUSY_LABEL, number=level, shown=MSG_WIZARD_BUSY_SHOWN.format(gauge=gauge, level=level, most=MOST_BUSY),
                           lowest=LEAST_BUSY, highest=MOST_BUSY, set=page.choosing(lambda value: choices.set_busy(role=self._role, level=value)))
