# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Progression generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, and its words."""

from llamatron.engine.generators import progression
from llamatron.engine.generators.progression import strings
from llamatron.engine.generators.progression.controller import ProgressionController
from llamatron.engine.generators.progression.settings import ProgressionSettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

PLUGIN = GeneratorPlugin(name=progression.NAME, section=progression.SECTION, settings=ProgressionSettings, strings=strings, controller=ProgressionController())
