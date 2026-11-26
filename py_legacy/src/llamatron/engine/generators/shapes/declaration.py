# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Shapes generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, its words, its logic and its page."""

from llamatron.engine.generators import shapes
from llamatron.engine.generators.shapes import strings, view
from llamatron.engine.generators.shapes.controller import ShapesController
from llamatron.engine.generators.shapes.model import ShapesSettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

PLUGIN = GeneratorPlugin(name=shapes.NAME, section=shapes.SECTION, settings=ShapesSettings, strings=strings, controller=ShapesController(), view=view.VIEW)
