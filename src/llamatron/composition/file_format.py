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

# Chords built in exact half steps from the note, which can leave the scale, in the order the
# editor offers them. Bare numbers are kept for chords built from the scale.
FIXED_CHORDS = {
    'M': ChordType.MAJOR, 'm': ChordType.MINOR, 'dim': ChordType.DIMINISHED, 'aug': ChordType.AUGMENTED,
    'sus2': ChordType.SUS2, 'sus4': ChordType.SUS4, 'pow': ChordType.POWER,
    'M6': ChordType.MAJOR6, 'm6': ChordType.MINOR6,
    'dom7': ChordType.DOMINANT7, 'M7': ChordType.MAJOR7, 'm7': ChordType.MINOR7, 'mM7': ChordType.MINOR_MAJOR7,
    'dim7': ChordType.DIMINISHED7, 'm7b5': ChordType.HALF_DIMINISHED7, 'aug7': ChordType.AUGMENTED7,
    'augM7': ChordType.AUGMENTED_MAJOR7, '7sus4': ChordType.DOMINANT7_SUS4,
    'dom9': ChordType.DOMINANT9, 'M9': ChordType.MAJOR9, 'm9': ChordType.MINOR9,
    'add9': ChordType.ADD9, 'madd9': ChordType.MINOR_ADD9,
    'dom11': ChordType.DOMINANT11, 'M11': ChordType.MAJOR11, 'm11': ChordType.MINOR11,
    'dom13': ChordType.DOMINANT13, 'M13': ChordType.MAJOR13, 'm13': ChordType.MINOR13,
}
# Chords that use only notes of the scale, as how many scale degrees each note is above the root.
SCALE_CHORDS = {
    '5': (0, 4), '3': (0, 2, 4), '7': (0, 2, 4, 6), '9': (0, 2, 4, 6, 8),
    '11': (0, 2, 4, 6, 8, 10), '13': (0, 2, 4, 6, 8, 10, 12),
}
CHORD_SYMBOLS = [*FIXED_CHORDS, *SCALE_CHORDS]

# The generators that a chain step can use by name, and the section of a file that names them.
NAMED_GENERATORS = {GeneratorKind.ARP: Section.ARPS, GeneratorKind.AUTO_RATCHET: Section.AUTO_RATCHETS}
