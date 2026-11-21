# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Hocket generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, and the class of its settings."""

from llamatron.engine.generators.hocket.settings import HocketSettings
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import GeneratorKind
from llamatron.model.schema.generator_plugins import GeneratorPlugin

PLUGIN = GeneratorPlugin(name=GeneratorKind.HOCKET, section=file_format.NAMED_GENERATORS[GeneratorKind.HOCKET], settings=HocketSettings)
