# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The logic of the Guitarify generator plugin: the controller's methods it fills in."""

from llamatron.engine.generators.base import UnchangedClip
from llamatron.engine.generators.controller import generator_from_settings, GeneratorController
from llamatron.engine.generators.guitarify import model


class GuitarifyController(GeneratorController):
    """What a Guitarify does: in Guitar mode, plays a clip's chords and notes as a guitar's two hands would, as a step of a chain;
    in Strum mode, leaves the notes as written and strums the chords at the very end, after every chain and the shapes."""

    __slots__ = ()

    def make_generator(self, *, settings, place):
        if settings.get_mode() == model.STRUM:
            return UnchangedClip()
        return generator_from_settings(settings=settings, place=place)

    def strum(self, settings):
        if settings.get_mode() != model.STRUM:
            return None
        return settings.strum_values(), settings.get_restart()
