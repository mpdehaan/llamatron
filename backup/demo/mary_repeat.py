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

"""Mary Had a Little Lamb, with each chord played twice using Repeater.

Run it from the top folder of this project:

    .venv/bin/python -m demo.mary_repeat

The files appear in ./output/mary2. The melody is the same as in demo/mary.py, and
each whole-note chord becomes two half notes, so the clips stay four measures long.
"""

from demo.mary import CHORDS, MELODY
from llamatron.generators.repeater import Repeater
from llamatron.renderers.clip_tree import ClipTree
from llamatron.song import Clip, Scene, Song, Track

OUTPUT_DIRECTORY = './output/mary2'


def build_song():
    song = Song(tempo=120)
    melody_track = song.add_track(Track('Melody'))
    chord_track = song.add_track(Track('Chords'))
    repeat_twice = Repeater(2)

    for melody, chords in zip(MELODY, CHORDS):
        scene = song.add_scene(Scene())
        song.set_clip(scene, melody_track, Clip(notes=melody))
        song.set_clip(scene, chord_track, repeat_twice.generate(Clip(notes=chords)))

    return song


if __name__ == '__main__':
    ClipTree(OUTPUT_DIRECTORY, build_song()).render()
