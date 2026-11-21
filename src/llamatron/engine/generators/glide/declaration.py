# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Glide generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, and its words."""

from llamatron.engine.generators import glide
from llamatron.engine.generators.glide import strings
from llamatron.engine.generators.glide.controller import GlideController
from llamatron.engine.generators.glide.model import GlideSettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

PLUGIN = GeneratorPlugin(name=glide.NAME, section=glide.SECTION, settings=GlideSettings, strings=strings, controller=GlideController())
