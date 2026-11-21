# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Hocket generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, and its words."""

from llamatron.engine.generators import hocket
from llamatron.engine.generators.hocket import strings
from llamatron.engine.generators.hocket.settings import HocketSettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

PLUGIN = GeneratorPlugin(name=hocket.NAME, section=hocket.SECTION, settings=HocketSettings, strings=strings)
