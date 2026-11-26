# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Shapes plugin's model: a Density's, a Swell's and an Articulate's shapes over time in one generator's settings, each named
as a clip's own shapes are, density_start and the like."""

from llamatron.engine.generators import settings_base
from llamatron.engine.generators.settings_base import GeneratorSettings
from llamatron.model.objects import shapes as shapes_values
from llamatron.model.objects.shapes import prefixed_shape_settings, shape_values
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import Shape
from llamatron.model.schema.setting import described, WholeNumber
from llamatron.user_strings import errors

# How much louder a Swell plays the strong beats, as a file names it.
SWELL_ACCENT = 'swell_accent'


def _every_shape_setting():
    """Return the descriptions of every shape's four parts, Density's, Swell's and Articulate's, in the order a file writes them."""
    settings = []
    for shape in file_format.SHAPES:
        settings += prefixed_shape_settings(shape)
    return settings


class ShapesSettings(GeneratorSettings):
    """A Shapes generator's settings: a Density, a Swell with its accent and an Articulate, each from its start to its end.

    It runs on no clip's notes itself: its controller names the shapes, which the Realizer lays over each finished clip that
    names it (engine/realizer/shapes.py), so GENERATOR is None. A shape whose start and end are both blank is not in force.
    """

    __slots__ = ()

    SETTINGS = described(
        *_every_shape_setting(),
        WholeNumber(name=SWELL_ACCENT, lowest=limits.MIN_ACCENT, highest=limits.MAX_ACCENT, error=errors.ERR_BAD_SHAPE_PERCENT),
        settings_base.RESTART_SETTING,
    )

    @classmethod
    def new(cls):
        """Return the settings a new one starts with: nothing set, which changes nothing until given values."""
        return cls({})

    def get_shape(self, shape):
        """Return the values of one of its shapes, or None where the shape's start and end are both blank."""
        accent = shapes_values.NO_ACCENT
        if shape == Shape.SWELL and self.get_written(SWELL_ACCENT):
            accent = self.get_written(SWELL_ACCENT)
        return shape_values(settings=self._settings, shape=shape, accent=accent)
