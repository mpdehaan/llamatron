# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What the shape generators share: Density, Swell and Articulate each hold a shape over time."""

from llamatron.engine.generators.settings_base import GeneratorSettings
from llamatron.model.objects import shapes as shapes_values
from llamatron.model.objects.shapes import shape_values, ShapeValues
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import shape_setting, ShapePart

class ShapeSetting:
    """A Density, Swell or Articulate generator's settings, as a file names them: a Swell's accent besides the four every shape has."""

    RESTART = file_format.GENERATOR_RESTART

    START = 'start'
    END = 'end'
    OVER = 'over'
    THEN = 'then'
    ACCENT = 'accent'


class ShapeSettings(GeneratorSettings):
    """A shape's settings as a generator a chain names, which wins over its clip's and its scene's: Density, Swell or Articulate, each a subclass.

    Like a drift, it runs on no clip's notes itself: the render reads it for each clip that
    names it (playback/shapes.py), so GENERATOR is None.
    """

    __slots__ = ()

    GENERATOR = None
    SHAPE = None

    @classmethod
    def new(cls):
        """Return the settings a new one starts with: nothing set, which plays as 100%, changing nothing until given values."""
        return cls({})

    def get_shape(self):
        """Return its shape's values, its start and end 100% when left blank."""
        written = {shape_setting(shape=self.SHAPE, part=part): self.get_written(part) for part in file_format.SHAPE_PARTS}
        values = shape_values(settings=written, shape=self.SHAPE)
        accent = self.get_written(ShapeSetting.ACCENT) or shapes_values.NO_ACCENT
        if values is None:
            return ShapeValues(shapes_values.UNCHANGED, shapes_values.UNCHANGED, written[shape_setting(shape=self.SHAPE, part=ShapePart.OVER)],
                               written[shape_setting(shape=self.SHAPE, part=ShapePart.THEN)] or file_format.SHAPE_THENS[0], accent)
        return values._replace(accent=accent)
