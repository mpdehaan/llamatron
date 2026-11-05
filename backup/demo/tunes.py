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

"""Old tunes for demos to use, as melodies and chord charts.

Simple Gifts is the 1848 Shaker tune, in C major and 4/4. The House of the Rising Sun is the
traditional melody, in A minor and 6/8, without any later arrangement of it. They share the
same notes, and each has a pickup measure followed by 16 measures. The melodies follow the
transcriptions at flutetunes.com, and the chord charts are plain, common harmonizations.
"""

import re
from fractions import Fraction

from llamatron.chord import ChordType
from llamatron.note import Note, Rest
from llamatron.scale import Scale, ScaleType
from llamatron.song import Clip

GIFTS_MEASURE = 1
RISING_SUN_MEASURE = Fraction(3, 4)

C_MAJOR = Scale(Note('C', 4), ScaleType.MAJOR)
A_MINOR = Scale(Note('A', 3), ScaleType.MINOR)

CHORD_TYPES = {
    '': ChordType.MAJOR,
    'm': ChordType.MINOR,
    '7': ChordType.DOMINANT7,
    'm7': ChordType.MINOR7,
    'dim': ChordType.DIMINISHED,
}


def chord(symbol, length):
    """Return a Chord from a symbol like 'Am' or 'E7', with its root around C3."""
    match = re.fullmatch(r'([A-G][#b]?)(.*)', symbol)
    name, kind = match[1], match[2]
    octave = 2 if name[0] in 'AB' else 3
    return Note(name, octave, length).to_chord(CHORD_TYPES[kind])


def melody(text, scale):
    """Return a Clip from words like 'C5:1/4', with '-' as the name for a rest."""
    notes = []
    for word in text.split():
        name, length = word.split(':')
        length = Fraction(length)
        if name == '-':
            notes.append(Rest(length))
        else:
            notes.append(Note(name[:-1], int(name[-1]), length))
    return Clip(notes=notes, scale=scale)


def chart(text, measure_length, scale):
    """Return a Clip of chords from words like 'Am' or 'E7:1/2', lasting a measure by default."""
    chords = []
    for word in text.split():
        symbol, _, length = word.partition(':')
        chords.append(chord(symbol, Fraction(length) if length else measure_length))
    return Clip(notes=chords, scale=scale)


SIMPLE_GIFTS = melody('''
    -:3/4 G4:1/8 G4:1/8
    C5:1/4 C5:1/8 D5:1/8 E5:1/8 C5:1/8 E5:1/8 F5:1/8
    G5:1/4 G5:1/8 F5:1/8 E5:1/4 D5:1/8 C5:1/8
    D5:1/4 D5:1/4 D5:1/4 C5:1/4
    D5:1/8 E5:1/8 D5:1/8 B4:1/8 G4:1/4 G4:1/4
    C5:1/4 C5:1/8 D5:1/8 E5:1/8 C5:1/8 E5:1/8 F5:1/8
    G5:1/4 G5:1/8 F5:1/8 E5:1/4 D5:1/8 C5:1/8
    D5:1/4 D5:1/4 E5:1/4 E5:1/8 D5:1/8
    C5:1/4 C5:1/8 D5:1/8 C5:1/2
    G5:1/2 E5:3/8 D5:1/8
    E5:1/8 F5:1/8 E5:1/8 D5:1/8 C5:1/4 C5:1/8 D5:1/8
    E5:1/4 E5:1/8 F5:1/8 G5:1/4 F5:1/8 E5:1/8
    D5:1/4 D5:1/8 E5:1/8 D5:1/4 G4:1/4
    C5:1/8 B4:1/8 C5:1/8 D5:1/8 E5:1/8 C5:1/8 E5:1/8 F5:1/8
    G5:1/4 G5:1/8 F5:1/8 E5:1/4 E5:1/8 D5:1/8
    D5:1/4 D5:1/4 E5:1/4 E5:1/8 D5:1/8
    C5:1/4 C5:1/8 D5:1/8 C5:1/2
''', C_MAJOR)

SIMPLE_GIFTS_CHORDS = chart('C  C C G G C C G C  C C C G C C G C', GIFTS_MEASURE, C_MAJOR)

# Some notes here are written once but ring across a bar line, as they do when sung.
RISING_SUN = melody('''
    -:5/8 E4:1/8
    A4:5/8 B4:1/8
    C5:5/8 E5:1/8
    D5:1/8 A4:1/8 A4:9/8 A5:1/8
    A5:5/8 A5:1/8
    G5:5/8 E5:1/8
    E5:11/8 A5:1/16 A5:1/16
    A5:5/8 A5:1/8
    G5:5/8 E5:1/8
    D5:5/8 A4:1/8
    C5:5/8 A4:1/8
    A4:5/8 A4:1/8
    G#4:1/8 E4:1/2 G#4:1/8
    A4:11/8 -:1/8
''', A_MINOR)

RISING_SUN_CHORDS = chart('Am  Am C D F Am C E E Am C D F Am E Am Am', RISING_SUN_MEASURE, A_MINOR)
