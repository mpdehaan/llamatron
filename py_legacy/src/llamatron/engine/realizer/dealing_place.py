# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Where a generator that deals notes out among tracks works: a written-out scene, with what the Realizer knows there of the
tracks that name the generator and of the notes it can deal, which a plugin's controller asks for."""


class DealingPlace:
    """A generator that deals notes out, in a written-out scene: the answers its plugin's controller may ask for."""

    __slots__ = ('_realizer', '_output', '_scene', '_name')

    def __init__(self, *, realizer, output, scene, name):
        """output is the render's TrackOutput, and name the generator's."""
        self._realizer = realizer
        self._output = output
        self._scene = scene
        self._name = name

    def pool(self, *, source, scene=None):
        """Return the tracks whose clips name the generator in a scene, the place's own unless given, but the source, in the song's track order."""
        return [track for track in self._output.tracks_naming(scene=scene or self._scene, name=self._name) if track != source]

    def plays(self, *, source, scene=None):
        """Return whether a source track is a track of the song with a clip in a scene, the place's own unless given."""
        return self._output.plays_source(scene=scene or self._scene, source=source)

    def turns(self, *, source, scene=None):
        """Return a source track's notes in a scene, the place's own unless given, as turns: the notes that start together, each a HandedNote, in time order."""
        return self._output.source_turns(scene=scene or self._scene, source=source)

    def earlier_scenes_in_run(self, restart):
        """Return the written-out scenes before the place's own in the generator's run, which its Restart says."""
        scenes = self._realizer.get_scenes()
        start = scenes.index(self._realizer.run_start(scene=self._scene, restart=restart))
        return scenes[start:scenes.index(self._scene)]
