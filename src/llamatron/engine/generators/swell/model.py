# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Swell plugin's model: its settings, which own a shape over time."""

from llamatron.engine.generators import settings_base
from llamatron.engine.generators.settings_base import GeneratorSettings
from llamatron.engine.generators.shape_part import ShapeSetting, written_shape
from llamatron.model.objects.shapes import shape_part_settings
from llamatron.model.schema import limits
from llamatron.model.schema.file_format import Shape
from llamatron.model.schema.setting import described, WholeNumber
from llamatron.user_strings import errors


class SwellSettings(GeneratorSettings):
    """A Swell generator's settings: how loud the notes play, from its start to its end, and how much louder the strong beats are.

    It runs on no clip's notes itself: its controller names the shape, which the Realizer lays over each finished clip that
    names it (playback/shapes.py), so GENERATOR is None.
    """

    __slots__ = ()

    SETTINGS = described(
        *shape_part_settings(shape=Shape.SWELL, named=lambda part: part),
        WholeNumber(name=ShapeSetting.ACCENT, lowest=limits.MIN_ACCENT, highest=limits.MAX_ACCENT, error=errors.ERR_BAD_SHAPE_PERCENT),
        settings_base.RESTART_SETTING,
    )

    @classmethod
    def new(cls):
        """Return the settings a new one starts with: nothing set, which plays as 100%, changing nothing until given values."""
        return cls({})

    def get_shape(self):
        """Return the values of the shape it owns, its start and end 100% when left blank."""
        return written_shape(owner=self, shape=Shape.SWELL)
