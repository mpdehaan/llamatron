# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The arpeggiator generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, and its words."""

from llamatron.engine.generators import arp
from llamatron.engine.generators.arp import strings
from llamatron.engine.generators.arp.settings import ArpSettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

PLUGIN = GeneratorPlugin(name=arp.NAME, section=arp.SECTION, settings=ArpSettings, strings=strings)
