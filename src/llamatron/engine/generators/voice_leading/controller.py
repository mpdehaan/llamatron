# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The logic of the VoiceLeading generator plugin: the controller's methods it fills in."""

from llamatron.engine.generators.controller import generator_from_settings, GeneratorController


class VoiceLeadingController(GeneratorController):
    """What a VoiceLeading does."""

    __slots__ = ()

    def make_generator(self, *, settings, place):
        return generator_from_settings(settings=settings, place=place)
