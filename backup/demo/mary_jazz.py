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

"""A jazz song made from Mary Had a Little Lamb and every generator in the project.

Run it from the top folder of this project:

    .venv/bin/python -m demo.mary_jazz

This writes an Ableton Live set to ./output/mary_jazz/mary_jazz.als. Set USE_ABLETON to
False to write a directory of MIDI files there instead. There's one scene for each section:

    Tune          The melody alone, then with chords, then with arpeggiated chords.
    Going Out     Each generator in STACK builds on the clip before it. The last one
                  moves the song into A minor, which is where the back half stays.
    Coming Back   Each earlier version in A minor, with one small random mutation.
    Tune Again    Plain Mary in A minor, to finish with the tune we started from.

Only the melody is ever changed, and Accompany chooses new chords to fit each version.
Change SEED to get a different performance, or edit the lists to change the song.
"""

import random
from itertools import accumulate

from demo.mary import MELODY
from llamatron.legacy.generators.accompany import Accompany
from llamatron.generators.arp import Arp, ChordOrder
from llamatron.legacy.generators.backfill import Backfill
from llamatron.legacy.generators.duration_change import DurationChange
from llamatron.legacy.generators.mix_up import MixUp
from llamatron.legacy.generators.mix_up2 import MixUp2
from llamatron.generators.repeater import Repeater
from llamatron.legacy.generators.reverse import Reverse
from llamatron.generators.auto_ratchet import AutoRatchet
from llamatron.legacy.generators.transpose import Transpose
from llamatron.legacy.generators.transpose_scale import TransposeScale
from llamatron.note import Note
from llamatron.renderers.ableton_project import AbletonProject
from llamatron.renderers.clip_tree import ClipTree
from llamatron.scale import Scale, ScaleType
from llamatron.song import Clip, Scene, Song, Track

USE_ABLETON = True

OUTPUT_DIRECTORY = './output/mary_jazz'

SEED = 7
EIGHTH = 0.125

C_MAJOR = Scale(Note('C', 4), ScaleType.MAJOR)
A_MINOR = Scale(Note('A', 3), ScaleType.MINOR)

MARY = Clip(notes=[note for section in MELODY for note in section], scale=C_MAJOR)

ACCOMPANY = Accompany()
ARPEGGIATE = Arp(EIGHTH, ChordOrder.UP_DOWN)
TO_MINOR = TransposeScale(input_scale=C_MAJOR, output_scale=A_MINOR)

# Each of these builds on the one before, so the song gets stranger as it goes.
STACK = [
    DurationChange([0.5, 1]),
    MixUp2([0.25], seed=SEED),
    MixUp([0.25], seed=SEED),
    Backfill([1]),
    Transpose(scale_notes=2),
    AutoRatchet([1, 1, 1, 2]),
    Reverse(),
    Repeater(2),
    TO_MINOR,
]

# One of these is picked at random for each scene on the way back.
SMALL_MUTATIONS = [
    MixUp2([0.25], seed=SEED),
    AutoRatchet([1, 1, 1, 2]),
    DurationChange([1, 0.5]),
    Transpose(scale_notes=1),
]


def build_song():
    song = Song(tempo=120)
    melody_track = song.add_track(Track('Melody'))
    chord_track = song.add_track(Track('Chords'))

    def play(name, melody, chords=None):
        scene = song.add_scene(Scene(name))
        song.set_clip(scene, melody_track, melody.renamed(name))
        if chords is not None:
            song.set_clip(scene, chord_track, chords.renamed(name))

    mary_chords = ACCOMPANY.generate(MARY)
    play('Tune Alone', MARY)
    play('Tune With Chords', MARY, mary_chords)
    play('Tune With Arp', MARY, ARPEGGIATE.generate(mary_chords))

    versions = list(accumulate(STACK, lambda clip, step: step.generate(clip), initial=MARY))
    for number, melody in enumerate(versions[1:], start=1):
        play(f'Going Out {number}', melody, ACCOMPANY.generate(melody))

    chooser = random.Random(SEED)
    for number, version in reversed(list(enumerate(versions[:-1]))):
        melody = chooser.choice(SMALL_MUTATIONS).generate(TO_MINOR.generate(version))
        play(f'Coming Back {number}', melody, ACCOMPANY.generate(melody))

    minor_mary = TO_MINOR.generate(MARY)
    play('Tune Again', minor_mary, ACCOMPANY.generate(minor_mary))
    return song


def main():
    renderer = AbletonProject if USE_ABLETON else ClipTree
    renderer(OUTPUT_DIRECTORY, build_song()).render()


if __name__ == '__main__':
    main()
