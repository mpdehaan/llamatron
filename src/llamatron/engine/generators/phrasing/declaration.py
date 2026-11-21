# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Phrasing generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, and its words."""

from llamatron.engine.generators import phrasing
from llamatron.engine.generators.phrasing import strings
from llamatron.engine.generators.phrasing.controller import PhrasingController
from llamatron.engine.generators.phrasing.model import PhrasingSettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

PLUGIN = GeneratorPlugin(name=phrasing.NAME, section=phrasing.SECTION, settings=PhrasingSettings, strings=strings, controller=PhrasingController())
