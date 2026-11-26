# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The arpeggiator generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, and its words."""

from llamatron.engine.generators import arp
from llamatron.engine.generators.arp import strings, view
from llamatron.engine.generators.arp.controller import ArpController
from llamatron.engine.generators.arp.model import ArpSettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

# Where the built-in arp every clip and track holds runs among the built-ins, lower first, all before their own lists of generators.
ARP_PLACE = 20

PLUGIN = GeneratorPlugin(name=arp.NAME, section=arp.SECTION, settings=ArpSettings, strings=strings, controller=ArpController(), view=view.VIEW, built_in_place=ARP_PLACE)
