# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The AutoRatchet generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, and its words."""

from llamatron.engine.generators import auto_ratchet
from llamatron.engine.generators.auto_ratchet import strings
from llamatron.engine.generators.auto_ratchet.controller import AutoRatchetController
from llamatron.engine.generators.auto_ratchet.model import AutoRatchetSettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

PLUGIN = GeneratorPlugin(name=auto_ratchet.NAME, section=auto_ratchet.SECTION, settings=AutoRatchetSettings, strings=strings, controller=AutoRatchetController())
