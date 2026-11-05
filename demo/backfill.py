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

"""A sparse pattern that fills in a little more with each scene, using Backfill.

Run it from the top folder of this project:

    .venv/bin/python -m demo.backfill

The files appear in ./output/backfill. Run_0 is the original pattern, and each later
clip is Backfill applied to the clip before it. Try lowering the probabilities to
have it fill in less, and more differently each time.
"""

from src.generators.backfill import Backfill
from src.note import Note, Rest
from src.renderers.clip_tree import ClipTree
from src.scale import Scale, ScaleType
from src.song import Clip, Scene, Song, Track

OUTPUT_DIRECTORY = './output/backfill'

WHOLE = 1
SIXTEENTH = 0.0625
THREE_SIXTEENTHS = 0.1875

C_MAJOR = Scale(Note('C', 4), ScaleType.MAJOR)

# One note on every fourth sixteenth, with silence in between.
PATTERN = [
    Note('C', 4, SIXTEENTH), Rest(THREE_SIXTEENTHS),
    Note('C', 5, SIXTEENTH), Rest(THREE_SIXTEENTHS),
    Note('C', 4, SIXTEENTH), Rest(THREE_SIXTEENTHS),
    Note('G', 4, SIXTEENTH), Rest(THREE_SIXTEENTHS),
]

RUNS = 2


def build_song():
    song = Song(tempo=120)
    track = song.add_track(Track('Pattern'))
    fill_in = Backfill([1], scale=C_MAJOR)
    clip = Clip(notes=PATTERN, length=WHOLE)

    for run in range(RUNS + 1):
        scene = song.add_scene(Scene(f'Run {run}'))
        clip.name = f'Run {run}'
        song.set_clip(scene, track, clip)
        clip = fill_in.generate(clip)

    return song


if __name__ == '__main__':
    ClipTree(OUTPUT_DIRECTORY, build_song()).render()
