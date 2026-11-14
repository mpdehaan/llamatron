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
"""The shape generators' editors: a Density's, Swell's or Articulate's name, start, end, over and then, and a Swell's accent."""

from llamatron.composition.generator_settings import ShapeSetting
from llamatron.composition.limits import MAX_ACCENT, MIN_ACCENT
from llamatron.tui.screens.restart_field import restart_field
from llamatron.tui.screens.field import NameField, NumberField
from llamatron.tui.screens.field_page import FieldPage
from llamatron.tui.screens.shape_fields import shape_fields
from llamatron.tui.screens.shows_named_item import ShowsNamedItem
from llamatron.strings.labels import MSG_ACCENT_LABEL
from llamatron.strings.marks import MSG_NONE_SHOWN
from llamatron.tui import keybindings

NO_ACCENT = 0


class ShapeEditor(ShowsNamedItem, FieldPage):
    """One shape generator's settings. A subclass names its SECTION, KIND, SHAPE, its label and whether it has an accent."""

    KEYS = keybindings.ShapeEditor
    KIND = None
    SHAPE = None
    LABEL = None
    HAS_ACCENT = False

    def __init__(self, *, holder, name):
        super().__init__(holder)
        self.show_item(name)

    def settings(self):
        return self.document().song().get_generator_settings(kind=self.KIND, name=self.item)

    def store(self, *, setting, value):
        self.document().set_generator_setting(section=self.SECTION, name=self.item, setting=setting, value=value)

    def fields(self):
        settings = self.settings()
        result = [
            NameField(value=lambda: self.item, rename=self.rename),
            *shape_fields(page=self, shape=self.SHAPE, value=lambda part: settings.to_data().get(part),
                          store=lambda part, value: self.store(setting=part, value=value), prefixed=False),
        ]
        if self.HAS_ACCENT:
            accent = settings.to_data().get(ShapeSetting.ACCENT)
            result.append(NumberField(
                page=self, label=MSG_ACCENT_LABEL, number=accent, start=NO_ACCENT, shown=MSG_NONE_SHOWN if accent is None else None,
                lowest=MIN_ACCENT, highest=MAX_ACCENT, set=lambda number: self.store(setting=ShapeSetting.ACCENT, value=number or None),
                clear=lambda: self.store(setting=ShapeSetting.ACCENT, value=None),
            ))
        result.append(restart_field(self))
        return result
