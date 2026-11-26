# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Musician generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, and its words."""

from llamatron.engine.generators import musician
from llamatron.engine.generators.musician import strings, view
from llamatron.engine.generators.musician.controller import MusicianController
from llamatron.engine.generators.musician.model import MusicianSettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

PLUGIN = GeneratorPlugin(name=musician.NAME, section=musician.SECTION, settings=MusicianSettings, strings=strings, controller=MusicianController(), view=view.VIEW)
