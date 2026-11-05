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

"""Mary Had a Little Lamb, with the melody written as scale degrees.

Run it from the top folder of this project:

    .venv/bin/python -m demo.mary_degrees

The files appear in ./output/mary4. The melody only says which degree of the scale to
play, so try changing the song's scale to hear it in another key.
"""

from llamatron.note import Degree, Note
from llamatron.renderers.clip_tree import ClipTree
from llamatron.scale import Scale, ScaleType
from llamatron.song import Clip, Scene, Song, Track

OUTPUT_DIRECTORY = './output/mary4'

WHOLE = 1
HALF = 0.5
QUARTER = 0.25

SCALE = Scale(Note('C', 4), ScaleType.MAJOR)

# A plain number lasts a quarter note, because of the clip's note_length.
MELODY = [
    [3, 2, 1, 2, 3, 3, Degree(3, HALF), 2, 2, Degree(2, HALF), 3, 5, Degree(5, HALF)],
    [3, 2, 1, 2, 3, 3, 3, 3, 2, 2, 3, 2, Degree(1, WHOLE)],
]


def build_song():
    song = Song(tempo=120, scale=SCALE)
    melody_track = song.add_track(Track('Melody'))

    for melody in MELODY:
        scene = song.add_scene(Scene())
        song.set_clip(scene, melody_track, Clip(notes=melody, note_length=QUARTER))

    return song


if __name__ == '__main__':
    ClipTree(OUTPUT_DIRECTORY, build_song()).render()
