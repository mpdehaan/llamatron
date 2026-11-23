# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Edits of one line of a tune by hand: a line is a list of notes and rests, each so many steps long, as a melody engine writes one.

A step of the line is either inside a note or inside a rest. A note is moved up and down the scale, made longer into the
rest after it and shorter, taken out, and put in where a rest is. Every edit returns a new line as long as the one given,
and a line an edit cannot change is returned as it was.
"""

import copy

from llamatron.music_theory.composing import notation

NOTES_IN_SCALE = 7
# How far from the scale's first note in its own octave a note may be moved, in notes of the scale.
LOWEST_PLACE = -NOTES_IN_SCALE
HIGHEST_PLACE = 3 * NOTES_IN_SCALE - 1
FIRST_DEGREE = 1
ONE_STEP = 1


def length_of(note):
    """How many steps a note or a rest lasts."""
    return note[notation.REST] if notation.REST in note else note[notation.STEPS]


def steps_of(line):
    return sum(length_of(note) for note in line)


def is_rest(note):
    return notation.REST in note


def found(*, line, step):
    """Which note or rest of a line a step is inside, and the step the note or rest starts on."""
    at = 0
    for index, note in enumerate(line):
        if step < at + length_of(note):
            return index, at
        at += length_of(note)
    raise IndexError(step)


def place_of(note):
    """Where a note is in the scale: 0 the scale's first note in the line's own octave, 7 the same note an octave up."""
    return note[notation.DEGREE] - FIRST_DEGREE + NOTES_IN_SCALE * note.get(notation.OCTAVE, 0)


def at_place(*, note, place):
    """A note moved to a place of the scale, with no sharp or flat of its own."""
    octave, degree = divmod(place, NOTES_IN_SCALE)
    moved = {field: value for field, value in note.items() if field not in (notation.DEGREE, notation.OCTAVE, notation.ACCIDENTAL)}
    moved[notation.DEGREE] = degree + FIRST_DEGREE
    if octave:
        moved[notation.OCTAVE] = octave
    return moved


def tidied(line):
    """A line with its rests that touch made one and nothing of no length."""
    result = []
    for note in line:
        if length_of(note) <= 0:
            continue
        if is_rest(note) and result and is_rest(result[-1]):
            result[-1] = {notation.REST: result[-1][notation.REST] + note[notation.REST]}
        else:
            result.append(copy.deepcopy(note))
    return result


def moved(*, line, step, by):
    """A line with the note a step is inside moved so many notes of the scale up, or down, held to the places a note may be."""
    index, _ = found(line=line, step=step)
    if is_rest(line[index]):
        return tidied(line)
    place = max(min(place_of(line[index]) + by, HIGHEST_PLACE), LOWEST_PLACE)
    return tidied([*line[:index], at_place(note=line[index], place=place), *line[index + 1:]])


def stretched(*, line, step, by):
    """A line with the note a step is inside one step longer, into the rest after it, or one step shorter, leaving a rest."""
    index, _ = found(line=line, step=step)
    note = line[index]
    if is_rest(note):
        return tidied(line)
    after = line[index + 1] if index + 1 < len(line) else None
    if by > 0:
        if after is None or not is_rest(after):
            return tidied(line)
        return tidied([*line[:index], {**note, notation.STEPS: note[notation.STEPS] + ONE_STEP}, {notation.REST: after[notation.REST] - ONE_STEP}, *line[index + 2:]])
    if note[notation.STEPS] <= ONE_STEP:
        return tidied(line)
    return tidied([*line[:index], {**note, notation.STEPS: note[notation.STEPS] - ONE_STEP}, {notation.REST: ONE_STEP}, *line[index + 1:]])


def nearest_place(*, line, index):
    """The place of the note before a place in the line, else of the note after, else the scale's first note."""
    before = [note for note in line[:index] if not is_rest(note)]
    after = [note for note in line[index:] if not is_rest(note)]
    if before:
        return place_of(before[-1])
    return place_of(after[0]) if after else 0


def toggled(*, line, step):
    """A line with the note a step is inside taken out, or, where the step is inside a rest, a note one step long put in on the step,
    at the place of the note before it."""
    index, start = found(line=line, step=step)
    note = line[index]
    if not is_rest(note):
        return tidied([*line[:index], {notation.REST: note[notation.STEPS]}, *line[index + 1:]])
    new = at_place(note={notation.STEPS: ONE_STEP}, place=nearest_place(line=line, index=index))
    return tidied([*line[:index], {notation.REST: step - start}, new, {notation.REST: note[notation.REST] - (step - start) - ONE_STEP}, *line[index + 1:]])
