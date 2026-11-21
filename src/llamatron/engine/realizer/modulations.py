# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The song's modulations as it plays: one play for each plugin whose generators change values as the song goes, Drift's
among them, held for the whole render, which every clip naming one of the plugin's generators hears."""

from llamatron.engine.generators import registry
from llamatron.model.schema import generator_plugins

# The controller's method that makes a plugin's play.
MODULATES = 'modulation'


class Modulations:
    """Every modulating plugin's play for one render, by the plugin's name."""

    __slots__ = ('_plays',)

    def __init__(self, *, song, seed):
        self._plays = {name: registry.controller_of(name).modulation(song=song, seed=seed) for name in generator_plugins.plugins() if registry.fills(name=name, method=MODULATES)}

    def play_of(self, kind):
        """Return the play of the plugin of a name."""
        return self._plays[kind]

    def draws_in_order(self, *, kind, name):
        return self._plays[kind].draws_in_order(name)

    def snapshot(self):
        """Return where every play stands now, for a render after an edit that starts at a later scene."""
        return {kind: play.snapshot() for kind, play in self._plays.items()}

    def restore(self, snapshot):
        """Put every play back where a snapshot found it."""
        for kind, held in snapshot.items():
            self._plays[kind].restore(held)


def modulates(kind):
    """Return whether the generators of the plugin of a name change values as the song plays."""
    return registry.fills(name=kind, method=MODULATES)
