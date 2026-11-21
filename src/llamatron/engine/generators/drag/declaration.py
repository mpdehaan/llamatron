# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Drag generator plugin's declaration: the name a set file and a chain write it by, the section of a set that holds its
generators, the class of its settings, and its words."""

from llamatron.engine.generators import drag
from llamatron.engine.generators.drag import strings
from llamatron.engine.generators.drag.controller import DragController
from llamatron.engine.generators.drag.settings import DragSettings
from llamatron.model.schema.generator_plugins import GeneratorPlugin

PLUGIN = GeneratorPlugin(name=drag.NAME, section=drag.SECTION, settings=DragSettings, strings=strings, controller=DragController())
