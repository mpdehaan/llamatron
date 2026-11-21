# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Articulate generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, and its words."""

from llamatron.engine.generators import articulate
from llamatron.engine.generators.articulate import strings
from llamatron.engine.generators.articulate.controller import ArticulateController
from llamatron.engine.generators.articulate.settings import ArticulateSettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

PLUGIN = GeneratorPlugin(name=articulate.NAME, section=articulate.SECTION, settings=ArticulateSettings, strings=strings, controller=ArticulateController())
