# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What carries through a song as one render plays it, apart from any one clip: the registers and draws it starts from, the
random streams every choice is drawn from and each clip's take, the song's modulations, and where those streams stood as
each written-out scene started, for a later render that takes its first scenes from this one."""

from llamatron.engine.realizer.modulations import Modulations
from llamatron.engine.realizer.scene_reuse import SceneCheckpoint
from llamatron.math.random_source import random_source
from llamatron.model.schema import file_format

# A seed made from a place: the song's seed, a scene's number and a track's place, multiplied by these so that each comes out different.
SEED_SONG_FACTOR = 1_000_003
SEED_SCENE_FACTOR = 1_009
SEED_TRACK_FACTOR = 31
# How far a clip's seeds move for each take after the first, a prime far past what a song's places reach.
SEED_TAKE_FACTOR = 1_000_000_007
FIRST_TAKE = 0
# The seed the song's random draws start afresh from as a retaken scene first starts.
DRAWS_TAKE_SEED = '{seed}/{scene}/draws take {take}'
# The registers' random values, for a Reset behavior that picks one, come from a generator of their own, so that they can't change what probability or an arp draws.
REGISTER_SEED_OFFSET = 7
# What a strum's seed adds, so that its loose timing draws apart from everything else, and how many seeds a render picks from.
STRUM_SEED_OFFSET = 977
STRUM_SEEDS = 1_000_000


class SongState:
    """The state of a song through one render, which the Realizer walks scene by scene and every clip reads."""

    __slots__ = ('_song', '_seed', '_takes', '_song_places', '_registers', '_draws', '_register_chooser', '_modulations', '_strum_seed', '_checkpoints')

    def __init__(self, *, song, seed, takes, keeps_checkpoints):
        """takes gives a clip new random choices by (the scene's place in the song, the track); keeps_checkpoints says whether
        to keep where the streams stood as each written scene started, for a later render to take its first scenes from."""
        self._song = song
        self._seed = seed
        self._takes = {}
        if takes is not None:
            self._takes = dict(takes)
        self._song_places = {id(scene): place for place, scene in enumerate(song.get_scenes())}
        self._registers = {name: song.get_register(name) for name in file_format.REGISTER_NAMES}
        self._draws = {name: song.get_draw(name) for name in file_format.DRAW_NAMES}
        register_seed = None
        strum_seed = None
        if seed is not None:
            register_seed = seed * SEED_SONG_FACTOR + REGISTER_SEED_OFFSET
            strum_seed = seed * SEED_SONG_FACTOR + STRUM_SEED_OFFSET
        self._register_chooser = random_source(register_seed)
        self._modulations = Modulations(song=song, seed=seed)
        # What every strum's loose timing draws from, fixed for the render so that every export of it and its playing agree.
        strum_chooser = random_source(strum_seed)
        self._strum_seed = strum_chooser.randrange(STRUM_SEEDS)
        self._checkpoints = None
        if keeps_checkpoints:
            self._checkpoints = []

    def get_seed(self):
        """Return the seed this render makes every random choice from, or None for a new take."""
        return self._seed

    def get_takes(self):
        return self._takes

    def get_checkpoints(self):
        return self._checkpoints

    def get_registers(self):
        return self._registers

    def get_draws(self):
        return self._draws

    def get_register_chooser(self):
        """Return what draws the registers' and the draws' random values."""
        return self._register_chooser

    def get_modulations(self):
        """Return the song's modulations as they play, which every clip naming a modulating generator hears."""
        return self._modulations

    def song_place(self, scene):
        """Return a written-out scene's scene's place in the song, counted from 0."""
        return self._song_places[id(scene.get_scene())]

    def take_of(self, *, scene, track):
        """Return which take a written-out scene's clip on a track plays, 0 unless the render was given another."""
        return self._takes.get((self.song_place(scene), track), FIRST_TAKE)

    def taken_seed(self, *, seed, scene, track):
        """Return a whole-number seed made from a clip's place moved on by the clip's take, the same seed for take 0."""
        return seed + self.take_of(scene=scene, track=track) * SEED_TAKE_FACTOR

    def chain_step_seed(self, *, scene, track, index):
        """Return the seed a generator that chooses at random takes at a place in a clip's chains when its settings give none:
        one made from the render's, which differs for every scene, track and place in the chain, so that a seeded render is
        always the same; None for a render with no seed, so that the generator draws its own random numbers."""
        if self._seed is None:
            return None
        place = self._song.get_track_names().index(track)
        return self.taken_seed(seed=self._seed * SEED_SONG_FACTOR + scene.get_number() * SEED_SCENE_FACTOR + place * SEED_TRACK_FACTOR + index, scene=scene, track=track)

    def strum_seed(self, *, scene, track):
        """Return the seed a clip's strum draws its loose timing from."""
        place = self._song.get_track_names().index(track)
        return self.taken_seed(seed=self._strum_seed + scene.get_number() * SEED_SCENE_FACTOR + place * SEED_TRACK_FACTOR, scene=scene, track=track)

    def retaken(self, earlier):
        """Return the (scene's place in the song, track) of every clip whose take differs from an earlier render's state's."""
        return {key for key in set(self._takes) | set(earlier.get_takes()) if self._takes.get(key, FIRST_TAKE) != earlier.get_takes().get(key, FIRST_TAKE)}

    def draw_afresh_for_a_take(self, *, written, scene_before):
        """As a retaken scene first starts, before its repeats, start the song's random draws afresh from the seed, the scene and its
        take, so that a draw that takes any value, or each value once, draws anew on every take, as a looping scene's laps and a
        scene launched again do, rather than as the take before drew; its repeats then draw on from one another as ever.
        scene_before is the written-out scene before, or None for the first."""
        place = self.song_place(written)
        take = max((self._takes.get((place, track), FIRST_TAKE) for track in written.get_track_names()), default=FIRST_TAKE)
        if take == FIRST_TAKE or self._seed is None:
            return
        if scene_before is not None and scene_before.get_scene() is written.get_scene():
            return
        self._register_chooser.seed(DRAWS_TAKE_SEED.format(seed=self._seed, scene=place, take=take))

    def note_scene_start(self):
        """Keep where the random streams stand as a written scene starts, where checkpoints are kept."""
        if self._checkpoints is not None:
            self._checkpoints.append(SceneCheckpoint(self._register_chooser.getstate(), self._modulations.snapshot()))

    def can_carry_on_from(self, earlier):
        """Return whether this state can take scenes from an earlier render's: both keep checkpoints and draw from one seed."""
        return earlier.get_checkpoints() is not None and self._checkpoints is not None and self._seed is not None and earlier.get_seed() == self._seed

    def take_scenes(self, *, earlier, count):
        """Take an earlier render's checkpoints of its first count written scenes, and its random streams as they stood as the next one started."""
        self._checkpoints = earlier.get_checkpoints()[:count]
        if count < len(earlier.get_checkpoints()):
            checkpoint = earlier.get_checkpoints()[count]
            self._register_chooser.setstate(checkpoint.register_state)
            self._modulations.restore(checkpoint.modulations)
