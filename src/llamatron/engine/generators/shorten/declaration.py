# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Shorten generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, and its words."""

from llamatron.engine.generators import shorten
from llamatron.engine.generators.shorten import strings
from llamatron.engine.generators.shorten.controller import ShortenController
from llamatron.engine.generators.shorten.model import ShortenSettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

PLUGIN = GeneratorPlugin(name=shorten.NAME, section=shorten.SECTION, settings=ShortenSettings, strings=strings, controller=ShortenController())
