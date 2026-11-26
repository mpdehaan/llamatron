# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The logic of the Shapes generator plugin: the controller's methods it fills in."""

from llamatron.engine.generators.controller import GeneratorController
from llamatron.model.schema import file_format


class ShapesController(GeneratorController):
    """What a Shapes generator does: it names the three shapes, each laid over a finished clip where set."""

    __slots__ = ()

    SHAPES = tuple(file_format.SHAPES)
