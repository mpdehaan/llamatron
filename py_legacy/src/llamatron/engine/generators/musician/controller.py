# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The logic of the Musician generator plugin: the controller's methods it fills in."""

from llamatron.engine.generators.controller import GeneratorController
from llamatron.engine.generators.musician.generator import Surroundings


class MusicianController(GeneratorController):
    """What a Musician does."""

    __slots__ = ()

    FOLLOWS_TRACKS = True

    def make_generator(self, *, settings, place):
        # A drum pattern's notes are drums, which no chord moves, whoever is said to play them.
        chords = None
        if not place.plays_drums():
            chords = place.chords_followed(settings.get_chords_from())
        surroundings = Surroundings(
            section=place.section(),

            chords=chords,
            tune=place.tune_heard(settings.get_tune_from()),
        )
        return settings.generator_for(where=place.where(), bar=place.bar(), beat=place.beat(), surroundings=surroundings, seed=place.seed())
