# noose6: a Python language and framework for producing MIDI clips.
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

from src.song import DEFAULT_TEMPO, Scene, Song, Track


def ramp(start, end, steps):
    """Return evenly spaced values from start to end, including both."""
    if type(steps) is not int or steps < 2:
        raise ValueError(f'invalid steps: {steps!r} (must be an integer of 2 or more)')
    return [start + (end - start) * step / (steps - 1) for step in range(steps)]


class Score:
    """Writes a song from top to bottom, one scene at a time, with up to five parts."""

    def __init__(self, tempo=DEFAULT_TEMPO):
        self.song = Song(tempo=tempo)
        self.melody_track = self.song.add_track(Track('Melody'))
        self.chord_track = self.song.add_track(Track('Chords'))
        self.bass_track = self.song.add_track(Track('Bass'))
        self.kick_track = self.song.add_track(Track('kick'))
        self.snare_track = self.song.add_track(Track('snare'))

    def play(self, name, melody, chords=None, bass=None, kick=None, snare=None):
        """Add a scene called name, with clips of the same name, and return it."""
        scene = self.song.add_scene(Scene(name))
        parts = [
            (self.melody_track, melody), (self.chord_track, chords), (self.bass_track, bass),
            (self.kick_track, kick), (self.snare_track, snare),
        ]
        for track, clip in parts:
            if clip is not None:
                self.song.set_clip(scene, track, clip.renamed(name))
        return scene
