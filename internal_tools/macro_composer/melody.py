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

"""A sketch of a tune, made by rule from a style's melody habits, a section's chords and a seed.

The sketch is a starting tune for a person to improve: correct, singable and in the style's scale, never a hook. A section is
cut into lines; the style's plan says which line each is (a letter, so that a line returns), whether it is varied, and whether
the lead or the answering instrument plays it. A line takes one of the style's rhythm cells and walks the style's ladder of
notes by step, landing its long notes on the notes of the chord under them. The same seed gives the same tune.
"""

import random

from notation import ACCIDENTAL, ARRIVAL, DEGREE, ENDING, FLAT, OCTAVE, REST, SHARP, STEPS, STRESS

# The fields of a style's melody habits.
GRID = 'grid'
LINE_BARS = 'line_bars'
LADDER = 'ladder'
RHYTHMS = 'rhythms'
ANSWER_RHYTHMS = 'answer_rhythms'
HOME = 'home'
SPAN = 'span'
# The fields of a plan's line.
LINE = 'line'
VARIED = 'varied'
ANSWER = 'answer'
HIGHER = 'higher'
# The half steps of each scale type's notes above its root.
MAJOR = 'major'
MINOR = 'minor'
HALF_STEPS = {
    MAJOR: (0, 2, 4, 5, 7, 9, 11), MINOR: (0, 2, 3, 5, 7, 8, 10), 'dorian': (0, 2, 3, 5, 7, 9, 10), 'mixolydian': (0, 2, 4, 5, 7, 9, 10),
}
HALF_STEPS_OF_MARK = {SHARP: 1, FLAT: -1}
NOTES_IN_OCTAVE = 12
NOTES_IN_SCALE = 7
OCTAVES_OF_LADDER = (-1, 0, 1)
# A long note lasts at least this share of a bar, and lands on a note of the chord.
LONG_SHARE = 4
# How far a line may move from one note to the next along the ladder, likeliest first, and how much a higher line starts up.
MOVES = (-1, 1, -1, 1, 0, -2, 2)
HIGHER_BY = 2
VARIED_NOTES = 2
THIRD = 2
FIFTH = 4
MAJOR_THIRD = 4
PERFECT_FIFTH = 7


def half_steps_of(*, note, scale_type):
    """A note of the scale, with its sharp or flat, as half steps above the scale's root."""
    return HALF_STEPS[scale_type][(note[DEGREE] - 1) % NOTES_IN_SCALE] + HALF_STEPS_OF_MARK.get(note.get(ACCIDENTAL), 0)


def ladder_of(*, notes, scale_type):
    """The style's notes over three octaves, lowest first, each with its octave and its half steps above the root."""
    rungs = []
    for octave in OCTAVES_OF_LADDER:
        for note in notes:
            rung = dict(note)
            if octave:
                rung[OCTAVE] = octave
            rungs.append((octave * NOTES_IN_OCTAVE + half_steps_of(note=note, scale_type=scale_type), rung))
    return sorted(rungs, key=height_of)


def height_of(rung):
    return rung[0]


def chord_notes(*, chord, scale_type):
    """The pitch classes of the chord on a degree of the scale; a chord with a sharp or flat is a major chord."""
    if ACCIDENTAL in chord:
        root = half_steps_of(note=chord, scale_type=scale_type)
        return {root % NOTES_IN_OCTAVE, (root + MAJOR_THIRD) % NOTES_IN_OCTAVE, (root + PERFECT_FIFTH) % NOTES_IN_OCTAVE}
    steps = HALF_STEPS[scale_type]
    return {steps[(chord[DEGREE] - 1 + more) % NOTES_IN_SCALE] for more in (0, THIRD, FIFTH)}


def nearest_chord_rung(*, ladder, place, wanted):
    """The place on the ladder nearest a place whose note is in the chord, or the place itself when none is near."""
    for away in (0, -1, 1):
        if 0 <= place + away < len(ladder) and ladder[place + away][0] % NOTES_IN_OCTAVE in wanted:
            return place + away
    return place


def line_of(*, rhythm, ladder, start, low, high, chords, grid, scale_type, dice):
    """One line: a rhythm cell with a note for each of its sounds, as the notes a tune's line is written in."""
    place = start
    notes = []
    at = 0
    for cell in rhythm:
        if REST in cell:
            notes.append({REST: cell[REST]})
            at += cell[REST]
            continue
        place = max(low, min(high, place + (dice.choice(MOVES) if notes and any(REST not in note for note in notes) else 0)))
        if cell[STEPS] * LONG_SHARE >= grid:
            place = nearest_chord_rung(ladder=ladder, place=place, wanted=chord_notes(chord=chords[(at // grid) % len(chords)], scale_type=scale_type))
        notes.append({**ladder[place][1], STEPS: cell[STEPS]})
        at += cell[STEPS]
    return notes


def stressed(notes):
    """A line with its longest note marked as the arrival and its last as the ending."""
    sounds = [note for note in notes if REST not in note]
    if len(sounds) > 1:
        longest = max(sounds, key=steps_of)
        if longest is not sounds[-1]:
            longest[STRESS] = ARRIVAL
        sounds[-1][STRESS] = ENDING
    return notes


def steps_of(note):
    return note[STEPS]


def home_place(*, ladder, home):
    """Where on the ladder the home note of the middle octave is."""
    for place, (_, rung) in enumerate(ladder):
        if rung[DEGREE] == home[DEGREE] and rung.get(ACCIDENTAL) == home.get(ACCIDENTAL) and OCTAVE not in rung:
            return place
    return len(ladder) // 2


def silent_line(*, grid, bars):
    return [{REST: grid}] * bars


def sketched(*, habits, plan, chords, scale_type, seed, answers):
    """A section's tune as lines: the lead's, or the answering instrument's when answers is true; a line that isn't its own is silent."""
    grid = habits[GRID]
    ladder = ladder_of(notes=habits[LADDER], scale_type=scale_type)
    home = home_place(ladder=ladder, home=habits[HOME])
    low = max(0, home - habits[SPAN])
    high = min(len(ladder) - 1, home + habits[SPAN])
    known = {}
    lines = []
    for count, entry in enumerate(plan):
        bars_before = count * habits[LINE_BARS]
        under = [chords[(bars_before + bar) % len(chords)] for bar in range(habits[LINE_BARS])]
        if bool(entry.get(ANSWER)) != answers:
            lines.append(silent_line(grid=grid, bars=habits[LINE_BARS]))
            continue
        letter = entry.get(LINE, str(count))
        dice = random.Random('{} {} {} {}'.format(seed, answers, letter, len(lines) if entry.get(VARIED) else ''))
        if letter in known and not entry.get(VARIED):
            lines.append([dict(note) for note in known[letter]])
            continue
        rhythms = habits[ANSWER_RHYTHMS] if answers else habits[RHYTHMS]
        if letter in known:
            kept = [dict(note) for note in known[letter]]
            sounds = [note for note in kept if REST not in note]
            for note in sounds[-VARIED_NOTES:]:
                rung = ladder[max(low, min(high, home + dice.choice(MOVES)))][1]
                for field in (DEGREE, ACCIDENTAL, OCTAVE, STRESS):
                    note.pop(field, None)
                note.update(rung)
            lines.append(stressed(kept))
            continue
        start = home + (HIGHER_BY if entry.get(HIGHER) else 0) + dice.choice((0, 0, 1, -1, 2))
        made = stressed(line_of(rhythm=dice.choice(rhythms), ladder=ladder, start=max(low, min(high, start)), low=low, high=high, chords=under, grid=grid,
                                scale_type=scale_type, dice=dice))
        known[letter] = made
        lines.append([dict(note) for note in made])
    return lines
