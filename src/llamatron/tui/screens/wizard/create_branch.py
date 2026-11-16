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
"""The wizard's Create branch: what will be made, to read, and the button that makes it."""

from llamatron.macro_composer.wizard_choices import genre_title
from llamatron.strings.errors import ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE
from llamatron.strings.labels import MSG_GENRE_LABEL, MSG_TEMPO_LABEL, MSG_WIZARD_CREATE_BRANCH, MSG_WIZARD_CREATE_BUTTON, MSG_WIZARD_FORM_LABEL, MSG_WIZARD_KEY_LABEL, MSG_WIZARD_LENGTH_LABEL, MSG_WIZARD_SCALE_TYPE_NAMES, MSG_WIZARD_SONG_LABEL
from llamatron.strings.legends import KeyName, MSG_WIZARD_CREATE_WHAT
from llamatron.strings.marks import MSG_WIZARD_FORM_SHOWN, MSG_WIZARD_GENRE_SHOWN, MSG_WIZARD_KEY_SHOWN, MSG_WIZARD_NEEDS_GENRE
from llamatron.tui.drawing import NOTHING
from llamatron.tui.text import clock
from llamatron.tui.screens.shared.field import Button, Field
from llamatron.tui.screens.wizard.branch import Branch


class CreateBranch(Branch):
    """A summary of the choices and the Create button, which works once a genre and a subgenre are chosen."""

    __slots__ = ()

    def name(self):
        return MSG_WIZARD_CREATE_BRANCH

    def note(self):
        return NOTHING if self.choices().is_ready() else MSG_WIZARD_NEEDS_GENRE

    def refusal(self):
        return None if self.choices().is_ready() else ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE

    def fields(self):
        choices = self.choices()
        page = self.page()
        fields = [Field(label=MSG_WIZARD_SONG_LABEL, value=page.song_name)]
        if choices.is_ready():
            fields += [
                Field(label=MSG_GENRE_LABEL, value=lambda: MSG_WIZARD_GENRE_SHOWN.format(genre=genre_title(choices.get_genre()), subgenre=choices.get_subgenre())),
                Field(label=MSG_WIZARD_KEY_LABEL, value=lambda: MSG_WIZARD_KEY_SHOWN.format(root=choices.get_root(), scale=MSG_WIZARD_SCALE_TYPE_NAMES[choices.get_scale_type()])),
                Field(label=MSG_TEMPO_LABEL, value=choices.get_tempo),
                Field(label=MSG_WIZARD_FORM_LABEL, value=lambda: MSG_WIZARD_FORM_SHOWN.format(form=choices.get_form(), count=len(choices.form_sections()))),
                Field(label=MSG_WIZARD_LENGTH_LABEL, value=lambda: clock(choices.form_seconds())),
            ]
        return [*fields, Button(label=MSG_WIZARD_CREATE_BUTTON, key_name=KeyName.ENTER, enter=page.create, enter_what=MSG_WIZARD_CREATE_WHAT)]
