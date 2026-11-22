# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Timing generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, its words, its logic and its page."""

from llamatron.engine.generators import timing
from llamatron.engine.generators.timing import strings, view
from llamatron.engine.generators.timing.controller import TimingController
from llamatron.engine.generators.timing.model import TimingSettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

# Where the built-in timing every clip and track holds runs: below generator_plugins.LIST_PLACE before their own lists of generators, above it after.
TIMING_PLACE = 60

PLUGIN = GeneratorPlugin(name=timing.NAME, section=timing.SECTION, settings=TimingSettings, strings=strings, controller=TimingController(), view=view.VIEW, built_in_place=TIMING_PLACE)
