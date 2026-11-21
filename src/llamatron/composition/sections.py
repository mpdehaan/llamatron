# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Which sections of named objects belong to the set and which to one song, and how messages name their items.

The set holds what every song shares: scales, patterns, generators of each kind, chains and
grooves, and the songs themselves. A song holds its own tracks and registers. Both change their sections the
same way, through a NamedItems each, and these lists say which is which.
"""

from llamatron.composition import file_format
from llamatron.composition.file_format import Section
from llamatron.user_strings import names

# How error messages name one object in each section of named objects.
SECTION_LABELS = {
    Section.PATTERNS: names.MSG_PATTERN_WORD, Section.CHAINS: names.MSG_CHAIN_WORD, Section.GROOVES: names.MSG_GROOVE_WORD, Section.INSTRUMENTS: names.MSG_INSTRUMENT_WORD, Section.SCALES: names.MSG_SCALE_WORD, Section.TRACKS: names.MSG_TRACK_WORD,
    Section.REGISTERS: names.MSG_REGISTER_WORD, Section.DRAWS: names.MSG_DRAW_WORD, Section.SONGS: names.MSG_SONG_WORD,
    **{section: kind for kind, section in file_format.NAMED_GENERATORS.items()},
}
# The set's sections, in the order they're written to a file, with the songs last.
SETLIST_SECTIONS = [Section.SCALES, Section.PATTERNS, *file_format.NAMED_GENERATORS.values(), Section.CHAINS, Section.GROOVES, Section.INSTRUMENTS, Section.SONGS]
# A song's sections, in the order they're written, before its scenes.
SONG_SECTIONS = [Section.REGISTERS, Section.DRAWS, Section.TRACKS]
# The generator kind each generator section holds, like arp for arps.
GENERATOR_KINDS = {section: kind for kind, section in file_format.NAMED_GENERATORS.items()}
# The sections whose items share one list of generators in a set file, the chains among them, and so may share no name.
GENERATOR_SECTIONS = (*file_format.NAMED_GENERATORS.values(), Section.CHAINS)
