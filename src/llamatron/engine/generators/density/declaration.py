# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Density generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, and its words."""

from llamatron.engine.generators import density
from llamatron.engine.generators.density import strings
from llamatron.engine.generators.density.controller import DensityController
from llamatron.engine.generators.density.settings import DensitySettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

PLUGIN = GeneratorPlugin(name=density.NAME, section=density.SECTION, settings=DensitySettings, strings=strings, controller=DensityController())
