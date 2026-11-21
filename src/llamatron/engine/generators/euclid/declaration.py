# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Euclidean mask generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, and its words."""

from llamatron.engine.generators import euclid
from llamatron.engine.generators.euclid import strings
from llamatron.engine.generators.euclid.controller import EuclidController
from llamatron.engine.generators.euclid.model import EuclidSettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

PLUGIN = GeneratorPlugin(name=euclid.NAME, section=euclid.SECTION, settings=EuclidSettings, strings=strings, controller=EuclidController())
