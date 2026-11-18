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
"""Which sections of named objects belong to the set and which to one song, and how messages name their items.

The set holds what every song shares: scales, patterns, generators of each kind, chains and
grooves, and the songs themselves. A song holds its own tracks and registers. Both change their sections the
same way, through a NamedItems each, and these lists say which is which.
"""

from llamatron.composition.file_format import NAMED_GENERATORS, Section
from llamatron.strings import names

# How error messages name one object in each section of named objects.
SECTION_LABELS = {
    Section.PATTERNS: names.MSG_PATTERN_WORD, Section.CHAINS: names.MSG_CHAIN_WORD, Section.GROOVES: names.MSG_GROOVE_WORD, Section.INSTRUMENTS: names.MSG_INSTRUMENT_WORD, Section.SCALES: names.MSG_SCALE_WORD, Section.TRACKS: names.MSG_TRACK_WORD,
    Section.REGISTERS: names.MSG_REGISTER_WORD, Section.SONGS: names.MSG_SONG_WORD,
    **{section: kind for kind, section in NAMED_GENERATORS.items()},
}
# The set's sections, in the order they're written to a file, with the songs last.
SETLIST_SECTIONS = [Section.SCALES, Section.PATTERNS, *NAMED_GENERATORS.values(), Section.CHAINS, Section.GROOVES, Section.INSTRUMENTS, Section.SONGS]
# A song's sections, in the order they're written, before its scenes.
SONG_SECTIONS = [Section.REGISTERS, Section.TRACKS]
# The generator kind each generator section holds, like arp for arps.
GENERATOR_KINDS = {section: kind for kind, section in NAMED_GENERATORS.items()}
