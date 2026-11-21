# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The shape generators' editors: a Density's, Swell's or Articulate's name, start, end, over and then, and a Swell's accent."""

from llamatron.engine.generators.shape_part import ShapeSetting
from llamatron.model.schema import limits
from llamatron.tui import keybindings
from llamatron.tui.screens.generators.restart_field import restart_field
from llamatron.tui.screens.generators.shape_fields import shape_fields
from llamatron.tui.screens.shared.field import NameField, NumberField
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.shared.generator_editor import GeneratorEditor
from llamatron.user_strings import labels, marks

NO_ACCENT = 0


class ShapeEditor(GeneratorEditor, FieldPage):
    """One shape generator's settings. A subclass names its SECTION, KIND, SHAPE, its label and whether it has an accent."""

    KEYS = keybindings.ShapeEditor
    KIND = None
    SHAPE = None
    LABEL = None
    HAS_ACCENT = False

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
                page=self, label=labels.MSG_ACCENT_LABEL, number=accent, start=NO_ACCENT, shown=marks.MSG_NONE_SHOWN if accent is None else None,
                lowest=limits.MIN_ACCENT, highest=limits.MAX_ACCENT, set=lambda number: self.store(setting=ShapeSetting.ACCENT, value=number or None),
                clear=lambda: self.store(setting=ShapeSetting.ACCENT, value=None),
            ))
        result.append(restart_field(self))
        return result
