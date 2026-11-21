# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Files saved before 1.0.30 numbered octaves as Live labels them, two lower than the numbering from C0 written since."""

SINCE = '1.0.30'
# How far Live's octave labels lie below the numbering from C0.
OFFSET = 2
# Where such a file held its octaves: the set's two defaults, and each pattern's octave row.
DEFAULT_OCTAVE = 'default_octave'
DEFAULT_DRUM_OCTAVE = 'default_drum_octave'
PATTERNS = 'patterns'
OCTAVE_ROW = 'octave'


def is_before(data):
    """A file with no version gives no sign of its numbering, and is taken as numbered from C0."""
    return False


def is_whole_number(value):
    return isinstance(value, int) and not isinstance(value, bool)


def moved(*, data, conversion):
    """Move every whole number of an octave up by OFFSET; anything else is left for the reader to refuse."""
    moved_data = dict(data)
    for name in (DEFAULT_OCTAVE, DEFAULT_DRUM_OCTAVE):
        if is_whole_number(moved_data.get(name)):
            moved_data[name] = moved_data[name] + OFFSET
    if isinstance(moved_data.get(PATTERNS), dict):
        moved_data[PATTERNS] = {name: _pattern_moved(pattern) for name, pattern in moved_data[PATTERNS].items()}
    return moved_data


def _pattern_moved(pattern):
    if not isinstance(pattern, dict) or not isinstance(pattern.get(OCTAVE_ROW), list):
        return pattern
    return {**pattern, OCTAVE_ROW: [octave + OFFSET if is_whole_number(octave) else octave for octave in pattern[OCTAVE_ROW]]}
