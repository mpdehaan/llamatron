# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Strum generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, and its words."""

from llamatron.engine.generators import strum
from llamatron.engine.generators.strum import strings
from llamatron.engine.generators.strum.controller import StrumController
from llamatron.engine.generators.strum.model import StrumSettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

PLUGIN = GeneratorPlugin(name=strum.NAME, section=strum.SECTION, settings=StrumSettings, strings=strings, controller=StrumController())
