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

"""A branch of the wizard for what the whole song has a way of, each a field: the branches under Composition are three."""

from rich.text import Text

from llamatron.strings import errors, messages
from llamatron.tui import drawing
from llamatron.tui.drawing import Style
from llamatron.tui.screens.shared.field import ChoiceField
from llamatron.tui.screens.wizard.branch import Branch

# A field is worth showing once there is more than one way to choose.
A_CHOICE = 2


class SongWaysBranch(Branch):
    """A branch whose fields each choose how the whole song goes in one respect. A subclass names itself and lists its traits."""

    __slots__ = ()

    def refusal(self):
        return None if self.get_choices().is_ready() else errors.ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE

    def traits(self):
        """Return each field's label with the traits it may stand for, the first the genre has being the one chosen."""
        raise NotImplementedError

    def way_fields(self):
        """Return a field for each trait the genre has more than one way of, since one way is nothing to choose."""
        choices = self.get_choices()
        page = self.get_page()
        fields = []
        for label, traits in self.traits():
            trait = choices.song_trait(traits)
            if trait is not None and len(choices.song_ways(trait)) >= A_CHOICE:
                fields.append(ChoiceField(page=page, label=label, choices=choices.song_ways(trait), current=choices.get_way(trait), set=self.way_setter(trait)))
        return fields

    def way_setter(self, trait):
        choices = self.get_choices()
        return self.get_page().choosing(lambda value: choices.set_way(trait=trait, value=value))

    def fields(self):
        return self.way_fields() if self.get_choices().is_ready() else []

    def notes(self, width):
        """Say so where the subgenre leaves nothing to choose, so that an empty branch explains itself."""
        if self.get_choices().is_ready() and not self.fields():
            return [Text(drawing.INDENT + messages.MSG_WIZARD_NOTHING_TO_CHOOSE, style=Style.DIM)]
        return []
