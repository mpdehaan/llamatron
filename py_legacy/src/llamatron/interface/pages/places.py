# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Places: where a page is, as a value, so that a presenter says where to go without naming the tracker's page that shows it
(the declarative pages' design). The tracker's site map (interface/tracker/site_map.py) knows which page shows each place.

A named thing's page (an ItemPlace) and a generator's part pages: each place names its part, the generator by its name, where it is built in, if it is a
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
# The kinds of place, which the site map makes each kind's page by.
GENERATOR_PART = 'generator part'
ITEM = 'item'


@dataclass(frozen=True, slots=True, kw_only=True)
class GeneratorPartPlace:
    """The page of one part of a generator: the part, the generator's name, where it is built in or None for one of the set's,
    the section it is of where the part's page needs it, and the row of steps a step row's page edits."""

    KIND = GENERATOR_PART

    part: str
    name: str
    built_in: object = None
    section: object = None
    steps: object = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ItemPlace:
    """The page of one named thing of the set: its section and its name, as a list page opens it."""

    KIND = ITEM

    section: str
    name: str
