# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""How long everything in a song lasts, measured once and kept until the song changes."""

from typing import NamedTuple

from llamatron.support.rational import Rational
from llamatron.composition.song_file_error import SongFileError
from llamatron.playback.song_renderer import SongRenderer
from llamatron.tui.text import SECONDS_PER_MINUTE

QUARTER_NOTES_PER_WHOLE_NOTE = 4
NO_SECONDS = Rational(0)


class Measured(NamedTuple):
    """One estimate of a song, with what every page asks of it worked out once: plain data, so that it can be kept and compared.

    plays is a SceneEstimate for each play of each scene, a scene's repeats one after another.
    scene_plays is, for each scene, the places in plays of its plays. scene_seconds is, for each
    scene, how long all of its repeats last, or None where one can't be worked out. problem is
    what stops the whole song from being estimated, when plays is empty.
    """

    plays: list
    problem: object
    scene_plays: list
    scene_seconds: list
    longest_scene_seconds: object
    song_seconds: object


def all_or_none(values):
    """Return the sum of some lengths, or None if any of them is unknown."""
    return None if any(value is None for value in values) else sum(values, NO_SECONDS)


def plays_of_each_scene(song):
    """Return, for each scene of a song, the places of its plays among every play of the song, its repeats one after another."""
    places = []
    start = 0
    for scene in song.get_scenes():
        places.append(range(start, start + scene.get_repeat()))
        start += scene.get_repeat()
    return places


def seconds_of_each_scene(*, plays, scene_plays):
    """Return, for each scene, how long all of its repeats last, or None where one can't be worked out."""
    return [all_or_none([plays[place].seconds for place in places]) for places in scene_plays]


def measured(song):
    """Return a song's estimate with every scene's plays and seconds worked out, which costs one pass over the scenes however many pages ask.

    A song that can't be estimated at all has a problem and no plays, and each of its scenes has
    no length.
    """
    scene_plays = plays_of_each_scene(song)
    try:
        plays = SongRenderer(song).estimate()
    except SongFileError as error:
        unknown = [None for _ in scene_plays]
        return Measured(plays=[], problem=str(error), scene_plays=scene_plays, scene_seconds=unknown, longest_scene_seconds=None, song_seconds=None)
    scene_seconds = seconds_of_each_scene(plays=plays, scene_plays=scene_plays)
    known = [seconds for seconds in scene_seconds if seconds is not None]
    return Measured(
        plays=plays, problem=None, scene_plays=scene_plays, scene_seconds=scene_seconds,
        longest_scene_seconds=max(known) if known else None, song_seconds=all_or_none([play.seconds for play in plays]),
    )


class Lengths:
    """The lengths of a song's scenes, clips and patterns in seconds.

    The lengths of scenes and clips come from one estimate of the song, which the document
    measures the first time one is asked for and keeps until the song changes: measure is what
    returns it. A pattern's own length and step size need no estimate, so asking for those never
    takes one, which matters in the pattern editor, where every edit changes the song and only the
    pattern's own length is shown. The estimate works a scene's length out without playing it where
    it can, and a scene that can't be rendered gets a problem instead of a length.
    """

    __slots__ = ('_song', '_measure')

    def __init__(self, *, song, measure):
        self._song = song
        self._measure = measure

    def song_seconds(self):
        """Return how long the song lasts, or None if any scene can't be worked out."""
        return self._measure().song_seconds

    def _first_play(self, index):
        """Return the estimate of a scene's first play, which its clips are measured against."""
        estimate = self._measure()
        return estimate.plays[estimate.scene_plays[index][0]]

    def scene_seconds(self, index):
        """Return how long a scene and all of its repeats last, or None if it can't be worked out."""
        return self._measure().scene_seconds[index]

    def scene_play_seconds(self, index):
        """Return how long one play of a scene lasts, its first, which its clips are measured against, or None."""
        if self._measure().problem:
            return None
        return self._first_play(index).seconds

    def longest_scene_seconds(self):
        """Return the length of the longest scene with all its repeats, or None if none can be worked out."""
        return self._measure().longest_scene_seconds

    def scene_problem(self, index):
        """Return what stops a scene from rendering, or None."""
        estimate = self._measure()
        if estimate.problem:
            return estimate.problem
        for place in estimate.scene_plays[index]:
            if estimate.plays[place].problem:
                return estimate.plays[place].problem
        return None

    def clip_seconds(self, *, index, track):
        """Return how long a clip lasts on the first play of its scene, or None."""
        if self._measure().problem:
            return None
        return self._first_play(index).clip_seconds.get(track)

    def pattern_seconds(self, name):
        """Return how long one play of a pattern lasts at the song's tempo."""
        return self.pattern_length(name) * SECONDS_PER_MINUTE * QUARTER_NOTES_PER_WHOLE_NOTE / self._song.get_tempo()

    def pattern_length(self, name):
        """Return how long one play of a pattern lasts, in fractions of a whole note."""
        return self._song.get_pattern_length(self._song.get_pattern(name))

    def step_size(self, name):
        """Return how long each step of a pattern is: its own step size, or else the song's."""
        return self._song.get_pattern_step_size(self._song.get_pattern(name))
