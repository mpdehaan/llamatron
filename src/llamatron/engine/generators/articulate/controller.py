# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The logic of the Articulate generator plugin: the controller's methods it fills in."""

from llamatron.engine.generators.controller import GeneratorController
from llamatron.model.schema.file_format import Shape


class ArticulateController(GeneratorController):
    """What a Articulate does."""

    __slots__ = ()

    SHAPE = Shape.ARTICULATE
