# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A two-octave keyboard drawn in text, showing which keys a scale uses.

The black keys sit on a row above the white keys, each between the two it belongs to, the scale's
keys are filled and the rest hatched, and the row of names beneath brackets the root, so that a
glance shows where a scale's half steps fall. It returns plain strings and knows nothing of any
toolkit, so the Scale page draws it under its fields.

The Chord dialog draws the same keyboard with a chord on it: rows() gives each
line as pieces, each a text and the kind of key it is, a key of the chord, a key of the scale or a
key outside it, so that the dialog draws the chord's keys filled and the scale's in an outline's
colour. chord_keys() says which keys a chord's notes are, from its root up.
"""

from llamatron.composition import named_scale
from llamatron.music import midi, note
from llamatron.music.note import Note
from llamatron.strings import marks
from llamatron.tui import drawing

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
# How many keys the keyboard has, numbered from its lowest C.
KEY_COUNT = OCTAVES * midi.HALF_STEPS_PER_OCTAVE
# The natural notes as half steps above C, and the marks that raise and lower one, for reading a note's name.
NATURAL_HALF_STEPS = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
SHARP_MARK = '#'
FLAT_MARK = 'b'


class KeyKind:
    """What a key of the keyboard is, when a chord is drawn on it: a key of the chord, a key of the scale, or a key outside the scale."""

    CHORD = 'chord'
    SCALE = 'scale'
    OUTSIDE = 'outside'


def pitch_class_of(name):
    """Return a note name's half steps above C, such as 1 for C# and 10 for Bb, whatever sharps and flats spell it."""
    return (NATURAL_HALF_STEPS[name[0]] + name.count(SHARP_MARK) - name[1:].count(FLAT_MARK)) % midi.HALF_STEPS_PER_OCTAVE


def chord_keys(*, note_names, inversion=None):
    """Return the keys of the keyboard a chord's notes are, as numbers from the lowest C: the root in the first octave and each
    note after it the next key up of its name, an inversion's lowest notes an octave higher, and a note past the last key an
    octave lower, so that every note of the chord has a key."""
    keys = []
    last = -1
    for name in note_names:
        key = pitch_class_of(name)
        while key <= last:
            key += midi.HALF_STEPS_PER_OCTAVE
        last = key
        keys.append(key)
    for place in range(min(inversion or 0, len(keys))):
        keys[place] += midi.HALF_STEPS_PER_OCTAVE
    return {key if key < KEY_COUNT else key % midi.HALF_STEPS_PER_OCTAVE + midi.HALF_STEPS_PER_OCTAVE for key in keys}


class Keyboard:
    """The three lines of a keyboard showing a scale: the black keys, the white keys and the names with the root bracketed."""

    __slots__ = ('root', 'half_steps', 'chord')

    def __init__(self, *, root, half_steps, chord=()):
        """chord is the keys a chord's notes are, numbered from the lowest C, which rows() draws apart."""
        self.root = root
        self.half_steps = half_steps
        self.chord = set(chord)

    def root_pitch_class(self):
        return Note(name=self.root, octave_number=named_scale.SPELLING_OCTAVE).get_midi_number() % midi.HALF_STEPS_PER_OCTAVE

    def pitch_classes(self):
        """Return the half steps above C of every note in the scale."""
        root = self.root_pitch_class()
        return {(root + step) % midi.HALF_STEPS_PER_OCTAVE for step in self.half_steps}

    def key_text(self, pitch_class):
        return marks.MSG_KEY_IN_SCALE if pitch_class in self.pitch_classes() else marks.MSG_KEY_OUT_OF_SCALE

    def white_keys(self):
        """Return the white keys across the octaves, as half steps above C, each with the column it starts at."""
        keys = []
        for octave in range(OCTAVES):
            for place, pitch_class in enumerate(WHITE_KEYS):
                keys.append((pitch_class, WHITE_ROW_INDENT + (octave * len(WHITE_KEYS) + place) * KEY_STRIDE))
        return keys

    def black_row(self):
        line = drawing.SPACE * (WHITE_ROW_INDENT + BLACK_KEY_SHIFT)
        for pitch_class, _ in self.white_keys():
            black = BLACK_KEY_AFTER.get(pitch_class)
            line += (self.key_text(black) if black is not None else drawing.SPACE * KEY_WIDTH) + drawing.SPACE * KEY_GAP
        return line.rstrip()

    def white_row(self):
        line = drawing.SPACE * WHITE_ROW_INDENT
        for pitch_class, _ in self.white_keys():
            line += self.key_text(pitch_class) + drawing.SPACE * KEY_GAP
        return line.rstrip()

    def names_row(self):
        """Return the white keys' names, with the root bracketed: under its white key, or under its black key in place of the two names beside it."""
        root = self.root_pitch_class()
        keys = self.white_keys()
        characters = list(drawing.SPACE * (WHITE_ROW_INDENT + len(keys) * KEY_STRIDE))
        for place, (pitch_class, column) in enumerate(keys):
            name = marks.MSG_ROOT_KEY_NAME.format(name=note.SHARP_NAMES[pitch_class]) if pitch_class == root else note.SHARP_NAMES[pitch_class].center(KEY_WIDTH)
            if BLACK_KEY_AFTER.get(pitch_class) == root or (place > 0 and BLACK_KEY_AFTER.get(keys[place - 1][0]) == root):
                # The root's name sits under its black key, so the white names either side make room for it.
                name = drawing.NOTHING
            characters[column:column + len(name)] = list(name)
        for pitch_class, column in keys:
            if BLACK_KEY_AFTER.get(pitch_class) == root:
                name = marks.MSG_ROOT_KEY_NAME.format(name=self.root)
                start = column + BLACK_KEY_SHIFT + (KEY_WIDTH - len(name)) // 2
                characters[start:start + len(name)] = list(name)
        return drawing.NOTHING.join(characters).rstrip()

    def lines(self):
        return [self.black_row(), self.white_row(), self.names_row()]

    def key_kind(self, key):
        """Return what a key is, by its number from the lowest C."""
        if key in self.chord:
            return KeyKind.CHORD
        return KeyKind.SCALE if key % midi.HALF_STEPS_PER_OCTAVE in self.pitch_classes() else KeyKind.OUTSIDE

    def key_piece(self, key):
        """Return a key as a piece, its text and its kind: a chord's key filled, a scale's outlined and one outside the scale hatched."""
        kind = self.key_kind(key)
        return {KeyKind.CHORD: marks.MSG_KEY_IN_CHORD, KeyKind.SCALE: marks.MSG_KEY_OF_SCALE_OUTLINED, KeyKind.OUTSIDE: marks.MSG_KEY_OUT_OF_SCALE}[kind], kind

    def rows(self):
        """Return the keyboard's three lines as pieces, each a text and a KeyKind, or None for what is no key: the black keys, the
        white keys, and the names, with the chord's keys told apart from the scale's, for the Chord dialog."""
        black = [(drawing.SPACE * (WHITE_ROW_INDENT + BLACK_KEY_SHIFT), None)]
        white = [(drawing.SPACE * WHITE_ROW_INDENT, None)]
        for octave in range(OCTAVES):
            for pitch_class in WHITE_KEYS:
                first = octave * midi.HALF_STEPS_PER_OCTAVE
                after = BLACK_KEY_AFTER.get(pitch_class)
                black.append(self.key_piece(first + after) if after is not None else (drawing.SPACE * KEY_WIDTH, None))
                black.append((drawing.SPACE * KEY_GAP, None))
                white.append(self.key_piece(first + pitch_class))
                white.append((drawing.SPACE * KEY_GAP, None))
        return [black, white, [(self.names_row(), None)]]


def one_octave_rows(pitch_class):
    """Return the three lines of one octave of keys as pieces, each a text and a KeyKind, with one key filled and its name bracketed: the keyswitch note picker's keys."""
    black, white, names = Keyboard(root=note.SHARP_NAMES[pitch_class], half_steps=(), chord={pitch_class}).rows()
    pieces = 1 + len(WHITE_KEYS) * 2
    width = WHITE_ROW_INDENT + len(WHITE_KEYS) * KEY_STRIDE
    return [black[:pieces], white[:pieces], [(names[0][0][:width].rstrip(), None)]]
