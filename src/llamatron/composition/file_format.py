# llamatron: a Python language and framework for producing MIDI clips.
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

"""The names the song file format uses, and its fixed lists, shared by everything that reads or writes it.

Each group of names is a class of constants, like Row.DEGREE for 'degree', so that code names
what it means and a misspelled name fails at once. The values are the plain strings the file
holds.
"""

from llamatron.chord import ChordType
# The defaults stay importable from here too, for code that reads the format and its defaults together.
from llamatron.composition.defaults import (  # noqa: F401
    DEFAULT_ACCUMULATOR_LIMIT, DEFAULT_DRUM_OCTAVE, DEFAULT_LENGTH, DEFAULT_OCTAVE, DEFAULT_PROBABILITY,
    DEFAULT_RATCHET, DEFAULT_SEED, DEFAULT_TEMPO, DEFAULT_VELOCITY, GRANULARITIES,
)
# And so do the limits that the rest of the program reads from here.
from llamatron.composition.limits import MAX_LIVE_OCTAVE, MAX_TRANSPOSE, MIN_LIVE_OCTAVE  # noqa: F401


class Section:
    """The sections of a song file that hold named objects, and its list of scenes."""

    SCALES = 'scales'
    PATTERNS = 'patterns'
    TRACKS = 'tracks'
    ARPS = 'arps'
    AUTO_RATCHETS = 'auto_ratchets'
    CHAINS = 'chains'
    SCENES = 'scenes'


class SongSetting:
    """The song's own settings, at the top of a file."""

    TITLE = 'title'
    AUTHOR = 'author'
    DESCRIPTION = 'description'
    TEMPO = 'tempo'
    SCALE = 'scale'
    SEED = 'seed'
    DEFAULT_LENGTH = 'default_length'
    GRANULARITY = 'granularity'
    DEFAULT_OCTAVE = 'default_octave'
    DEFAULT_DRUM_OCTAVE = 'default_drum_octave'


class ScaleSetting:
    """A named scale's settings."""

    ROOT = 'root'
    TYPE = 'type'


class TrackSetting:
    """A track's settings."""

    DRUM = 'drum'
    MUTE = 'mute'
    TRANSPOSE = 'transpose'
    CC = 'cc'


class PatternSetting:
    """A pattern's settings, besides its rows."""

    STEPS = 'steps'
    DRUM = 'drum'
    DIRECTION = 'direction'
    ACCUMULATOR_LIMIT = 'accumulator_limit'


class Row:
    """A pattern's rows, each holding one value for every step, as in the pattern editor."""

    DEGREE = 'degree'
    DURATION = 'duration'
    ACCIDENTAL = 'accidental'
    OCTAVE = 'octave'
    CHORD = 'chord'
    VELOCITY = 'velocity'
    PROBABILITY = 'probability'
    GLIDE = 'glide'
    RATCHET = 'ratchet'
    RATCHET_OFFSET = 'ratchet_offset'
    NOTE_ADD = 'note_add'
    VELOCITY_ADD = 'velocity_add'
    GRAB = 'grab'
    CC1 = 'cc1'
    CC2 = 'cc2'
    CC3 = 'cc3'
    CC4 = 'cc4'
    SLIDE = 'slide'


class CellSetting:
    """What a scene's cell for a track can set."""

    PATTERN = 'pattern'
    CHAIN = 'chain'
    LOOP = 'loop'
    REPEAT = 'repeat'
    DIRECTION = 'direction'
    MORPH_TO = 'morph_to'
    MORPH_STYLE = 'morph_style'
    RHYTHM_FROM = 'rhythm_from'
    GRAB_TRACK = 'grab_track'


class SceneSetting:
    """A scene's settings, and the cells it holds for its tracks."""

    NAME = 'name'
    REPEAT = 'repeat'
    SCALE = 'scale'
    TEMPO = 'tempo'
    TEMPO_START = 'tempo_start'
    TEMPO_END = 'tempo_end'
    TRACKS = 'tracks'


class Direction:
    """The orders a pattern's steps can play in, with the Cirklon's names for them."""

    FORWARD = 'forward'
    REVERSE_A = 'reverse_a'
    REVERSE_B = 'reverse_b'
    ALTERNATE = 'alternate'
    PENDULUM = 'pendulum'
    RANDOM = 'random'
    BROWNIAN = 'brownian'
    EITHERWAY = 'eitherway'


class GeneratorKind:
    """The kinds of generator a chain step can name."""

    ARP = 'arp'
    AUTO_RATCHET = 'auto_ratchet'


class Accidental:
    """The accidentals a step can have."""

    SHARP = '#'
    FLAT = 'b'


# Files and the UI number octaves the way Live displays them, where MIDI note 60 is C3. Notes in
# this project number them two higher, so that same note is C5.
LIVE_OCTAVE_OFFSET = 2

PATTERN_ROWS = [
    Row.DEGREE, Row.DURATION, Row.ACCIDENTAL, Row.OCTAVE, Row.CHORD, Row.VELOCITY, Row.PROBABILITY, Row.GLIDE,
    Row.RATCHET, Row.RATCHET_OFFSET, Row.NOTE_ADD, Row.VELOCITY_ADD, Row.GRAB,
    Row.CC1, Row.CC2, Row.CC3, Row.CC4, Row.SLIDE,
]
# Rows that are on or off for each step, which files write as true or false.
TOGGLE_ROWS = (Row.GLIDE, Row.GRAB, Row.SLIDE)
# A pattern's CC lanes, whose numbers each track sets for itself.
CC_ROWS = (Row.CC1, Row.CC2, Row.CC3, Row.CC4)
# Which pattern rows the notes side owns when a clip takes its rhythm from another pattern.
# Everything else belongs to the rhythm.
NOTE_ROWS = (Row.DEGREE, Row.ACCIDENTAL, Row.OCTAVE, Row.CHORD, Row.NOTE_ADD)
# Rows that hold a whole number of any size, positive or negative.
SIGNED_ROWS = (Row.RATCHET_OFFSET, Row.NOTE_ADD, Row.VELOCITY_ADD)
FORWARD = Direction.FORWARD
DIRECTIONS = [
    Direction.FORWARD, Direction.REVERSE_A, Direction.REVERSE_B, Direction.ALTERNATE, Direction.PENDULUM,
    Direction.RANDOM, Direction.BROWNIAN, Direction.EITHERWAY,
]
NOTE_LETTERS = 'ABCDEFG'
# How many half steps each accidental moves a note.
ACCIDENTALS = {Accidental.SHARP: 1, Accidental.FLAT: -1}

class ChordSymbol:
    """The chord symbols a step's Chord row can hold, as a file writes them.

    Named symbols, like M or dom7, are exact half steps from the step's note, so they can leave
    the scale. Plain numbers stack every other note of the scale from the step's degree, so they
    follow the scale, which is why dominants are written dom7 rather than 7.
    """

    MAJOR = 'M'
    MINOR = 'm'
    DIMINISHED = 'dim'
    AUGMENTED = 'aug'
    SUS2 = 'sus2'
    SUS4 = 'sus4'
    POWER = 'pow'
    MAJOR6 = 'M6'
    MINOR6 = 'm6'
    DOMINANT7 = 'dom7'
    MAJOR7 = 'M7'
    MINOR7 = 'm7'
    MINOR_MAJOR7 = 'mM7'
    DIMINISHED7 = 'dim7'
    HALF_DIMINISHED7 = 'm7b5'
    AUGMENTED7 = 'aug7'
    AUGMENTED_MAJOR7 = 'augM7'
    DOMINANT7_SUS4 = '7sus4'
    DOMINANT9 = 'dom9'
    MAJOR9 = 'M9'
    MINOR9 = 'm9'
    ADD9 = 'add9'
    MINOR_ADD9 = 'madd9'
    DOMINANT11 = 'dom11'
    MAJOR11 = 'M11'
    MINOR11 = 'm11'
    DOMINANT13 = 'dom13'
    MAJOR13 = 'M13'
    MINOR13 = 'm13'
    SCALE_FIFTH = '5'
    SCALE_TRIAD = '3'
    SCALE_SEVENTH = '7'
    SCALE_NINTH = '9'
    SCALE_ELEVENTH = '11'
    SCALE_THIRTEENTH = '13'


# The named chord symbols, in the order the editor offers them, and the chords they make.
FIXED_CHORDS = {
    ChordSymbol.MAJOR: ChordType.MAJOR, ChordSymbol.MINOR: ChordType.MINOR,
    ChordSymbol.DIMINISHED: ChordType.DIMINISHED, ChordSymbol.AUGMENTED: ChordType.AUGMENTED,
    ChordSymbol.SUS2: ChordType.SUS2, ChordSymbol.SUS4: ChordType.SUS4, ChordSymbol.POWER: ChordType.POWER,
    ChordSymbol.MAJOR6: ChordType.MAJOR6, ChordSymbol.MINOR6: ChordType.MINOR6,
    ChordSymbol.DOMINANT7: ChordType.DOMINANT7, ChordSymbol.MAJOR7: ChordType.MAJOR7, ChordSymbol.MINOR7: ChordType.MINOR7,
    ChordSymbol.MINOR_MAJOR7: ChordType.MINOR_MAJOR7, ChordSymbol.DIMINISHED7: ChordType.DIMINISHED7,
    ChordSymbol.HALF_DIMINISHED7: ChordType.HALF_DIMINISHED7, ChordSymbol.AUGMENTED7: ChordType.AUGMENTED7,
    ChordSymbol.AUGMENTED_MAJOR7: ChordType.AUGMENTED_MAJOR7, ChordSymbol.DOMINANT7_SUS4: ChordType.DOMINANT7_SUS4,
    ChordSymbol.DOMINANT9: ChordType.DOMINANT9, ChordSymbol.MAJOR9: ChordType.MAJOR9, ChordSymbol.MINOR9: ChordType.MINOR9,
    ChordSymbol.ADD9: ChordType.ADD9, ChordSymbol.MINOR_ADD9: ChordType.MINOR_ADD9,
    ChordSymbol.DOMINANT11: ChordType.DOMINANT11, ChordSymbol.MAJOR11: ChordType.MAJOR11, ChordSymbol.MINOR11: ChordType.MINOR11,
    ChordSymbol.DOMINANT13: ChordType.DOMINANT13, ChordSymbol.MAJOR13: ChordType.MAJOR13, ChordSymbol.MINOR13: ChordType.MINOR13,
}
# The chord symbols that stack notes of the scale, and how many scale degrees above the step's
# degree each of their notes is. A scale fifth is the root and the fifth, and each of the others
# adds every other scale note above the root.
SCALE_CHORDS = {
    ChordSymbol.SCALE_FIFTH: (0, 4),
    ChordSymbol.SCALE_TRIAD: (0, 2, 4),
    ChordSymbol.SCALE_SEVENTH: (0, 2, 4, 6),
    ChordSymbol.SCALE_NINTH: (0, 2, 4, 6, 8),
    ChordSymbol.SCALE_ELEVENTH: (0, 2, 4, 6, 8, 10),
    ChordSymbol.SCALE_THIRTEENTH: (0, 2, 4, 6, 8, 10, 12),
}
CHORD_SYMBOLS = [*FIXED_CHORDS, *SCALE_CHORDS]

# The generators that a chain step can use by name, and the section of a file that names them.
NAMED_GENERATORS = {GeneratorKind.ARP: Section.ARPS, GeneratorKind.AUTO_RATCHET: Section.AUTO_RATCHETS}
