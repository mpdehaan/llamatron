# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later


"""Tests of the keyboard the Chord dialog draws: which keys a chord's notes are, and the pieces each line is drawn from."""

import unittest

from llamatron.composition import file_format
from llamatron.composition.chords import spelled_chord
from llamatron.composition.file_format import ChordSymbol
from llamatron.composition.named_scale import NamedScale, scale_type_name
from llamatron.music import note
from llamatron.music.note import NoteName
from llamatron.music.scale import ScaleType
from llamatron.tui import drawing
from llamatron.tui.components import keyboard as keyboard_values
from llamatron.tui.components.keyboard import chord_keys, Keyboard, KeyKind, pitch_class_of
from llamatron.user_strings import marks

MAJOR = scale_type_name(ScaleType.MAJOR)
# Note names with their half steps above C, the awkward spellings among them.
PITCH_CLASSES = {'C': 0, 'C#': 1, 'Db': 1, 'E#': 5, 'Fb': 4, 'Bb': 10, 'B': 11, 'Cb': 11, 'B#': 0, 'F##': 7, 'Bbb': 9}
C_MAJOR_TRIAD = ('C', 'E', 'G')
A_MINOR_TRIAD = ('A', 'C', 'E')
C_KEY = 0
E_KEY = 4
G_KEY = 7
A_KEY = 9
OCTAVE = 12
FIRST_INVERSION = 1
SECOND_INVERSION = 2
FIRST_DEGREE = 1


class TestChordKeys(unittest.TestCase):

    def test_a_note_name_is_its_half_steps_above_c_however_it_is_spelled(self):
        for name, pitch_class in PITCH_CLASSES.items():
            with self.subTest(name=name):
                self.assertEqual(pitch_class_of(name), pitch_class)

    def test_a_chords_notes_go_up_from_its_root_in_the_first_octave(self):
        self.assertEqual(chord_keys(note_names=C_MAJOR_TRIAD), {C_KEY, E_KEY, G_KEY})
        # The notes after the root are the next keys up, into the second octave.
        self.assertEqual(chord_keys(note_names=A_MINOR_TRIAD), {A_KEY, C_KEY + OCTAVE, E_KEY + OCTAVE})

    def test_an_inversion_puts_its_lowest_notes_an_octave_higher(self):
        self.assertEqual(chord_keys(note_names=C_MAJOR_TRIAD, inversion=FIRST_INVERSION), {C_KEY + OCTAVE, E_KEY, G_KEY})
        self.assertEqual(chord_keys(note_names=C_MAJOR_TRIAD, inversion=SECOND_INVERSION), {C_KEY + OCTAVE, E_KEY + OCTAVE, G_KEY})
        # A note that would pass the last key comes down an octave, so every note keeps a key.
        self.assertEqual(chord_keys(note_names=A_MINOR_TRIAD, inversion=FIRST_INVERSION), {A_KEY + OCTAVE, C_KEY + OCTAVE, E_KEY + OCTAVE})

    def test_every_chord_on_every_root_has_a_key_for_each_of_its_notes(self):
        for root in note.ROOT_NAMES:
            scale = NamedScale(root=root, kind=MAJOR)
            for symbol in file_format.CHORD_SYMBOLS:
                with self.subTest(root=root, symbol=symbol):
                    notes = spelled_chord(scale=scale, degree=FIRST_DEGREE, symbol=symbol).notes
                    keys = chord_keys(note_names=notes)
                    self.assertTrue(all(0 <= key < keyboard_values.KEY_COUNT for key in keys))
                    self.assertEqual({key % OCTAVE for key in keys}, {pitch_class_of(name) for name in notes})


class TestKeyboardRows(unittest.TestCase):

    def keyboard(self, *, chord=()):
        scale = NamedScale(root=NoteName.C, kind=MAJOR)
        return Keyboard(root=scale.get_root(), half_steps=scale.get_half_steps(), chord=chord)

    def row_text(self, row):
        return drawing.NOTHING.join(text for text, _ in row)

    def test_the_pieces_draw_the_keys_where_the_plain_lines_do(self):
        keyboard = self.keyboard()
        plain = keyboard.lines()
        for row, line in zip(keyboard.rows(), plain):
            drawn = self.row_text(row).rstrip()
            self.assertEqual(len(drawn), len(line))
            # A scale's key is outlined where the plain keyboard fills it, and the rest is the same.
            self.assertEqual(drawn.replace(marks.MSG_KEY_OF_SCALE_OUTLINED, marks.MSG_KEY_IN_SCALE), line)

    def test_a_chords_keys_are_filled_the_scales_outlined_and_the_rest_hatched(self):
        keyboard = self.keyboard(chord=chord_keys(note_names=C_MAJOR_TRIAD))
        black, white, names = keyboard.rows()
        kinds = [kind for _, kind in white if kind is not None]
        # C, E and G of the first octave are the chord's; the other white keys are the scale's.
        self.assertEqual(kinds[:7], [KeyKind.CHORD, KeyKind.SCALE, KeyKind.CHORD, KeyKind.SCALE, KeyKind.CHORD, KeyKind.SCALE, KeyKind.SCALE])
        self.assertEqual(set(kinds[7:]), {KeyKind.SCALE})
        self.assertEqual({kind for _, kind in black if kind is not None}, {KeyKind.OUTSIDE})
        self.assertEqual(self.row_text(white).count(marks.MSG_KEY_IN_CHORD), len(C_MAJOR_TRIAD))
        self.assertIn(marks.MSG_KEY_OUT_OF_SCALE, self.row_text(black))
        self.assertEqual(self.row_text(names), keyboard.names_row())
        # A chord's note outside the scale is filled all the same: C minor's Eb.
        minor = self.keyboard(chord=chord_keys(note_names=spelled_chord(scale=NamedScale(root=NoteName.C, kind=MAJOR), degree=FIRST_DEGREE, symbol=ChordSymbol.MINOR).notes))
        self.assertEqual([kind for _, kind in minor.rows()[0] if kind is not None].count(KeyKind.CHORD), 1)
