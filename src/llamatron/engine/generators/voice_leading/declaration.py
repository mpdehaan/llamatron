# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Voice leading generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, and its words."""

from llamatron.engine.generators import voice_leading
from llamatron.engine.generators.voice_leading import strings
from llamatron.engine.generators.voice_leading.controller import VoiceLeadingController
from llamatron.engine.generators.voice_leading.settings import VoiceLeadingSettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

PLUGIN = GeneratorPlugin(name=voice_leading.NAME, section=voice_leading.SECTION, settings=VoiceLeadingSettings, strings=strings, controller=VoiceLeadingController())
