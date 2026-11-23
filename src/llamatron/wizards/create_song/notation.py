# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The song wizard's parts: a tune as a list of notes and a drum's bar as a list of hits, each turned into a pattern's rows and back.

A tune is sung lines, each a list of notes, each note a mapping that says only what is not plain:

    {degree: 5, steps: 2}                    the scale's fifth note for two steps
    {rest: 2}                                silence for two steps
    {degree: 1, steps: 4, octave: 1}         an octave above the part's octave; -1 is an octave below
    {degree: 7, steps: 1, accidental: flat}  flattened; sharp sharpens
    {degree: 6, steps: 1, stress: pickup}    soft, a note that leads into a bar
    {degree: 5, steps: 2, stress: arrival}   accented, the stressed note a line arrives on
    {degree: 1, steps: 2, stress: peak}      the strongest accent, a line's highest or most stressed note
    {degree: 3, steps: 2, stress: ending}    eased, a line's last note
    {degree: 5, steps: 2, velocity: 96}      a velocity written out, where no stress says it
    {degree: 1, steps: 1, level: ghost}      at one of the part's named levels: ghost, soft or accent

A drum's bar is a list with one of accent, loud, soft, ghost and none for every step; loud is the drum's normal stroke.
"""

from fractions import Fraction

from llamatron.music_theory.fundamentals import intervals
from llamatron.user_strings import errors
from llamatron.wizards.create_song import wizard_names

# The rows of a pattern, as a set file names them.
STEPS = 'steps'
STEP_SIZE = 'step_size'
DRUM = 'drum'
DEGREE = 'degree'
ACCIDENTAL = 'accidental'
OCTAVE = 'octave'
TIE = 'tie'
VELOCITY = 'velocity'
CHORD = 'chord'
DEFAULT_STEP_SIZE = '1/16'
# The rows a note can say besides its own, each by the row's name.
OTHER_ROWS = (CHORD, 'gate', 'dot', 'probability')

# The fields of a tune and of a note.
LINES = 'lines'
STEP = 'step'
REST = 'rest'
STRESS = 'stress'
# How much louder or softer than its part a note is, where an engine says.
LOUDER = 'louder'
SHARP = 'sharp'
FLAT = 'flat'
ACCIDENTAL_MARKS = {SHARP: '#', FLAT: 'b'}
ACCIDENTAL_WORDS = {mark: word for word, mark in ACCIDENTAL_MARKS.items()}
PICKUP = 'pickup'
ARRIVAL = 'arrival'
PEAK = 'peak'
ENDING = 'ending'
# How far each stress moves a note from the part's velocity.
STRESSES = {PEAK: 12, ARRIVAL: 8, PICKUP: -8, ENDING: -4}
STRESS_OF_MOVE = {move: stress for stress, move in STRESSES.items()}
# A line that has run this many bars without a rest ends at the next bar line.
LONGEST_LINE_IN_BARS = 2

# The fields of a drum's bar and the words for its hits.
HITS = 'hits'
LOUD = 'loud'
NONE = 'none'
# The named level a note of a tune is played at, where the note says.
LEVEL = 'level'
NOTE_NAMES = ['C', 'C', 'D', 'D', 'E', 'F', 'F', 'G', 'G', 'A', 'A', 'B']
SHARP_MARK = '#'
SHARPS = [None, SHARP_MARK, None, SHARP_MARK, None, None, SHARP_MARK, None, SHARP_MARK, None, SHARP_MARK, None]
NAME_OF_DRUM = {number: name for name, number in wizard_names.NOTATION_KIT.items()}


class NotWritable(ValueError):
    """A pattern holds something the parts have no way to say."""


def clamped(velocity):
    return max(wizard_names.LOWEST_VELOCITY, min(wizard_names.HIGHEST_VELOCITY, velocity))


def kept_rows(rows):
    """Only the rows that say anything, as a set file keeps them."""
    return {name: values for name, values in rows.items() if says_anything(values)}


def stress_moves(*, velocity, levels):
    """Return how far each stress moves a note from the part's velocity: the usual distances, or where a part says its levels,
    the distances to its accent and its soft note, a lesser stress going two thirds or half the way."""
    if not levels:
        return STRESSES
    up = levels.get(wizard_names.ACCENT, velocity + STRESSES[PEAK]) - velocity
    down = levels.get(wizard_names.SOFT, velocity + STRESSES[PICKUP]) - velocity
    arrival = round(Fraction(up * STRESSES[ARRIVAL], STRESSES[PEAK]))
    ending = round(Fraction(down * STRESSES[ENDING], STRESSES[PICKUP]))
    return {PEAK: up, ARRIVAL: arrival, PICKUP: down, ENDING: ending}


def louder_by(*, louder, moves):
    """An engine's louder or softer, in the usual distances, as far as the part's own distances make it."""
    if not louder:
        return 0
    return round(Fraction(louder * moves[PEAK], STRESSES[PEAK])) if louder > 0 else round(Fraction(louder * moves[PICKUP], STRESSES[PICKUP]))


def tune_rows(*, lines, octave, velocity, step_size, levels=None):
    """Return a tune's lines as a pattern; levels are the part's accent, soft and ghost velocities where the part says them."""
    moves = stress_moves(velocity=velocity, levels=levels)
    given = levels or {}
    named = {
        wizard_names.ACCENT: velocity + moves[PEAK],
        wizard_names.SOFT: velocity + moves[PICKUP],
        wizard_names.GHOST: given.get(wizard_names.GHOST, velocity + moves[PICKUP]),
    }
    rows = {name: [] for name in (DEGREE, ACCIDENTAL, OCTAVE, TIE, VELOCITY) + OTHER_ROWS}
    for line in lines:
        for note in line:
            loud = _note_velocity(note=note, velocity=velocity, moves=moves, named=named)
            _add_note_rows(rows=rows, note=note, octave=octave, loud=loud)
    pattern = {STEPS: len(rows[DEGREE]), STEP_SIZE: step_size}
    pattern.update(kept_rows(rows))
    return pattern


def _note_velocity(*, note, velocity, moves, named):
    """Return a note's velocity: its own, or its level's moved by its stress and by how much louder it is; None for a rest."""
    if REST in note:
        return None
    at = named.get(note.get(LEVEL), velocity)
    stressed = at + moves.get(note.get(STRESS), 0) + louder_by(louder=note.get(LOUDER, 0), moves=moves)
    return note.get(VELOCITY, clamped(stressed))


def _add_note_rows(*, rows, note, octave, loud):
    """Add a note or a rest to a pattern's rows, a step for each step it lasts, the steps after its first tied for a note."""
    rest = REST in note
    if rest:
        length = note[REST]
    else:
        length = note[STEPS]
    held = [None] * (length - 1)
    degree = None
    octave_of_note = None
    if not rest:
        degree = note[DEGREE]
        octave_of_note = octave + note.get(OCTAVE, 0)
    rows[DEGREE] += [degree] + held
    rows[ACCIDENTAL] += [ACCIDENTAL_MARKS.get(note.get(ACCIDENTAL))] + held
    rows[OCTAVE] += [octave_of_note] + held
    rows[TIE] += [False] + [not rest] * (length - 1)
    rows[VELOCITY] += [loud] + held
    for name in OTHER_ROWS:
        rows[name] += [note.get(name)] + held


def drum_rows(*, drum, hits, loud, soft, step_size, accent=None, ghost=None):
    """Return a drum's bar as a pattern; drum is a name of the kit or a General MIDI note number. An accent with no velocity
    of its own is a loud stroke, and a ghost note with none a soft one."""
    velocities = {LOUD: loud, wizard_names.SOFT: soft, wizard_names.ACCENT: loud, wizard_names.GHOST: soft}
    if accent is not None:
        velocities[wizard_names.ACCENT] = accent
    if ghost is not None:
        velocities[wizard_names.GHOST] = ghost
    number = wizard_names.NOTATION_KIT.get(drum, drum)
    sharp = SHARPS[number % intervals.HALF_STEPS_PER_OCTAVE]
    on = [hit != NONE for hit in hits]
    pattern = {STEPS: len(hits), DRUM: True, STEP_SIZE: step_size}
    pattern[DEGREE] = _where_on(on=on, value=NOTE_NAMES[number % intervals.HALF_STEPS_PER_OCTAVE])
    pattern[OCTAVE] = _where_on(on=on, value=number // intervals.HALF_STEPS_PER_OCTAVE)
    pattern[VELOCITY] = [velocities.get(hit) for hit in hits]
    if sharp:
        pattern[ACCIDENTAL] = _where_on(on=on, value=sharp)
    return pattern


def _where_on(*, on, value):
    """Return a row holding a value on every step that is on and nothing elsewhere."""
    row = []
    for hit in on:
        if hit:
            row.append(value)
        else:
            row.append(None)
    return row


def drum_hits(*, pattern, velocities=None):
    """Return a drum pattern as its drum, its hits and its loud and soft velocities."""
    steps = pattern[STEPS]
    degree = pattern[DEGREE]
    empty = [None] * steps
    accidental = pattern.get(ACCIDENTAL) or empty
    octaves = pattern.get(OCTAVE) or empty
    loud = velocities or pattern.get(VELOCITY) or empty
    numbers = set()
    for place in range(steps):
        if degree[place] is not None:
            numbers.add(_note_number(name=degree[place], accidental=accidental[place], octave=octaves[place]))
    present = {value for value in loud if value is not None}
    levels = sorted(present, reverse=True)
    if len(numbers) != 1 or not 1 <= len(levels) <= 2:
        raise NotWritable(errors.ERR_NOT_A_BAR)
    number = numbers.pop()
    hits = []
    for place in range(steps):
        hits.append(_hit_at(degree=degree[place], loud=loud[place], loudest=levels[0]))
    return NAME_OF_DRUM.get(number, number), hits, levels[0], levels[-1]


def _note_number(*, name, accidental, octave):
    """Return the MIDI note number of a note's name, its sharp and its octave."""
    number = NOTE_NAMES.index(name) + octave * intervals.HALF_STEPS_PER_OCTAVE
    if accidental == SHARP_MARK:
        number += 1
    return number


def _hit_at(*, degree, loud, loudest):
    """Return a step's hit: none where nothing plays, loud at the loudest velocity, and soft otherwise."""
    if degree is None:
        return NONE
    if loud == loudest:
        return LOUD
    return wizard_names.SOFT


def says_anything(values):
    """Return whether a row holds any value but nothing and off."""
    for value in values:
        if value not in (None, False):
            return True
    return False


def copied_line(line):
    """Return a line of notes with each note a copy of its own, to change without changing the line it came from."""
    return [dict(note) for note in line]


def is_silent(lines):
    """Return whether lines hold nothing but rests."""
    for line in lines:
        if not is_rests(line):
            return False
    return True


def is_rests(line):
    """Return whether a line holds nothing but rests."""
    for note in line:
        if REST not in note:
            return False
    return True


def without_fields(*, entry, fields):
    """Return an entry, a note or a section, without the fields named."""
    return {field: value for field, value in entry.items() if field not in fields}


def with_fields_only(*, entry, fields):
    """Return only the fields named of an entry, a note or a section."""
    return {field: value for field, value in entry.items() if field in fields}
