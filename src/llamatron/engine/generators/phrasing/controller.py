# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The logic of the Phrasing generator plugin: the controller's methods it fills in."""

from llamatron.engine.generators.controller import GeneratorController


class PhrasingController(GeneratorController):
    """What a Phrasing does."""

    __slots__ = ()

    def make_generator(self, *, settings, place):
        return settings.generator_for(where=place.where(), bar=place.bar())
