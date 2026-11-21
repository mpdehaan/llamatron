# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Where one step of a chain runs: the clip of a track in a written-out scene, and what the Realizer knows there, which a
generator plugin's controller asks for as it makes the generator that runs."""

from typing import NamedTuple

from llamatron.user_strings import errors


class ClipBeingMade(NamedTuple):
    """The clip a step runs in: a track's in a written-out scene, and whether this is the pass that counts register changes."""

    scene: object
    track: str
    counting: bool


class StepInChains(NamedTuple):
    """A step of a clip's chains: the step, the chain that holds it, its place among all the clip's chains' steps, and what
    keeps its end state apart, None where none is kept."""

    step: object
    chain: str
    index: int
    key: object


class ChainStepPlace:
    """One step of a chain, run by a track's clip in a written-out scene: the answers a plugin's controller may ask for, each
    worked out only when asked, so that a generator that needs none of them costs nothing for them."""

    __slots__ = ('_realizer', '_song', '_step', '_scene', '_track', '_chain', '_index', '_key', '_counting')

    def __init__(self, *, realizer, clip, step):
        """clip is the ClipBeingMade the step runs in, and step the StepInChains."""
        self._realizer = realizer
        self._song = realizer.get_song()
        self._step = step.step
        self._scene = clip.scene
        self._track = clip.track
        self._chain = step.chain
        self._index = step.index
        self._key = step.key
        self._counting = clip.counting

    def where(self):
        """Return where a problem with the generator's settings is, for its message: its chain and kind."""
        return errors.ERR_WHERE_CHAIN.format(chain=self._chain, kind=self._step.kind)

    def seed(self):
        """Return the seed a generator that chooses at random takes when its settings give none, or None for an unseeded render."""
        return self._realizer.chain_step_seed(scene=self._scene, track=self._track, index=self._index)

    def pattern_step(self):
        """Return the step size of the pattern the clip plays."""
        return self._song.get_pattern_step_size(self._song.get_pattern(self._scene.get_clip_slot(self._track).get_pattern_name()))

    def bar(self):
        return self._song.get_time_signature().bar_length()

    def beat(self):
        return self._song.get_time_signature().beat_length()

    def tempo(self):
        """Return the scene's tempo, or the song's where the scene sets none."""
        return self._song.get_tempo() if self._scene.get_tempo() is None else self._scene.get_tempo()

    def section(self):
        """Return the kind of section the scene is, as the song wizard named it, or None."""
        return self._scene.get_scene().get_section()

    def plays_drums(self):
        """Return whether the clip plays a drum pattern."""
        return self._realizer.plays_drums(scene=self._scene, track=self._track)

    def continuation(self, settings):
        """Return where a generator with these settings carries on from in the clip, or None where its end state isn't kept."""
        if self._key is None:
            return None
        return self._realizer.continuation(settings=settings, scene=self._scene, track=self._track, key=self._key, counting=self._counting)

    def chords_followed(self, source):
        """Return the chords a track of the song plays in the scene, after its own chains, or None."""
        return self._realizer.chords_followed(scene=self._scene, track=self._track, source=source, counting=self._counting)

    def tune_heard(self, source):
        """Return when the tune sounds on a track of the song in the scene, after its own chains, or None."""
        return self._realizer.tune_heard(scene=self._scene, track=self._track, source=source, counting=self._counting)
