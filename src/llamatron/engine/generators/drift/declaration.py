# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Drift generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, and its words."""

from llamatron.engine.generators import drift
from llamatron.engine.generators.drift import strings, view
from llamatron.engine.generators.drift.controller import DriftController
from llamatron.engine.generators.drift.model import DriftSettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

PLUGIN = GeneratorPlugin(name=drift.NAME, section=drift.SECTION, settings=DriftSettings, strings=strings, controller=DriftController(), view=view.VIEW)
