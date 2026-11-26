# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The logic of the Drift generator plugin: the controller's methods it fills in."""

from llamatron.engine.generators.controller import GeneratorController
from llamatron.engine.generators.drift.play import DriftPlay


class DriftController(GeneratorController):
    """What a Drift does."""

    __slots__ = ()

    def modulation(self, *, song, seed):
        return DriftPlay(song=song, seed=seed)
