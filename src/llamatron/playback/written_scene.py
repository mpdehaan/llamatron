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


class WrittenScene:
    """A scene's place in the song, counted from 1, with the name, scale and tempo it plays with."""

    def __init__(self, number, name, scale_name, tempo, scene):
        self._number = number
        self._name = name
        self._scale_name = scale_name
        self._tempo = tempo
        self._scene = scene

    @classmethod
    def write_out(cls, song):
        """Return every scene of a song in order, with a scene that repeats written out once for each repeat.

        A scene uses its own scale, or else the song's, and a repeat's name gets its number.
        """
        written = []
        for scene in song.get_scenes():
            scale = scene.get_scale_name() or song.get_scale_name()
            repeat = scene.get_repeat()
            for place in range(repeat):
                name = scene.get_name()
                name = str(f'Scene {len(written) + 1}' if name is None else name)
                if repeat > 1:
                    name = f'{name} {place + 1}'
                written.append(cls(len(written) + 1, name, scale, scene.get_tempo(place), scene))
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

    def get_cell(self, track):
        """Return what it plays on a track, or None if nothing."""
        return self._scene.get_cell(track)

    def describe(self):
        """Return how error messages name it, like "scene 3 (verse)"."""
        return f'scene {self._number} ({self._name})'
