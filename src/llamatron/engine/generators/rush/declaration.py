# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Rush generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, and its words."""

from llamatron.engine.generators import rush
from llamatron.engine.generators.rush import strings
from llamatron.engine.generators.rush.settings import RushSettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

PLUGIN = GeneratorPlugin(name=rush.NAME, section=rush.SECTION, settings=RushSettings, strings=strings)
