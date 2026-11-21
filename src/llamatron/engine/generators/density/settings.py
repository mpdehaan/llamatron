# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The settings of the density generator: their names, their checks and their defaults, as a set file holds them."""

from llamatron.engine.generators import settings_base
from llamatron.engine.generators.shape_settings import ShapeSettings
from llamatron.model.objects.shapes import shape_part_settings
from llamatron.model.schema.file_format import Shape
from llamatron.model.schema.setting import described

class DensitySettings(ShapeSettings):
    """A Density generator's settings: the share of notes that play, from its start to its end."""

    __slots__ = ()

    SHAPE = Shape.DENSITY
    SETTINGS = described(*shape_part_settings(shape=Shape.DENSITY, named=lambda part: part), settings_base.RESTART_SETTING)
