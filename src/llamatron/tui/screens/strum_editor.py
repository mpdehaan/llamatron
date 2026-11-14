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
"""The Strum editor page: one Strum generator's name and its strum, which wins over a clip's and its track's."""

from llamatron.composition.file_format import GeneratorKind, Section
from llamatron.strings.help import HELP_STRUM_EDITOR
from llamatron.strings.labels import Crumb, MSG_STRUM_LABEL
from llamatron.strings.messages import MSG_RENAME_GENERATOR_PROMPT
from llamatron.tui import keybindings
from llamatron.tui.screens.restart_field import restart_field
from llamatron.tui.screens.field import NameField
from llamatron.tui.screens.field_page import FieldPage
from llamatron.tui.screens.shows_named_item import ShowsNamedItem
from llamatron.tui.screens.strum_fields import strum_fields


class StrumEditor(ShowsNamedItem, FieldPage):

    KEYS = keybindings.StrumEditor
    HELP = HELP_STRUM_EDITOR
    SECTION = Section.STRUMS
    CRUMBS_BEFORE = (Crumb.GENERATORS,)
    RENAME_PROMPT = MSG_RENAME_GENERATOR_PROMPT.format(label=MSG_STRUM_LABEL)

    def __init__(self, *, holder, name):
        super().__init__(holder)
        self.show_item(name)

    def strum(self):
        return self.document().song().get_generator_settings(kind=GeneratorKind.STRUM, name=self.item)

    def fields(self):
        strum = self.strum()
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            *strum_fields(
                page=self, value=strum.get_strum_setting, prefixed=False,
                store=lambda part, value: self.document().set_generator_setting(section=Section.STRUMS, name=self.item, setting=part, value=value),
            ),
            restart_field(self),
        ]
