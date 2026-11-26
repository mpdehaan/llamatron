# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Which sections of named objects belong to the set and which to one song, and how messages name their items.

The set holds what every song shares: scales, patterns, generators of each kind, chains and
grooves, and the songs themselves. A song holds its own tracks and registers. Both change their sections the
same way, through a NamedItems each, and these lists say which is which.
"""

import functools

from llamatron.model.schema import generator_plugins
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import names

# How error messages name one object in each section of named objects.
SECTION_LABELS = {
    Section.PATTERNS: names.MSG_PATTERN_WORD, Section.CHAINS: names.MSG_CHAIN_WORD, Section.GROOVES: names.MSG_GROOVE_WORD, Section.INSTRUMENTS: names.MSG_INSTRUMENT_WORD, Section.SCALES: names.MSG_SCALE_WORD, Section.TRACKS: names.MSG_TRACK_WORD,
    Section.DRAWS: names.MSG_DRAW_WORD, Section.SONGS: names.MSG_SONG_WORD,
}
# A song's sections, in the order they're written, before its scenes.
SONG_SECTIONS = [Section.DRAWS, Section.TRACKS]


def section_label(section):
    """Return how error messages name one object of a section: a generator plugin's section by the plugin's name."""
    return generator_plugins.names_by_section().get(section) or SECTION_LABELS[section]


@functools.cache
def setlist_sections():
    """Return the set's sections, in the order they're written to a file, the generator plugins' by their names, the songs last."""
    return [Section.SCALES, Section.PATTERNS, *generator_plugins.sections_by_name().values(), Section.CHAINS, Section.GROOVES, Section.INSTRUMENTS, Section.SONGS]


@functools.cache
def generator_sections():
    """Return the sections whose items share one list of generators in a set file, the chains among them, and so may share no name."""
    return (*generator_plugins.sections_by_name().values(), Section.CHAINS)
