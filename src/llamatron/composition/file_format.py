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

"""The song file format's fixed lists and defaults, shared by the objects that read and write it."""

from llamatron.chord import ChordType

# The song settings that have defaults, as they're used when a file leaves them out. Every
# setting has one, so that a file written by an older version still loads.
DEFAULT_TEMPO = 120
DEFAULT_LENGTH = '1/16'
GRANULARITIES = ['1/16', '1/32', '1/64', '1/128', '1/256']
DEFAULT_OCTAVE = 3
DEFAULT_DRUM_OCTAVE = 1
DEFAULT_SEED = 1
DEFAULT_VELOCITY = 127
DEFAULT_PROBABILITY = 100
DEFAULT_RATCHET = 1

# Files and the UI number octaves the way Live displays them, where MIDI note 60 is C3. Notes in
# this project number them two higher, so that same note is C5.
LIVE_OCTAVE_OFFSET = 2
MIN_LIVE_OCTAVE, MAX_LIVE_OCTAVE = -2, 8

PATTERN_ROWS = [
    'degree', 'duration', 'accidental', 'octave', 'chord', 'velocity', 'probability', 'glide',
    'ratchet', 'ratchet_offset', 'note_add', 'velocity_add', 'grab',
    'cc1', 'cc2', 'cc3', 'cc4', 'slide',
]
# Rows that are on or off for each step, which files write as true or false.
TOGGLE_ROWS = ('glide', 'grab', 'slide')
# A pattern's CC lanes, whose numbers each track sets for itself.
CC_ROWS = ('cc1', 'cc2', 'cc3', 'cc4')
# Which pattern rows the notes side owns when a clip takes its rhythm from another pattern.
# Everything else belongs to the rhythm.
NOTE_ROWS = ('degree', 'accidental', 'octave', 'chord', 'note_add')
MAX_TRANSPOSE = 24
DEFAULT_ACCUMULATOR_LIMIT = 36
FORWARD = 'forward'
DIRECTIONS = [FORWARD, 'reverse_a', 'reverse_b', 'alternate', 'pendulum', 'random', 'brownian', 'eitherway']
NOTE_LETTERS = 'ABCDEFG'
ACCIDENTALS = {'#': 1, 'b': -1}

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
NAMED_GENERATORS = {'arp': 'arps', 'auto_ratchet': 'auto_ratchets'}
