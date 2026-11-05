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

"""Mary Had a Little Lamb, with a shuffled melody using MixUp and MixUp2.

Run it from the top folder of this project:

    .venv/bin/python -m demo.mary_mix_up

The files appear in ./output/mary8. The chords are the same as in demo/mary.py. The first
scene's melody uses MixUp, which swaps notes with any other note, and the second uses
MixUp2, which swaps notes with the next note. Try changing the probabilities, or remove
the seeds to get a different result every time.
"""

from demo.mary import CHORDS, MELODY
from src.legacy.generators.mix_up import MixUp
from src.legacy.generators.mix_up2 import MixUp2
from src.renderers.clip_tree import ClipTree
from src.song import Clip, Scene, Song, Track

OUTPUT_DIRECTORY = './output/mary8'

GENERATORS = [MixUp([0.25], seed=1), MixUp2([0.25], seed=1)]


def build_song():
    song = Song(tempo=120)
    melody_track = song.add_track(Track('Melody'))
    chord_track = song.add_track(Track('Chords'))

    for melody, chords, generator in zip(MELODY, CHORDS, GENERATORS):
        scene = song.add_scene(Scene())
        song.set_clip(scene, melody_track, generator.generate(Clip(notes=melody)))
        song.set_clip(scene, chord_track, Clip(notes=chords))

    return song


if __name__ == '__main__':
    ClipTree(OUTPUT_DIRECTORY, build_song()).render()
