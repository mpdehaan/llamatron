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

"""Mary Had a Little Lamb, with the chords played one note at a time using Arp.

Run it from the top folder of this project:

    .venv/bin/python -m demo.mary_arp

The files appear in ./output/mary3. The melody is the same as in demo/mary.py. Try
changing the ChordOrder to UP, DOWN, DOWN_UP or RANDOM to hear the difference.
"""

from demo.mary import CHORDS, MELODY
from llamatron.generators.arp import Arp, ChordOrder
from llamatron.renderers.clip_tree import ClipTree
from llamatron.song import Clip, Scene, Song, Track

OUTPUT_DIRECTORY = './output/mary3'

EIGHTH = 0.125


def build_song():
    song = Song(tempo=120)
    melody_track = song.add_track(Track('Melody'))
    chord_track = song.add_track(Track('Chords'))
    arpeggiate = Arp(EIGHTH, ChordOrder.UP_DOWN)

    for melody, chords in zip(MELODY, CHORDS):
        scene = song.add_scene(Scene())
        song.set_clip(scene, melody_track, Clip(notes=melody))
        song.set_clip(scene, chord_track, arpeggiate.generate(Clip(notes=chords)))

    return song


if __name__ == '__main__':
    ClipTree(OUTPUT_DIRECTORY, build_song()).render()
