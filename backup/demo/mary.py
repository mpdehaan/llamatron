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

"""Mary Had a Little Lamb, written out as a directory of MIDI files.

Run it from the top folder of this project:

    .venv/bin/python -m demo.mary

The files appear in ./output/mary, named <scene>-<track>.mid. Each scene is four
measures long, track 0 is the melody and track 1 is the chords.
"""

from llamatron.chord import ChordType
from llamatron.note import Note
from llamatron.renderers.clip_tree import ClipTree
from llamatron.song import Clip, Scene, Song, Track

OUTPUT_DIRECTORY = './output/mary'

# Note lengths, as fractions of a whole note.
WHOLE = 1
HALF = 0.5
QUARTER = 0.25

# The two chords that this song needs, each lasting a whole measure.
C_CHORD = Note('C', 3, WHOLE).to_chord(ChordType.MAJOR)
G7_CHORD = Note('G', 2, WHOLE).to_chord(ChordType.DOMINANT7)

# Each inner list is one scene.
MELODY = [
    [
        # Ma-ry had a
        Note('E', 4, QUARTER), Note('D', 4, QUARTER), Note('C', 4, QUARTER), Note('D', 4, QUARTER),
        # lit-tle lamb,
        Note('E', 4, QUARTER), Note('E', 4, QUARTER), Note('E', 4, HALF),
        # lit-tle lamb,
        Note('D', 4, QUARTER), Note('D', 4, QUARTER), Note('D', 4, HALF),
        # lit-tle lamb,
        Note('E', 4, QUARTER), Note('G', 4, QUARTER), Note('G', 4, HALF),
    ],
    [
        # Ma-ry had a
        Note('E', 4, QUARTER), Note('D', 4, QUARTER), Note('C', 4, QUARTER), Note('D', 4, QUARTER),
        # lit-tle lamb, its
        Note('E', 4, QUARTER), Note('E', 4, QUARTER), Note('E', 4, QUARTER), Note('E', 4, QUARTER),
        # fleece was white as
        Note('D', 4, QUARTER), Note('D', 4, QUARTER), Note('E', 4, QUARTER), Note('D', 4, QUARTER),
        # snow.
        Note('C', 4, WHOLE),
    ],
]

CHORDS = [
    [C_CHORD, C_CHORD, G7_CHORD, C_CHORD],
    [C_CHORD, C_CHORD, G7_CHORD, C_CHORD],
]


def build_song():
    song = Song(tempo=120)
    melody_track = song.add_track(Track('Melody'))
    chord_track = song.add_track(Track('Chords'))

    for melody, chords in zip(MELODY, CHORDS):
        scene = song.add_scene(Scene())
        song.set_clip(scene, melody_track, Clip(notes=melody))
        song.set_clip(scene, chord_track, Clip(notes=chords))

    return song


if __name__ == '__main__':
    ClipTree(OUTPUT_DIRECTORY, build_song()).render()
