# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The logic of the Chords generator plugin: the controller's methods it fills in."""

from llamatron.engine.generators.chords import model
from llamatron.engine.generators.chords.generator import ChordsGenerator
from llamatron.engine.generators.controller import GeneratorController


class ChordsController(GeneratorController):
    """What a Chords generator does: moves a clip's notes through its progression, or along the chords another track plays, or turns
    each single note into a chord, then voices them, sparing a drum pattern, whose notes are drums."""

    __slots__ = ()

    MOVES_PITCHES = True
    # In Follow Progression it plays from the chords of the track its settings name, which is rendered first.
    FOLLOWS_TRACKS = True

    def make_generator(self, *, settings, place):
        continuation = place.continuation(settings)
        mode = settings.get_mode()
        moving = None
        if mode == model.PROGRESSION:
            moving = settings.progression(bar=place.bar(), continuation=continuation)
        elif mode == model.FOLLOW_PROGRESSION:
            moving = settings.following(place.chords_followed(settings.get_chords_from()))
        elif mode == model.AUTO_CHORD:
            moving = settings.auto_chord()
        voicing = None
        if settings.voices():
            voicing = settings.voicing(continuation)
        return ChordsGenerator(moving=moving, voicing=voicing)
