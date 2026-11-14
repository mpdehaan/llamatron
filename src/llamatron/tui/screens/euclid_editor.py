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
"""The Euclid editor page: one Euclid generator's name and its rhythm, a mask painted on clips on top of their track's."""

from rich.text import Text

from llamatron.composition.file_format import EuclidPart, GeneratorKind, Section
from llamatron.strings.help import HELP_EUCLID_EDITOR
from llamatron.strings.labels import Crumb, MSG_EUCLID_LABEL, MSG_EUCLID_PART_LABELS
from llamatron.strings.messages import MSG_RENAME_GENERATOR_PROMPT
from llamatron.tui import keybindings
from llamatron.tui.screens.restart_field import restart_field
from llamatron.tui.screens.euclid_fields import drawn_rhythm, euclid_fields, pick_rhythm
from llamatron.tui.screens.field import NameField
from llamatron.tui.screens.field_page import FieldPage
from llamatron.tui.screens.shows_named_item import ShowsNamedItem
from llamatron.tui.drawing import Style


class EuclidEditor(ShowsNamedItem, FieldPage):

    KEYS = keybindings.EuclidEditor
    HELP = HELP_EUCLID_EDITOR
    SECTION = Section.EUCLIDS
    CRUMBS_BEFORE = (Crumb.GENERATORS,)
    RENAME_PROMPT = MSG_RENAME_GENERATOR_PROMPT.format(label=MSG_EUCLID_LABEL)

    def __init__(self, *, holder, name):
        super().__init__(holder)
        self.show_item(name)

    def euclid(self):
        return self.document().song().get_generator_settings(kind=GeneratorKind.EUCLID, name=self.item)

    def store(self, *, part, value):
        self.document().set_generator_setting(section=Section.EUCLIDS, name=self.item, setting=part, value=value)

    def fields(self):
        return [NameField(value=lambda: self.item, rename=self.rename), *euclid_fields(page=self, value=self.euclid().get_euclid_setting, store=lambda part, value: self.store(part=part, value=value), prefixed=False), restart_field(self)]

    def page_keys(self):
        if self.field().label == MSG_EUCLID_PART_LABELS[EuclidPart.HITS]:
            return [self.bind(self.KEYS.PICK_RHYTHM, action=lambda: pick_rhythm(page=self, store=lambda part, value: self.store(part=part, value=value)))]
        return []

    def notes(self, width):
        mask = self.euclid().get_euclid()
        return [] if mask is None else [Text(drawn_rhythm(hits=mask.hits, steps=mask.steps, rotate=mask.rotate), style=Style.DIM)]
