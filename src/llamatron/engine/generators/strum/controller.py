# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The logic of the Strum generator plugin: the controller's methods it fills in."""

from llamatron.engine.generators.controller import GeneratorController


class StrumController(GeneratorController):
    """What a Strum does."""

    __slots__ = ()

    def strum(self, settings):
        return settings.get_strum(), settings.get_restart()
