# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""How a heard chord is named and numbered in a key (music_theory/harmony/heard_chords.py): its root spelled in the key, an
applied chord numbered by the chord it leads to, and a borrowed chord by its root."""

import unittest

from llamatron.model.objects.named_scale import NamedScale
from llamatron.model.schema.file_format import ChordSymbol, ScaleKind
from llamatron.model.values.note import NoteName
from llamatron.music_theory.harmony import heard_chords
from llamatron.user_strings import marks

C_MAJOR = NamedScale(root=NoteName.C, kind=ScaleKind.MAJOR)
C = 0
D = 2
E = 4
F = 5
F_SHARP = 6
G = 7
B_FLAT = 10
G_SHARP = 8
E_FLAT = 3
F_MAJOR = NamedScale(root=NoteName.F, kind=ScaleKind.MAJOR)
FOUR = heard_chords.ROMAN_NUMERALS[3]
FIVE = heard_chords.ROMAN_NUMERALS[4]
SIX = heard_chords.ROMAN_NUMERALS[5]
SEVEN = heard_chords.ROMAN_NUMERALS[6]


def applied(*, dominant, target):
    """Return an applied chord's numeral, as marks writes it."""
    return marks.MSG_SECONDARY_DOMINANT.format(dominant=dominant, target=target)


class TestHeardChordNames(unittest.TestCase):

    def test_a_secondary_dominant_is_numbered_by_the_chord_it_leads_to(self):
        self.assertEqual(heard_chords.chord_texts(root=D, symbol=ChordSymbol.DOMINANT7, scale=C_MAJOR), ('D7', applied(dominant=marks.MSG_DOMINANT_SEVENTH_NUMERAL, target=FIVE)))
        self.assertEqual(heard_chords.chord_texts(root=E, symbol=ChordSymbol.DOMINANT7, scale=C_MAJOR)[1], applied(dominant=marks.MSG_DOMINANT_SEVENTH_NUMERAL, target=SIX.lower()))
        self.assertEqual(heard_chords.chord_texts(root=C, symbol=ChordSymbol.DOMINANT7, scale=C_MAJOR)[1], applied(dominant=marks.MSG_DOMINANT_SEVENTH_NUMERAL, target=FOUR))

    def test_the_keys_own_dominant_is_plain(self):
        self.assertEqual(heard_chords.chord_texts(root=G, symbol=ChordSymbol.DOMINANT7, scale=C_MAJOR), ('G7', FIVE))

    def test_a_diminished_seventh_a_half_step_below_a_chord_leads_to_it(self):
        self.assertEqual(heard_chords.chord_texts(root=F_SHARP, symbol=ChordSymbol.DIMINISHED7, scale=C_MAJOR),
                         ('F#dim7', applied(dominant=marks.MSG_LEADING_TONE_SEVENTH_NUMERAL, target=FIVE)))

    def test_a_borrowed_chord_is_numbered_by_its_root_and_spelled_with_a_flat(self):
        self.assertEqual(heard_chords.chord_texts(root=F, symbol=ChordSymbol.MINOR, scale=C_MAJOR), ('Fm', FOUR.lower()))
        flat = marks.MSG_ACCIDENTAL_MARKS[heard_chords.Accidental.FLAT]
        self.assertEqual(heard_chords.chord_texts(root=B_FLAT, symbol=ChordSymbol.DOMINANT7, scale=C_MAJOR), ('Bb7', flat + SEVEN))

    def test_a_chords_notes_are_spelled_from_its_root_by_interval(self):
        self.assertEqual(heard_chords.chord_tone_names(root=C, symbol=ChordSymbol.DOMINANT7, scale=C_MAJOR)[B_FLAT], NoteName.B_FLAT)
        self.assertEqual(heard_chords.chord_tone_names(root=F_SHARP, symbol=ChordSymbol.DIMINISHED7, scale=C_MAJOR)[E_FLAT], NoteName.E_FLAT)

    def test_a_slash_bass_is_spelled_as_its_chords_note(self):
        name, _ = heard_chords.chord_texts(root=E, symbol=ChordSymbol.DOMINANT7, scale=F_MAJOR, bass=G_SHARP)
        self.assertTrue(name.endswith(NoteName.G_SHARP))
