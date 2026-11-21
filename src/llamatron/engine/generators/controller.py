# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What every generator plugin's controller is: the logic of a kind of generator, one method for each thing a generator may do.

Each method does nothing unless a plugin's controller fills it in, and the Realizer calls only the methods a plugin fills in
(engine/generators/registry.py), so that a plugin written elsewhere does whatever it does through these methods alone and
nothing outside its folder knows it by name. What a plugin fills in, and what the Realizer hands it there, is said with each
method.
"""


class GeneratorController:
    """The logic of one kind of generator: the methods a plugin's controller fills in, each doing nothing until it does."""

    __slots__ = ()

    # Whether its generators move the pitches of a clip's notes, so that a drum pattern, whose notes are drums, is left alone.
    MOVES_PITCHES = False
    # Whether its generators play from what another track plays, its chords or its tune, named in the settings' tracks.
    FOLLOWS_TRACKS = False
    # The shape its generators lay over a whole finished clip, a Shape such as density, or None for none.
    SHAPE = None

    def make_generator(self, *, settings, place):
        """Return the generator that runs on a clip's notes as one step of a chain, from the generator's settings and its
        place, a ChainStepPlace that answers what the Realizer knows there; None, for a kind that runs on no clip's notes."""
        return None


    def strum(self, settings):
        """Return how its generator strums a clip's chords, as a Strum, and the generator's Restart, or None for none."""
        return None

    def moving_row(self, *, settings, place):
        """Return how its generator moves a clip's notes early or late, as a MovingRow, at a place in the clip's chains."""
        return None


def generator_from_settings(*, settings, place):
    """Return the generator a kind's settings make on their own, given the seed, the pattern's step, the bar, where it
    carries on from and the tempo of its place: what most plugins' make_generator does."""
    return settings.make_generator(
        where=place.where(), default_seed=place.seed(), default_step=place.pattern_step(), bar=place.bar(),
        continuation=place.continuation(settings), tempo=place.tempo(),
    )
