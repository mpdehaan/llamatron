# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Chords generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, its words, its logic and its page."""

from llamatron.engine.generators import chords
from llamatron.engine.generators.chords import strings, view
from llamatron.engine.generators.chords.controller import ChordsController
from llamatron.engine.generators.chords.model import ChordsSettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

PLUGIN = GeneratorPlugin(name=chords.NAME, section=chords.SECTION, settings=ChordsSettings, strings=strings, controller=ChordsController(), view=view.VIEW)
