# llamatron: a music program
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

"""A riff: a song's second hook, two bars of single notes that a rhythm player repeats exactly while the chords move the riff under the song.

A riff is written over the home chord, in eighths, as one line of notes and rests (line_edits.py): the first bar states
the figure, starting on the chord's root, and the second says the figure again with another ending, as a riff answers
itself. The Progression generator moves the line with each chord, as it moves a bass figure. A song asks for a riff
with who plays it, which kinds of section it is played in, and either a take, a number the notes are drawn from, or the
notes themselves written by hand.
"""

import random

from llamatron.macro_composer.notation import DEGREE, OCTAVE, REST, STEPS

# What a song says of its riff.
RIFF = 'riff'
RIFF_ROLES = 'roles'
RIFF_KINDS = 'kinds'
RIFF_TAKE = 'take'
RIFF_LINE = 'line'
FIRST_TAKE = 0
RIFF_BARS = 2
RIFF_SEED = 'riff {} {}'
# The notes a riff is drawn from, each a degree and an octave from the player's own, with how often each is drawn: the root most, then the note under it.
HOME = (1, 0)
LADDER = ((HOME, 4), ((7, -1), 3), ((3, 0), 2), ((4, 0), 2), ((5, 0), 2), ((5, -1), 1), ((1, 1), 1))
# How long a note may last, in eighths, the shorter the likelier, and how often a place after the first is a rest.
LENGTHS = (1, 1, 2, 2, 3)
REST_SHARE = 0.2
LONGEST_REST = 2
# How many notes at the end of the second bar are drawn again, as the riff's answer.
ANSWER_NOTES = 2
TRIES = 20


def note_at(*, place, steps):
    degree, octave = place
    return {DEGREE: degree, STEPS: steps, **({OCTAVE: octave} if octave else {})}


def drawn_place(*, dice, before):
    """A note of the ladder, by its share, and never the note just played a third time running."""
    places = [place for place, share in LADDER for _ in range(share) if before[-2:] != [place, place]]
    return dice.choice(places)


def riff_bar(*, dice, eighths):
    """One bar of a riff: notes and a few rests filling the bar, the first note the root."""
    bar = []
    places = []
    room = eighths
    while room:
        length = min(dice.choice(LENGTHS), room)
        if bar and length <= LONGEST_REST and dice.random() < REST_SHARE and REST not in bar[-1]:
            bar.append({REST: length})
        else:
            place = HOME if not bar else drawn_place(dice=dice, before=places)
            places.append(place)
            bar.append(note_at(place=place, steps=length))
        room -= length
    return bar


def answered(*, bar, dice):
    """A bar said again with its last notes drawn anew, so that the riff's second bar answers its first."""
    sounding = [count for count, note in enumerate(bar) if REST not in note]
    again = [dict(note) for note in bar]
    for _ in range(TRIES):
        for count in sounding[1:][-ANSWER_NOTES:]:
            again[count] = note_at(place=drawn_place(dice=dice, before=[]), steps=bar[count][STEPS])
        if again != bar:
            break
    return again


def riff_line(*, seed, take, eighths):
    """A song's riff as one line of two bars, drawn from the song's seed and the riff's take."""
    dice = random.Random(RIFF_SEED.format(seed, take))
    first = riff_bar(dice=dice, eighths=eighths)
    return first + answered(bar=first, dice=dice)
