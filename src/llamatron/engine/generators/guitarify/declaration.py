# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Guitarify generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, and its words."""

from llamatron.engine.generators import guitarify
from llamatron.engine.generators.guitarify import strings, view
from llamatron.engine.generators.guitarify.controller import GuitarifyController
from llamatron.engine.generators.guitarify.model import GuitarifySettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

# Where the built-in guitarify every clip and track holds runs: below generator_plugins.LIST_PLACE before their own lists of generators, above it after.
GUITARIFY_PLACE = 30

PLUGIN = GeneratorPlugin(name=guitarify.NAME, section=guitarify.SECTION, settings=GuitarifySettings, strings=strings, controller=GuitarifyController(), view=view.VIEW, built_in_place=GUITARIFY_PLACE)
