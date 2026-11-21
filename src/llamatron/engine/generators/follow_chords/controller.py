# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The logic of the FollowChords generator plugin: the controller's methods it fills in."""

from llamatron.engine.generators.controller import GeneratorController
from llamatron.engine.generators.follow_chords.generator import FollowChords


class FollowChordsController(GeneratorController):
    """What a FollowChords does."""

    __slots__ = ()

    MOVES_PITCHES = True
    FOLLOWS_TRACKS = True

    def make_generator(self, *, settings, place):
        return FollowChords(chords=place.chords_followed(settings.get_chords_from()))
