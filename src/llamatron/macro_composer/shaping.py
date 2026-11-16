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

"""Velocity shaped by rhythm and style: how far each note of a part moves from its own velocity by where it falls in the bar.

A part keeps a full default velocity and moves a little from it, never more than REACH, so that a song is never made quiet by
its dynamics. The feel says which places a style leans on: backbeat (rock, pop, funk), four (dance music),
swing (shuffles and jazz) or down (marches, folk, orchestral and chip music). A note off the beat that is held over the next
beat is a push, and is accented.
"""

from fractions import Fraction

from llamatron.macro_composer.notation import DEGREE, DRUM, CHORD, DEFAULT_STEP_SIZE, STEP_SIZE, VELOCITY

REACH = 8
PUSH = 5
LOWEST_SHAPED = 30
HIGHEST_SHAPED = 127
BACKBEAT = 'backbeat'
FOUR = 'four'
SWING = 'swing'
DOWN = 'down'
FEELS = (BACKBEAT, FOUR, SWING, DOWN)
# What a part is to the band, which decides the places it leans on.
PERCUSSION = 'perc'
BASS = 'bass'
COMPING = 'comp'
TUNE = 'tune'
# Tracks whose drums stay as the band's drummer plays them, and the words that mark a bass.
LEFT_ALONE = ('kick', 'snare', 'clap', 'crash', 'tom', 'rim', 'fill', 'foot', 'timp', 'cymbal', 'gong')
BASSES = ('bass', 'tuba', 'left', 'pedal', 'cello', 'sub')
COMPOUND_SIGNATURES = ('6/8', '9/8', '12/8')
COMPOUND_BEAT = Fraction(3, 8)
SIMPLE_BEAT = Fraction(1, 4)
# For each feel and role, the move on: the downbeat, the middle beat, a backbeat, a half beat, anything finer.
ON_DOWNBEAT = 0
ON_MIDDLE = 1
ON_BACKBEAT = 2
ON_HALF = 3
ON_FINER = 4
TABLES = {
    BACKBEAT: {PERCUSSION: (4, 4, 4, -2, -7), BASS: (6, 3, 1, -2, -5), COMPING: (2, 2, 5, -3, -6), TUNE: (5, 2, 0, -3, -5)},
    FOUR: {PERCUSSION: (0, 0, 0, 5, -6), BASS: (4, 2, 2, 3, -5), COMPING: (5, 2, 2, 0, -5), TUNE: (5, 2, 0, -2, -5)},
    SWING: {PERCUSSION: (0, 0, 5, -5, -7), BASS: (4, 2, 1, -5, -6), COMPING: (0, 0, 4, -3, -6), TUNE: (4, 2, 1, -4, -6)},
    DOWN: {PERCUSSION: (6, 3, 0, -4, -7), BASS: (6, 3, 0, -4, -7), COMPING: (6, 3, 0, -4, -7), TUNE: (6, 3, 0, -4, -7)},
}


def is_compound(time_signature):
    return str(time_signature) in COMPOUND_SIGNATURES


def role_of(*, pattern, tracks):
    """What a pattern is to the band, from the tracks that play it, or None for a drum that is left as the drummer plays it."""
    names = ' '.join(tracks).lower()
    if pattern.get(DRUM):
        return None if any(word in names for word in LEFT_ALONE) else PERCUSSION
    if any(word in names for word in BASSES):
        return BASS
    return COMPING if pattern.get(CHORD) and any(pattern[CHORD]) else TUNE


def moves(*, pattern, role, feel, signature, compound):
    """How far each note of a pattern moves, by its step."""
    size = Fraction(str(pattern.get(STEP_SIZE, DEFAULT_STEP_SIZE)))
    beat = COMPOUND_BEAT if compound else SIMPLE_BEAT
    beats = signature / beat
    onsets = [place for place, value in enumerate(pattern[DEGREE]) if value is not None]
    table = TABLES[DOWN if compound else feel][role]
    found = {}
    for place in onsets:
        count = ((place * size) % signature) / beat
        if count.denominator == 1:
            if count == 0:
                move = table[ON_DOWNBEAT]
            elif beats.denominator == 1 and beats % 2 == 0 and count == beats / 2:
                move = table[ON_MIDDLE]
            elif int(count) % 2 == 1:
                move = table[ON_BACKBEAT]
            else:
                move = 0
        else:
            next_beat = (int(count) + 1) * beat + (place * size) // signature * signature
            later = [other * size for other in onsets if other > place]
            pushed = role != PERCUSSION and (not later or later[0] > next_beat) and len(pattern[DEGREE]) * size > next_beat
            finer = (count * 2).denominator != 1 and not (compound and (count * 3).denominator == 1)
            move = PUSH if pushed else table[ON_FINER] if finer else table[ON_HALF]
        found[place] = max(-REACH, min(REACH, move))
    return found


def shaped(*, pattern, role, feel, signature, compound):
    """A pattern's velocities moved by its rhythm."""
    new = list(pattern[VELOCITY])
    for place, move in moves(pattern=pattern, role=role, feel=feel, signature=signature, compound=compound).items():
        if new[place] is not None:
            new[place] = max(LOWEST_SHAPED, min(HIGHEST_SHAPED, new[place] + move))
    return new


def unshaped(*, pattern, role, feel, signature, compound):
    """The velocities a pattern had before it was shaped, where they can be told."""
    old = list(pattern[VELOCITY])
    for place, move in moves(pattern=pattern, role=role, feel=feel, signature=signature, compound=compound).items():
        if old[place] is not None:
            old[place] = old[place] - move
    return old
