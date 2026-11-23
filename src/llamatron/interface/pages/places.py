# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Places: where a page is, as a value, so that a presenter says where to go without naming the tracker's page that shows it
(the declarative pages' design). The tracker's site map (interface/tracker/site_map.py) knows which page shows each place.

A generator's part pages come first: each place names its part, the generator by its name, where it is built in, if it is a
clip's or a track's own (a BuiltInPlace), and for some parts the section the generator is of and the row of steps.
"""

from dataclasses import dataclass

# The parts of a generator a page of its own edits: its offsets, a row of its steps, its progression's chords, its guitar bar,
# and its Bypass When statements.
OFFSETS = 'offsets'
STEP_ROW = 'step row'
CHORDS = 'chords'
GUITAR_BAR = 'guitar bar'
BYPASS_WHEN = 'bypass when'


@dataclass(frozen=True, slots=True, kw_only=True)
class GeneratorPartPlace:
    """The page of one part of a generator: the part, the generator's name, where it is built in or None for one of the set's,
    the section it is of where the part's page needs it, and the row of steps a step row's page edits."""

    part: str
    name: str
    built_in: object = None
    section: object = None
    steps: object = None
