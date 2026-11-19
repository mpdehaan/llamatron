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
from llamatron.strings import help as help_text, labels, messages
from llamatron.tui import keybindings
from llamatron.tui.screens.generators.restart_field import restart_field
from llamatron.tui.screens.generators.strum_fields import strum_fields
from llamatron.tui.screens.shared.field import NameField
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.shared.shows_named_item import ShowsNamedItem


class StrumEditor(ShowsNamedItem, FieldPage):

    KEYS = keybindings.StrumEditor
    HELP = help_text.HELP_STRUM_EDITOR
    SECTION = Section.STRUMS
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=labels.MSG_STRUM_LABEL)

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
                store=lambda part, value: self.document().change(self.document().generator(section=Section.STRUMS, name=self.item).set_setting, name=part, value=value),
            ),
            restart_field(self),
        ]
