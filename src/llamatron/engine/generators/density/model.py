# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Density plugin's model: its settings, which own a shape over time."""

from llamatron.engine.generators import settings_base
from llamatron.engine.generators.settings_base import GeneratorSettings
from llamatron.engine.generators.shape_part import written_shape
from llamatron.model.objects.shapes import shape_part_settings
from llamatron.model.schema.file_format import Shape
from llamatron.model.schema.setting import described


class DensitySettings(GeneratorSettings):
    """A Density generator's settings: the share of notes that play, from its start to its end.

    It runs on no clip's notes itself: its controller names the shape, which the Realizer lays over each finished clip that
    names it (engine/realizer/shapes.py), so GENERATOR is None.
    """

    __slots__ = ()

    SETTINGS = described(
        *shape_part_settings(shape=Shape.DENSITY, named=lambda part: part),
        settings_base.RESTART_SETTING,
    )

    @classmethod
    def new(cls):
        """Return the settings a new one starts with: nothing set, which plays as 100%, changing nothing until given values."""
        return cls({})

    def get_shape(self):
        """Return the values of the shape it owns, its start and end 100% when left blank."""
        return written_shape(owner=self, shape=Shape.DENSITY)
