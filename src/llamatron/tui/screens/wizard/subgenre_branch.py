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
"""The song wizard's Subgenre branch, under Genre: the subgenre and the settings that are the subgenre's own."""

from llamatron.composition.limits import MAX_TEMPO, MIN_TEMPO
from llamatron.strings.errors import ERR_WIZARD_CHOOSE_GENRE
from llamatron.strings.labels import MSG_TEMPO_LABEL, MSG_WIZARD_SUBGENRE_BRANCH, MSG_WIZARD_SUBGENRE_LABEL, MSG_WIZARD_SWING_LABEL, MSG_WIZARD_VALUE_FROM
from llamatron.strings.legends import MSG_FROM_GENRE_WHAT
from llamatron.strings.marks import MSG_WIZARD_TEMPO_SHOWN
from llamatron.tui.screens.shared.field import ChoiceField, NumberField
from llamatron.tui.screens.wizard.branch import Branch


class SubgenreBranch(Branch):
    """The subgenre, and what a subgenre is played with: only the settings that mean something for the one chosen are shown."""

    __slots__ = ()

    def name(self):
        return MSG_WIZARD_SUBGENRE_BRANCH

    def refusal(self):
        return None if self.choices().get_genre() is not None else ERR_WIZARD_CHOOSE_GENRE

    def fields(self):
        choices = self.choices()
        page = self.page()
        if choices.get_genre() is None:
            return []
        subgenres = choices.subgenres()
        fields = [self.choice_from_nothing(label=MSG_WIZARD_SUBGENRE_LABEL, values=subgenres, names=subgenres, current=choices.get_subgenre(), set_value=choices.set_subgenre)]
        if not choices.is_ready():
            return fields
        lowest, highest = choices.tempo_range()
        fields.append(NumberField(page=page, label=MSG_TEMPO_LABEL, number=choices.get_tempo(), shown=MSG_WIZARD_TEMPO_SHOWN.format(tempo=choices.get_tempo(), low=lowest, high=highest),
                                  lowest=MIN_TEMPO, highest=MAX_TEMPO, set=page.choosing(choices.set_tempo)))
        if choices.has_swing():
            # The subgenre's own swing is said to be the genre's.
            swing = choices.get_swing()
            shown = MSG_WIZARD_VALUE_FROM.format(value=swing, origin=MSG_FROM_GENRE_WHAT) if swing == choices.swing_of_genre() else None
            fields.append(ChoiceField(page=page, label=MSG_WIZARD_SWING_LABEL, choices=choices.swings(), current=swing, shown=shown, set=page.choosing(choices.set_swing)))
        return fields
