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
"""The wizard's Genre branch: the genre and the subgenre, which must be chosen, then the key, the tempo and the song's name, which arrive filled in."""

from llamatron.macro_composer.wizard_choices import SCALE_TYPES, genre_names, genre_title
from llamatron.music.note import ROOT_NAMES
from llamatron.strings.labels import MSG_GENRE_LABEL, MSG_NAME_LABEL, MSG_SCALE_LABEL, MSG_WIZARD_GENRE_BRANCH, MSG_WIZARD_KEY_LABEL, MSG_WIZARD_LENGTH_LABEL, MSG_WIZARD_METER_LABEL, MSG_WIZARD_SCALE_TYPE_NAMES
from llamatron.strings.legends import What
from llamatron.strings.marks import MSG_WIZARD_LENGTH_SHOWN, MSG_WIZARD_OWN_FORM
from llamatron.tui.text import clock
from llamatron.tui.screens.shared.field import ChoiceField, Field
from llamatron.tui.screens.wizard.branch import Branch
from llamatron.tui.screens.wizard.subgenre_branch import SubgenreBranch


class GenreBranch(Branch):
    """The genre and the subgenre, and what follows from them."""

    __slots__ = ()

    def name(self):
        return MSG_WIZARD_GENRE_BRANCH

    def children(self):
        # The subgenre and its own settings are a panel under the genre.
        return [SubgenreBranch(page=self.page())]

    def fields(self):
        choices = self.choices()
        page = self.page()
        genres = genre_names()
        fields = [
            self.choice_from_nothing(label=MSG_GENRE_LABEL, values=genres, names=[genre_title(genre) for genre in genres], current=choices.get_genre(), set_value=choices.set_genre),
        ]
        if choices.is_ready():
            fields += [
                ChoiceField(page=page, label=MSG_WIZARD_KEY_LABEL, choices=ROOT_NAMES, current=choices.get_root(), set=page.choosing(choices.set_root)),
                ChoiceField(page=page, label=MSG_SCALE_LABEL, choices=SCALE_TYPES, names=[MSG_WIZARD_SCALE_TYPE_NAMES[kind] for kind in SCALE_TYPES], current=choices.get_scale_type(),
                            shown=MSG_WIZARD_SCALE_TYPE_NAMES[choices.get_scale_type()], set=page.choosing(choices.set_scale_type)),
                # The meter is the subgenre's, so it is only shown; the length follows the sections, so stepping it chooses a longer or a shorter form.
                Field(label=MSG_WIZARD_METER_LABEL, value=choices.meter),
                self.length_field(),
            ]
        if page.replaces():
            # A replaced song keeps its name, so the name is only shown.
            return [*fields, Field(label=MSG_NAME_LABEL, value=page.song_name)]
        return [*fields, Field(label=MSG_NAME_LABEL, value=page.song_name, enter=page.ask_song_name, enter_what=What.RENAME)]

    def length_field(self):
        """Return the Length field, whose steps choose a shorter or a longer suggested form; once the form is the song's own,
        the length is only shown, since a step would put a suggested form in place of the sections changed."""
        choices = self.choices()
        if choices.has_own_form():
            return Field(label=MSG_WIZARD_LENGTH_LABEL, value=lambda: MSG_WIZARD_LENGTH_SHOWN.format(length=clock(choices.form_seconds()), form=MSG_WIZARD_OWN_FORM))
        return Field(label=MSG_WIZARD_LENGTH_LABEL, value=lambda: MSG_WIZARD_LENGTH_SHOWN.format(length=clock(choices.form_seconds()), form=choices.get_form()),
                     adjust=self.page().choosing(choices.step_length))
