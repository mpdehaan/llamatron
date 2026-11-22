# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Phrasing generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, and its words."""

from llamatron.engine.generators import phrasing
from llamatron.engine.generators.phrasing import strings, view
from llamatron.engine.generators.phrasing.controller import PhrasingController
from llamatron.engine.generators.phrasing.model import PhrasingSettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

# Where the built-in phrasing every clip and track holds runs: below generator_plugins.LIST_PLACE before their own lists of generators, above it after.
PHRASING_PLACE = 70

PLUGIN = GeneratorPlugin(name=phrasing.NAME, section=phrasing.SECTION, settings=PhrasingSettings, strings=strings, controller=PhrasingController(), view=view.VIEW, built_in_place=PHRASING_PLACE)
