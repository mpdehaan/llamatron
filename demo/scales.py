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

"""Every supported scale, with each one in its own scene.

Run it from the top folder of this project:

    .venv/bin/python -m demo.scales

The files appear in ./output/scales, named after their scales. Each clip plays one full
octave of its scale in quarter notes, from C4 up to C5.
"""

from src.note import Note
from src.renderers.clip_tree import ClipTree
from src.scale import Scale, ScaleType
from src.song import Clip, Scene, Song, Track

OUTPUT_DIRECTORY = './output/scales'

QUARTER = 0.25
ROOT = Note('C', 4, QUARTER)


def build_song():
    song = Song(tempo=120)
    track = song.add_track(Track('Scales'))

    for scale_type in ScaleType:
        scale = Scale(ROOT, scale_type)
        scene = song.add_scene(Scene(scale_type.name))
        clip = Clip(scale_type.name, notes=scale.octaves(1), scale=scale)
        song.set_clip(scene, track, clip)

    return song


if __name__ == '__main__':
    ClipTree(OUTPUT_DIRECTORY, build_song()).render()
