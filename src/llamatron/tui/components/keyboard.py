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
"""A two-octave keyboard drawn in text, showing which keys a scale uses, approved by the user on 2026-11-08.

The black keys sit on a row above the white keys, each between the two it belongs to, the scale's
keys are filled and the rest hatched, and the row of names beneath brackets the root, so that a
glance shows where a scale's half steps fall. It returns plain strings and knows nothing of any
toolkit, so the Scale page draws it under its fields.
"""

from llamatron.composition.named_scale import SPELLING_OCTAVE
from llamatron.music.midi import HALF_STEPS_PER_OCTAVE
from llamatron.music.note import Note, SHARP_NAMES
from llamatron.tui.drawing import NOTHING, SPACE
from llamatron.strings.marks import MSG_KEY_IN_SCALE, MSG_KEY_OUT_OF_SCALE, MSG_ROOT_KEY_NAME

# The white keys of an octave as half steps above C, and the black key after each white key that has one.
WHITE_KEYS = [0, 2, 4, 5, 7, 9, 11]
BLACK_KEY_AFTER = {0: 1, 2: 3, 5: 6, 7: 8, 9: 10}
OCTAVES = 2
# A key is three characters wide with one between keys, the white row starts after four columns and the black keys sit half a key along.
KEY_WIDTH = 3
KEY_GAP = 1
KEY_STRIDE = KEY_WIDTH + KEY_GAP
WHITE_ROW_INDENT = 4
BLACK_KEY_SHIFT = 2


class Keyboard:
    """The three lines of a keyboard showing a scale: the black keys, the white keys and the names with the root bracketed."""

    __slots__ = ('root', 'half_steps')

    def __init__(self, *, root, half_steps):
        self.root = root
        self.half_steps = half_steps

    def root_pitch_class(self):
        return Note(name=self.root, octave_number=SPELLING_OCTAVE).get_midi_number() % HALF_STEPS_PER_OCTAVE

    def pitch_classes(self):
        """Return the half steps above C of every note in the scale."""
        root = self.root_pitch_class()
        return {(root + step) % HALF_STEPS_PER_OCTAVE for step in self.half_steps}

    def key_text(self, pitch_class):
        return MSG_KEY_IN_SCALE if pitch_class in self.pitch_classes() else MSG_KEY_OUT_OF_SCALE

    def white_keys(self):
        """Return the white keys across the octaves, as half steps above C, each with the column it starts at."""
        keys = []
        for octave in range(OCTAVES):
            for place, pitch_class in enumerate(WHITE_KEYS):
                keys.append((pitch_class, WHITE_ROW_INDENT + (octave * len(WHITE_KEYS) + place) * KEY_STRIDE))
        return keys

    def black_row(self):
        line = SPACE * (WHITE_ROW_INDENT + BLACK_KEY_SHIFT)
        for pitch_class, _ in self.white_keys():
            black = BLACK_KEY_AFTER.get(pitch_class)
            line += (self.key_text(black) if black is not None else SPACE * KEY_WIDTH) + SPACE * KEY_GAP
        return line.rstrip()

    def white_row(self):
        line = SPACE * WHITE_ROW_INDENT
        for pitch_class, _ in self.white_keys():
            line += self.key_text(pitch_class) + SPACE * KEY_GAP
        return line.rstrip()

    def names_row(self):
        """Return the white keys' names, with the root bracketed: under its white key, or under its black key in place of the two names beside it."""
        root = self.root_pitch_class()
        keys = self.white_keys()
        characters = list(SPACE * (WHITE_ROW_INDENT + len(keys) * KEY_STRIDE))
        for place, (pitch_class, column) in enumerate(keys):
            name = MSG_ROOT_KEY_NAME.format(name=SHARP_NAMES[pitch_class]) if pitch_class == root else SHARP_NAMES[pitch_class].center(KEY_WIDTH)
            if BLACK_KEY_AFTER.get(pitch_class) == root or (place > 0 and BLACK_KEY_AFTER.get(keys[place - 1][0]) == root):
                # The root's name sits under its black key, so the white names either side make room for it.
                name = NOTHING
            characters[column:column + len(name)] = list(name)
        for pitch_class, column in keys:
            if BLACK_KEY_AFTER.get(pitch_class) == root:
                name = MSG_ROOT_KEY_NAME.format(name=self.root)
                start = column + BLACK_KEY_SHIFT + (KEY_WIDTH - len(name)) // 2
                characters[start:start + len(name)] = list(name)
        return NOTHING.join(characters).rstrip()

    def lines(self):
        return [self.black_row(), self.white_row(), self.names_row()]
