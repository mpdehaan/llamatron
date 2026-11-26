# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What a render made of a song, as those who play or show it ask after the render: the written-out rows of each scene, the
clips that loop through their scene, the moments the draws drew, and what was taken from an earlier render."""


class Realization:
    """One render's answers about the song it realized, each worked out by the Realizer that made it."""

    __slots__ = ('_realizer', '_song')

    def __init__(self, *, realizer, song):
        self._realizer = realizer
        self._song = song

    def rows_of_scene(self, index):
        """Return the places in the grid of a scene's written-out rows, one for each repeat, in order."""
        scene = self._song.get_scenes()[index]
        return [place for place, written in enumerate(self._realizer.get_scenes()) if written.get_scene() is scene]

    def loops_through(self, *, scene, track):
        """Return whether a track's clip in a scene loops for as long as the scene lasts."""
        return self._realizer.fills_its_scene(scene=scene, track=track)

    def draw_moments(self, row):
        """Return the moments in a written-out row at which a draw drew, in whole notes from the row's start, with where every draw then stood."""
        return self._realizer.get_timeline(self._realizer.get_scenes()[row]).get_draw_moments()

    def kept_tracks(self, rows):
        """Return the tracks whose clips were taken from an earlier render in every written-out row given."""
        scenes = self._realizer.get_scenes()
        return self._realizer.kept_tracks([scenes[row] for row in rows])

    def get_reused_scene_count(self):
        return self._realizer.get_reused_scene_count()

    def get_kept_clip_count(self):
        return self._realizer.get_kept_clip_count()

    def has_taken_anything(self):
        return self._realizer.has_taken_anything()
