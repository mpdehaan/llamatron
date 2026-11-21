# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A branch of the wizard for what the whole song has a way of, each a field: the branches under Composition are three."""

from rich.text import Text

from llamatron.interface.tracker import drawing
from llamatron.interface.tracker.drawing import Style
from llamatron.interface.tracker.screens.shared.field import ChoiceField
from llamatron.interface.tracker.screens.wizard.branch import Branch
from llamatron.user_strings import errors, messages

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
            trait = choices.get_band().song_trait(traits)
            if trait is not None and len(choices.get_band().song_ways(trait)) >= A_CHOICE:
                fields.append(ChoiceField(page=page, label=label, choices=choices.get_band().song_ways(trait), current=choices.get_band().get_way(trait), set=self.way_setter(trait)))
        return fields

    def way_setter(self, trait):
        choices = self.get_choices()
        return self.get_page().choosing(lambda value: choices.get_band().set_way(trait=trait, value=value))

    def fields(self):
        return self.way_fields() if self.get_choices().is_ready() else []

    def remarks(self, width):
        """Say so where the subgenre leaves nothing to choose, so that an empty branch explains itself."""
        if self.get_choices().is_ready() and not self.fields():
            return [Text(drawing.INDENT + messages.MSG_WIZARD_NOTHING_TO_CHOOSE, style=Style.DIM)]
        return []
