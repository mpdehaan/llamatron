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

"""Converting song data written with durations into data written with step sizes and gates.

Before gates, each step of a pattern had its own duration, which was both how long its note
sounded and how far it was to the next step. Now every step of a pattern is the same length, its
step size, and a note's gate says how long it sounds. Each pattern gets the largest step size that
every one of its durations is a whole number of. Each old step becomes a step whose gate is its old
duration, followed by empty steps for the rest of that time, so every note starts and lasts exactly
as before. Tests use this to keep writing patterns as notes and durations, and the demo generator
uses it to write the demos.
"""

import math
from fractions import Fraction as F

from llamatron.composition.file_format import PATTERN_ROWS, GateModifier, PatternSetting, Row
from llamatron.composition.row_descriptions import ROW_DESCRIPTIONS

OLD_DURATION = 'duration'
OLD_DEFAULT_LENGTH = 'default_length'
OLD_GRANULARITY = 'granularity'
OLD_DEFAULT = '1/16'
SONG_STEP_SIZE = F(1, 16)
DOTTED = F(3, 2)
TRIPLET = F(2, 3)
LONGEST_PLAIN = (1, 2, 4)
# Settings a pattern keeps as they are.
KEPT_SETTINGS = (PatternSetting.DRUM, PatternSetting.DIRECTION)


def text_length(length):
    """Return a length as a file writes it: a whole number, or a fraction like 3/16."""
    return length.numerator if length.denominator == 1 else f'{length.numerator}/{length.denominator}'


def is_plain_length(length):
    """Return whether a length is a whole note or a power of two of one, like 1/8 or 2, up to 4."""
    return (length.numerator == 1 and length.denominator & (length.denominator - 1) == 0) or length in LONGEST_PLAIN


def gate_for(duration):
    """Return the gate and Dot row value that make a duration: plain, dotted, a triplet, or else exact."""
    if is_plain_length(duration):
        return duration, None
    if is_plain_length(duration / DOTTED):
        return duration / DOTTED, GateModifier.DOTTED
    if is_plain_length(duration / TRIPLET):
        return duration / TRIPLET, GateModifier.TRIPLET
    return duration, None


def common_step(durations):
    """Return the largest length that every duration is a whole number of."""
    step = durations[0]
    for duration in durations[1:]:
        step = F(math.gcd(step.numerator * duration.denominator, duration.numerator * step.denominator), step.denominator * duration.denominator)
    return step


def to_gates(*, old, default=F(1, 16)):
    """Return an old pattern, whose steps each had a duration, as one with a fixed step size and gates.

    Data that's wrong is passed through as it is, so that the song's own checks refuse it: a
    pattern with no steps stays without any, and a row that's the wrong length stays that length.
    A Gate or Dot value given for a step is kept, in place of the one its duration would give.
    """
    steps = old[PatternSetting.STEPS]
    if not steps:
        return {key: value for key, value in old.items() if key != OLD_DURATION}
    durations = [F(str(value)) if value is not None else default for value in (old.get(OLD_DURATION) or [None] * steps)]
    step = common_step(durations)
    misfits = {row: old[row] for row in PATTERN_ROWS if isinstance(old.get(row), list) and len(old[row]) != steps}
    rows = [row for row in PATTERN_ROWS if row in old and row not in (Row.GATE, Row.DOT) and row not in misfits]
    degrees = old.get(Row.DEGREE) or [None] * steps
    new_rows = {row: [] for row in [*rows, Row.GATE, Row.DOT]}
    for place, duration in enumerate(durations):
        # A rest plays nothing, so only a step with a note needs a gate.
        plays = degrees[place] is not None
        gate, dot = gate_for(duration) if plays and duration != step else (None, None)
        gate = text_length(gate) if gate is not None else None
        gate, dot = _given(old=old, row=Row.GATE, place=place, worked_out=gate), _given(old=old, row=Row.DOT, place=place, worked_out=dot)
        for row in rows:
            new_rows[row].append(old[row][place])
        new_rows[Row.GATE].append(gate)
        new_rows[Row.DOT].append(dot)
        for _ in range(int(duration / step) - 1):
            for row in rows:
                new_rows[row].append(_filler_value(row=row, value=old[row][place]))
            new_rows[Row.GATE].append(None)
            new_rows[Row.DOT].append(None)
    new = {PatternSetting.STEPS: len(new_rows[Row.GATE])}
    if step != SONG_STEP_SIZE:
        new[PatternSetting.STEP_SIZE] = text_length(step)
    for setting in KEPT_SETTINGS:
        if setting in old:
            new[setting] = old[setting]
    for row, values in new_rows.items():
        if any(value is not None and value is not False for value in values):
            new[row] = values
    new.update(misfits)
    return new


def _filler_value(*, row, value):
    """Return what a step added to fill out an old step's duration holds on a row: nothing, except that a tie covers the whole duration."""
    if row == Row.TIE:
        return value
    return ROW_DESCRIPTIONS[row].blank()


def _given(*, old, row, place, worked_out):
    """Return a step's value on a row as the old pattern gives it, or else the value worked out for it."""
    values = old.get(row)
    if isinstance(values, list) and len(values) == old[PatternSetting.STEPS] and values[place] is not None:
        return values[place]
    return worked_out


def song_to_gates(data):
    """Return a whole song's data with every pattern in gates, and the old song settings for lengths gone."""
    data = dict(data)
    default = F(str(data.pop(OLD_DEFAULT_LENGTH, OLD_DEFAULT)))
    data.pop(OLD_GRANULARITY, None)
    data['patterns'] = {name: to_gates(old=pattern, default=default) for name, pattern in (data.get('patterns') or {}).items()}
    return data
