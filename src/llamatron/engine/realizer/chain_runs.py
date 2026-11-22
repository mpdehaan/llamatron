# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What a clip runs its notes through, in order: its built-in generators that run before its own lists of generators, the
chains its clip's, its scene's and its track's lists name, then the built-ins that run after them. A clip's built-in that is
switched on stands in for its track's of the same kind whole."""

from typing import NamedTuple

from llamatron.model.schema import generator_plugins
from llamatron.user_strings import names

# What a built-in generator goes by where a generator's name is asked for: in a message and in what keeps a generator's state
# from one clip to the next, which a clip's built-in shares with its track's, so that the same track carries on whichever ran.
BUILT_IN_NAME = names.MSG_BUILT_IN_NAME
NO_STATEMENTS = ()


class ChainRun(NamedTuple):
    """One run of a clip's notes through a chain: the name it goes by, and the chain, which answers get_steps() and
    get_bypass_when()."""

    name: str
    chain: object


class BuiltInStep(NamedTuple):
    """A built-in generator as a step of a chain: its kind, the name it goes by, and its settings, which it holds itself."""

    kind: str
    name: str
    settings: object

    def settings_in(self, setlist):
        """Return the generator's settings, which a built-in holds itself, whatever the set."""
        return self.settings


class BuiltInChain:
    """A chain of one built-in generator, with no statements of its own: the clip's, its scene's and its track's still bypass it."""

    __slots__ = ('_steps',)

    def __init__(self, step):
        self._steps = [step]

    def get_steps(self):
        return list(self._steps)

    def get_bypass_when(self):
        return list(NO_STATEMENTS)


def chain_runs(*, setlist, clip_slot, scene, track):
    """Return the ChainRuns of a clip in a scene on a track, in order: its built-ins before the lists, the chains of its own, its
    scene's and its track's lists, then its built-ins after them."""
    on_clip = clip_slot.built_ins_on()
    on_track = track.built_ins_on()
    lists = [*clip_slot.get_chain_names(), *scene.get_chain_names(), *track.get_chain_names()]
    runs = []
    if on_clip or on_track:
        runs += _built_in_runs(kinds=generator_plugins.built_ins_before_list(), clip_slot=clip_slot, track=track, on_clip=on_clip, on_track=on_track)
    for name in lists:
        runs.append(ChainRun(name, setlist.chain_run(name)))
    if on_clip or on_track:
        runs += _built_in_runs(kinds=generator_plugins.built_ins_after_list(), clip_slot=clip_slot, track=track, on_clip=on_clip, on_track=on_track)
    return runs


def _built_in_runs(*, kinds, clip_slot, track, on_clip, on_track):
    """Return a run for each of some built-in kinds the clip or its track has switched on, the clip's standing in for the track's."""
    runs = []
    for kind in kinds:
        holder = None
        if kind in on_clip:
            holder = clip_slot
        elif kind in on_track:
            holder = track
        if holder is not None:
            runs.append(ChainRun(BUILT_IN_NAME, BuiltInChain(BuiltInStep(kind, BUILT_IN_NAME, holder.get_built_in(kind)))))
    return runs
