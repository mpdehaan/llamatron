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

"""Mary Had a Little Lamb, loaded back from MIDI files and moved down into B flat minor.

Run demo.mary_arp first, because this reads the files it writes to ./output/mary3:

    .venv/bin/python -m demo.mary_arp
    .venv/bin/python -m demo.mary_transpose

The files appear in ./output/mary5.
"""

import os

from src.generators.transpose_scale import TransposeScale
from src.importers.clip_tree import ClipTreeImporter
from src.note import Note
from src.renderers.clip_tree import ClipTree
from src.scale import Scale, ScaleType

INPUT_DIRECTORY = './output/mary3'
OUTPUT_DIRECTORY = './output/mary5'

C_MAJOR = Scale(Note('C', 4), ScaleType.MAJOR)
B_FLAT_MINOR = Scale(Note('Bb', 3), ScaleType.MINOR)


def build_song():
    song = ClipTreeImporter(INPUT_DIRECTORY).load()
    to_minor = TransposeScale(input_scale=C_MAJOR, output_scale=B_FLAT_MINOR)

    for scene in song.scenes:
        for track in song.tracks:
            clip = song.get_clip(scene, track)
            if clip is not None:
                song.set_clip(scene, track, to_minor.generate(clip))

    return song


def main():
    if not os.path.isdir(INPUT_DIRECTORY):
        print(f'{INPUT_DIRECTORY} is missing, so please run this demo first: '
              '.venv/bin/python -m demo.mary_arp')
        return
    ClipTree(OUTPUT_DIRECTORY, build_song()).render()


if __name__ == '__main__':
    main()
