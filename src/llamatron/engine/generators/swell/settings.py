# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The settings of the swell generator: their names, their checks and their defaults, as a set file holds them."""

from llamatron.engine.generators import settings_base
from llamatron.engine.generators.shape_settings import ShapeSetting, ShapeSettings
from llamatron.model.objects.shapes import shape_part_settings
from llamatron.model.schema import limits
from llamatron.model.schema.file_format import Shape
from llamatron.model.schema.setting import described, WholeNumber
from llamatron.user_strings import errors

class SwellSettings(ShapeSettings):
    """A Swell generator's settings: how loud the notes play, from its start to its end, and how much louder the strong beats are."""

    __slots__ = ()

    SHAPE = Shape.SWELL
    SETTINGS = described(
        *shape_part_settings(shape=Shape.SWELL, named=lambda part: part),
        WholeNumber(name=ShapeSetting.ACCENT, lowest=limits.MIN_ACCENT, highest=limits.MAX_ACCENT, error=errors.ERR_BAD_SHAPE_PERCENT),
        settings_base.RESTART_SETTING,
    )
