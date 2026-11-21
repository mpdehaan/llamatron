# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The shape over time a plugin's model may own, which a Density, a Swell and an Articulate each hold: its start, its end, how
long it takes and what follows, read from the model's settings. The part is composed into a model, never inherited."""

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


def written_shape(*, owner, shape):
    """Return the values of the shape a model owns, from its settings, its start and end 100% when left blank."""
    written = {shape_setting(shape=shape, part=part): owner.get_written(part) for part in file_format.SHAPE_PARTS}
    values = shape_values(settings=written, shape=shape)
    accent = owner.get_written(ShapeSetting.ACCENT) or shapes_values.NO_ACCENT
    if values is None:
        return ShapeValues(shapes_values.UNCHANGED, shapes_values.UNCHANGED, written[shape_setting(shape=shape, part=ShapePart.OVER)],
                           written[shape_setting(shape=shape, part=ShapePart.THEN)] or file_format.SHAPE_THENS[0], accent)
    return values._replace(accent=accent)
