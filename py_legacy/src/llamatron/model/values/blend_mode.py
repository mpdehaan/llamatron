# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""How one clip morphs toward another: where the target comes in from."""

from enum import auto, Enum


class BlendMode(Enum):
    """Where the target comes in from as Blend moves one clip towards another."""

    LEFT = auto()
    RIGHT = auto()
    MIDDLE = auto()
