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

"""Simple Gifts turns into The House of the Rising Sun, in under two minutes.

Run it from the top folder of this project:

    .venv/bin/python -m demo.gifts_to_sun

This writes an Ableton Live set to ./output/gifts_to_sun/gifts_to_sun.als, with the song in
Arrangement View from start to finish, and in Session View as one scene per part. Set
USE_ABLETON to False to write a directory of MIDI files there instead. demo/blend_base.py
explains the recipe. Edit PROGRESSION or SEED to get a different performance, or turn off
USE_SMOOTHER to hear what it changes.
"""

from fractions import Fraction

from demo.blend_base import BlendMode, BlendPiece, Part
from demo.tunes import (
    RISING_SUN,
    RISING_SUN_CHORDS,
    SIMPLE_GIFTS,
    SIMPLE_GIFTS_CHORDS,
)
from src.analyzers.scale_detector import ScaleDetector
from src.legacy.generators.counterpoint import CounterpointStyle
from src.legacy.generators.stretch import Stretch
from src.renderers.ableton_project import AbletonProject
from src.renderers.clip_tree import ClipTree

USE_ABLETON = True
USE_SMOOTHER = True

OUTPUT_DIRECTORY = './output/gifts_to_sun'

SEED = 7

# Measures of Rising Sun are stretched to last as long as measures of 4/4, so these are the
# lengths of its eighth and quarter notes after stretching.
SUN_EIGHTH = Fraction(1, 6)
SUN_QUARTER = Fraction(1, 3)

PROGRESSION = [
    Part(2, 9, 30, BlendMode.STRONG_BEATS, None, CounterpointStyle.NOTE_AGAINST_NOTE),
    Part(2, 9, 60, BlendMode.CONTOUR, SUN_QUARTER, CounterpointStyle.FLOWING),
    Part(10, 17, 90, BlendMode.SLICES, SUN_EIGHTH, CounterpointStyle.CANON),
]

OPENING_LAST_MEASURE = 9

# Each measure of Rising Sun in 6/8 is stretched to last as long as a measure of 4/4.
TO_FOUR_FOUR = Stretch(Fraction(4, 3))
SUN = TO_FOUR_FOUR.generate(RISING_SUN)
SUN_CHORDS = TO_FOUR_FOUR.generate(RISING_SUN_CHORDS)

GIFTS_SCALE = ScaleDetector().analyze(SIMPLE_GIFTS)
SUN_SCALE = ScaleDetector().analyze(SUN)


def build_song():
    return BlendPiece(
        'Simple Gifts', SIMPLE_GIFTS, SIMPLE_GIFTS_CHORDS,
        'Rising Sun', SUN, SUN_CHORDS,
        PROGRESSION, OPENING_LAST_MEASURE,
        arp_step=SUN_EIGHTH, flowing_step=SUN_EIGHTH,
        seed=SEED, use_smoother=USE_SMOOTHER,
    ).build_song()


def main():
    renderer = AbletonProject if USE_ABLETON else ClipTree
    renderer(OUTPUT_DIRECTORY, build_song()).render()


if __name__ == '__main__':
    main()
