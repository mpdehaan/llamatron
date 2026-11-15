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

"""The MacroComposer's parts: a tune as a list of notes and a drum's bar as a list of hits, each turned into a pattern's rows and back.

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

A drum's bar is a list with one of loud, soft and none for every step.
"""

from collections import Counter
from llamatron.strings.errors import ERR_NOT_A_BAR, ERR_NOT_A_TUNE

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
LOWEST_VELOCITY = 1
HIGHEST_VELOCITY = 127
# A line that has run this many bars without a rest ends at the next bar line.
LONGEST_LINE_IN_BARS = 2

# The fields of a drum's bar and the words for its hits.
HITS = 'hits'
LOUD = 'loud'
SOFT = 'soft'
NONE = 'none'
NOTE_NAMES = ['C', 'C', 'D', 'D', 'E', 'F', 'F', 'G', 'G', 'A', 'A', 'B']
SHARP_MARK = '#'
SHARPS = [None, SHARP_MARK, None, SHARP_MARK, None, None, SHARP_MARK, None, SHARP_MARK, None, SHARP_MARK, None]
NOTES_IN_OCTAVE = 12
# The General MIDI drums a bar may name.
KIT = {
    'kick': 36, 'rim': 37, 'snare': 38, 'clap': 39, 'hat': 42, 'hat by foot': 44, 'tom low': 45, 'open': 46, 'tom mid': 47, 'crash': 49, 'tom high': 50, 'ride': 51, 'splash': 55, 'bell': 53, 'tamb': 54,
    'cowbell': 56, 'conga high': 63, 'conga low': 64, 'timbale': 65, 'maracas': 70, 'claves': 75, 'woodblock': 76, 'shaker': 82,
}
NAME_OF_DRUM = {number: name for name, number in KIT.items()}



class NotWritable(ValueError):
    """A pattern holds something the parts have no way to say."""


def clamped(velocity):
    return max(LOWEST_VELOCITY, min(HIGHEST_VELOCITY, velocity))


def kept_rows(rows):
    """Only the rows that say anything, as a set file keeps them."""
    return {name: values for name, values in rows.items() if any(value not in (None, False) for value in values)}


def tune_rows(*, lines, octave, velocity, step_size):
    """A tune's lines as a pattern."""
    rows = {name: [] for name in (DEGREE, ACCIDENTAL, OCTAVE, TIE, VELOCITY) + OTHER_ROWS}
    for line in lines:
        for note in line:
            rest = REST in note
            length = note[REST] if rest else note[STEPS]
            held = [None] * (length - 1)
            loud = None if rest else note.get(VELOCITY, clamped(velocity + STRESSES.get(note.get(STRESS), 0) + note.get(LOUDER, 0)))
            rows[DEGREE] += [None if rest else note[DEGREE]] + held
            rows[ACCIDENTAL] += [ACCIDENTAL_MARKS.get(note.get(ACCIDENTAL))] + held
            rows[OCTAVE] += [None if rest else octave + note.get(OCTAVE, 0)] + held
            rows[TIE] += [False] + [not rest] * (length - 1)
            rows[VELOCITY] += [loud] + held
            for name in OTHER_ROWS:
                rows[name] += [note.get(name)] + held
    pattern = {STEPS: len(rows[DEGREE]), STEP_SIZE: step_size}
    pattern.update(kept_rows(rows))
    return pattern


def commonest(values):
    return Counter(value for value in values if value is not None).most_common(1)[0][0]


def plainest_velocity(loud):
    """The velocity a tune is written against: the one from which the most notes are plain or a stress, the commonest of those."""
    counts = Counter(value for value in loud if value is not None)
    said = {base: sum(count for value, count in counts.items() if value == base or value - base in STRESS_OF_MOVE) for base in counts}
    return max(counts, key=lambda base: (said[base], counts[base]))


def tune_lines(*, pattern, bar, velocities=None):
    """A pattern as a tune's lines, with the octave and velocity the notes are written against; velocities stands in for the pattern's own."""
    steps = pattern[STEPS]
    degree = pattern[DEGREE]
    empty = [None] * steps
    accidental = pattern.get(ACCIDENTAL) or empty
    octaves = pattern.get(OCTAVE) or empty
    tie = pattern.get(TIE) or [False] * steps
    loud = velocities or pattern.get(VELOCITY) or empty
    if not any(value is not None for value in degree) or not any(value is not None for value in loud):
        raise NotWritable(ERR_NOT_A_TUNE)
    octave = commonest(octaves)
    velocity = plainest_velocity(loud)
    lines = [[]]
    started = 0
    place = 0
    while place < steps:
        end = place + 1
        if degree[place] is None:
            while end < steps and degree[end] is None and not tie[end]:
                end += 1
            lines[-1].append({REST: end - place})
            if end < steps:
                lines.append([])
                started = end
        else:
            if lines[-1] and place % bar == 0 and place - started >= LONGEST_LINE_IN_BARS * bar:
                lines.append([])
                started = place
            while end < steps and degree[end] is None and tie[end]:
                end += 1
            note = {DEGREE: degree[place], STEPS: end - place}
            if octaves[place] != octave:
                note[OCTAVE] = octaves[place] - octave
            if accidental[place]:
                note[ACCIDENTAL] = ACCIDENTAL_WORDS[accidental[place]]
            move = loud[place] - velocity
            if move in STRESS_OF_MOVE:
                note[STRESS] = STRESS_OF_MOVE[move]
            elif move:
                note[VELOCITY] = loud[place]
            for name in OTHER_ROWS:
                if pattern.get(name) and pattern[name][place] is not None:
                    note[name] = pattern[name][place]
            lines[-1].append(note)
        place = end
    return [line for line in lines if line], octave, velocity


def drum_rows(*, drum, hits, loud, soft, step_size):
    """A drum's bar as a pattern; drum is a name of the kit or a General MIDI note number."""
    number = KIT.get(drum, drum)
    name = NOTE_NAMES[number % NOTES_IN_OCTAVE]
    sharp = SHARPS[number % NOTES_IN_OCTAVE]
    on = [hit != NONE for hit in hits]
    pattern = {STEPS: len(hits), DRUM: True, STEP_SIZE: step_size, DEGREE: [name if hit else None for hit in on],
               OCTAVE: [number // NOTES_IN_OCTAVE if hit else None for hit in on],
               VELOCITY: [loud if hit == LOUD else soft if hit == SOFT else None for hit in hits]}
    if sharp:
        pattern[ACCIDENTAL] = [sharp if hit else None for hit in on]
    return pattern


def drum_hits(*, pattern, velocities=None):
    """A drum pattern as its drum, its hits and its loud and soft velocities."""
    steps = pattern[STEPS]
    degree = pattern[DEGREE]
    empty = [None] * steps
    accidental = pattern.get(ACCIDENTAL) or empty
    octaves = pattern.get(OCTAVE) or empty
    loud = velocities or pattern.get(VELOCITY) or empty
    numbers = {NOTE_NAMES.index(degree[place]) + (1 if accidental[place] == SHARP_MARK else 0) + octaves[place] * NOTES_IN_OCTAVE
               for place in range(steps) if degree[place] is not None}
    levels = sorted({value for value in loud if value is not None}, reverse=True)
    if len(numbers) != 1 or not 1 <= len(levels) <= 2:
        raise NotWritable(ERR_NOT_A_BAR)
    number = numbers.pop()
    hits = [NONE if degree[place] is None else LOUD if loud[place] == levels[0] else SOFT for place in range(steps)]
    return NAME_OF_DRUM.get(number, number), hits, levels[0], levels[-1]
