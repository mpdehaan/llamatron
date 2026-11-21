# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The settings of the articulate generator: their names, their checks and their defaults, as a set file holds them."""

from llamatron.engine.generators import settings_base
from llamatron.engine.generators.shape_settings import ShapeSettings
from llamatron.model.objects.shapes import shape_part_settings
from llamatron.model.schema.file_format import Shape
from llamatron.model.schema.setting import described

class ArticulateSettings(ShapeSettings):
    """An Articulate generator's settings: how long each note sounds, as a share of what's written, from its start to its end."""

    __slots__ = ()

    SHAPE = Shape.ARTICULATE
    SETTINGS = described(*shape_part_settings(shape=Shape.ARTICULATE, named=lambda part: part), settings_base.RESTART_SETTING)
