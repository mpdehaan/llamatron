# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The settings of the rush generator: their names, their checks and their defaults, as a set file holds them."""

from llamatron.engine.generators import step_row_settings
from llamatron.engine.generators.step_row_settings import MovingRowSettings

class RushSettings(MovingRowSettings):
    """A Rush's settings: a note starting on a step that's on plays early."""

    __slots__ = ()

    DEFAULT_AMOUNT = step_row_settings.DEFAULT_RUSH
