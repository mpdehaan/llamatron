# llamatron: a Python language and framework for producing MIDI clips.
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

"""One scene of the song as it plays, with a repeating scene written out once for each repeat."""

# Scenes are numbered from 1 as they play, and so are a scene's repeats in their names.
FIRST_NUMBER = 1
# A scene's repeats are counted from 0 as they're written out.
FIRST_REPEAT = 0
# A scene with no name of its own is named by its number, and a repeat adds its number to the name.
UNNAMED_SCENE = 'Scene {number}'
REPEAT_NAME = '{name} {repeat}'
# How error messages name a scene.
DESCRIPTION = 'scene {number} ({name})'


class WrittenScene:
    """A scene's place in the song, counted from 1, with the name, scale and tempo it plays with."""

    __slots__ = ('_number', '_name', '_scale_name', '_tempo', '_scene', '_resets')

    def __init__(self, number, name, scale_name, tempo, scene, resets):
        self._number = number
        self._name = name
        self._scale_name = scale_name
        self._tempo = tempo
        self._scene = scene
        self._resets = resets

    @classmethod
    def write_out(cls, song):
        """Return every scene of a song in order, with a scene that repeats written out once for each repeat.

        A scene uses its own scale, or else the song's, and a repeat's name gets its number. A
        scene resets its registers only as it first starts, not on every repeat.
        """
        written = []
        for scene in song.get_scenes():
            scale = scene.get_scale_name() or song.get_scale_name()
            repeat = scene.get_repeat()
            for place in range(repeat):
                number = len(written) + FIRST_NUMBER
                name = _scene_name(scene.get_name(), number)
                if repeat > 1:
                    name = REPEAT_NAME.format(name=name, repeat=place + FIRST_NUMBER)
                resets = scene.get_reset_names() if place == FIRST_REPEAT else []
                written.append(cls(number, name, scale, scene.get_tempo(place), scene, resets))
        return written

    def get_number(self):
        return self._number

    def get_name(self):
        return self._name

    def get_scale_name(self):
        """Return the name of the scale it plays in, or None if neither it nor the song has one."""
        return self._scale_name

    def get_tempo(self):
        """Return its tempo, or None to use the song's."""
        return self._tempo

    def get_track_names(self):
        return self._scene.get_track_names()

    def get_reset_names(self):
        """Return the registers it sets back to their defaults as it starts."""
        return list(self._resets)

    def get_cell(self, track):
        """Return what it plays on a track, or None if nothing."""
        return self._scene.get_cell(track)

    def describe(self):
        """Return how error messages name it, like "scene 3 (verse)"."""
        return DESCRIPTION.format(number=self._number, name=self._name)


def _scene_name(name, number):
    """Return a scene's name as text, or one made from its number if it has none."""
    return str(UNNAMED_SCENE.format(number=number) if name is None else name)
