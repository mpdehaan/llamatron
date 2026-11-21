# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Swell generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, and its words."""

from llamatron.engine.generators import swell
from llamatron.engine.generators.swell import strings
from llamatron.engine.generators.swell.controller import SwellController
from llamatron.engine.generators.swell.model import SwellSettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

PLUGIN = GeneratorPlugin(name=swell.NAME, section=swell.SECTION, settings=SwellSettings, strings=strings, controller=SwellController())
