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

"""Rendering a composed Song into a ClipGrid of finished clips, for the renderers to write."""

from fractions import Fraction

from llamatron.composition.song_file_error import SongFileError
from llamatron.playback.cell_player import CellPlayer
from llamatron.playback.grab_source import GrabSource
from llamatron.playback.written_scene import WrittenScene
from llamatron.song import ClipGrid, Scene, Track


class SongRenderer:
    """Plays every scene of a song into finished clips, remembering each clip once it's played.

    Clips are played when they're first asked for, so that a clip that grabs from another track
    can simply ask for that track's clip, and a grab that goes round in a circle is caught.
    """

    def __init__(self, song):
        self._song = song
        self._scenes = WrittenScene.write_out(song)
        self._clips = {}
        self._lengths = {}
        # The tracks whose clips are waiting on a grab, to catch clips that grab in a circle.
        self._grabbing = []

    def render(self):
        """Return a ClipGrid with every scene's finished clips, or raise SongFileError."""
        tempo = float(self._song.get_tempo())
        grid = ClipGrid(tempo=int(tempo) if tempo.is_integer() else tempo)
        tracks = {
            name: grid.add_track(Track(name, mute=self._song.get_track(name).is_muted()))
            for name in self._song.get_track_names()
        }
        for scene in self._scenes:
            tempo = None if scene.get_tempo() is None else float(scene.get_tempo())
            grid_scene = grid.add_scene(Scene(scene.get_name(), tempo=tempo))
            for name in self._song.get_track_names():
                clip = self.get_clip(scene, name)
                if clip is not None:
                    grid.set_clip(grid_scene, tracks[name], clip)
        return grid

    def estimate(self):
        """Return how long each written-out scene and its clips last, in seconds.

        Each item is (number, seconds or None, {track: seconds or None}, problem or None). This
        runs the same code as render, so that it can't disagree with a render, but a problem in
        one scene only affects that scene.
        """
        result = []
        for scene in self._scenes:
            tempo = self._song.get_tempo() if scene.get_tempo() is None else scene.get_tempo()
            whole_notes_to_seconds = Fraction(240) / tempo
            clips, problem, seconds = {}, None, None
            try:
                seconds = self.get_scene_length(scene) * whole_notes_to_seconds
                for track in scene.get_track_names():
                    clips[track] = self.get_clip(scene, track).total_length() * whole_notes_to_seconds
            except SongFileError as error:
                problem = str(error)
            result.append((scene.get_number(), seconds, clips, problem))
        return result

    def get_clip(self, scene, track, grabbing=True):
        """Return the finished clip a track plays in a written-out scene, or None if it plays nothing."""
        cell = scene.get_cell(track)
        if cell is None:
            return None
        grabbing = grabbing and cell.get_grab_track() is not None
        key = (scene.get_number(), track, grabbing)
        if key not in self._clips:
            self._clips[key] = CellPlayer(self, self._song, scene, track).play(grabbing)
        return self._clips[key]

    def get_scene_length(self, scene):
        """Return how long a scene lasts, which is its longest clip that doesn't loop."""
        number = scene.get_number()
        if number in self._lengths:
            return self._lengths[number]
        cells = [scene.get_cell(track) for track in scene.get_track_names()]
        if cells and all(cell.loops() for cell in cells):
            raise SongFileError(f'{scene.describe()}: every clip is set to loop, so the scene would never end. Turn off loop on at least one clip.')
        length = Fraction(0)
        for track in scene.get_track_names():
            if not scene.get_cell(track).loops():
                # Grabbing only changes pitches, so lengths come from clips played without it, which
                # means a clip can grab from one that loops to fill the scene.
                length = max(length, self.get_clip(scene, track, grabbing=False).total_length())
        self._lengths[number] = length
        return length

    def get_grab_source(self, scene, track):
        """Return the notes the track that a track's cell grabs from plays in a scene, or None if it plays nothing there."""
        other = scene.get_cell(track).get_grab_track()
        if scene.get_cell(other) is None:
            return None
        waiting = [*self._grabbing, track]
        if other in waiting:
            loop = ' → '.join([*waiting[waiting.index(other):], other])
            raise SongFileError(f'{scene.describe()}: circular grab: {loop}. Remove the grab track from one of these clips.')
        self._grabbing.append(track)
        try:
            source = self.get_clip(scene, other)
        finally:
            self._grabbing.pop()
        return GrabSource(source)

    def make_generator(self, step, scene, track, chain, index):
        """Return the generator for one step of a chain, as a cell on a track in a scene uses it.

        An arp with no seed of its own gets one from the song's, which differs for every scene,
        track and place in the chain, so that a render is always the same.
        """
        kind, name = step
        settings = self._song.get_generator_settings(kind, name)
        place = self._song.get_track_names().index(track)
        seed = self._song.get_seed() * 1_000_003 + scene.get_number() * 1_009 + place * 31 + index
        return settings.make_generator(f'chain {chain!r}, {kind}', seed)
