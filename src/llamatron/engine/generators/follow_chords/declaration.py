# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Follow Chords generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, and its words."""

from llamatron.engine.generators import follow_chords
from llamatron.engine.generators.follow_chords import strings
from llamatron.engine.generators.follow_chords.controller import FollowChordsController
from llamatron.engine.generators.follow_chords.settings import FollowChordsSettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

PLUGIN = GeneratorPlugin(name=follow_chords.NAME, section=follow_chords.SECTION, settings=FollowChordsSettings, strings=strings, controller=FollowChordsController())
