# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A packet's chord chart (exporters/pdf/chord_chart.py): a card for each chord name in the order the song first plays it,
its numerals in every key it is heard in, how long it lasts, its closest voicing named as fingering, and its pages."""

import os
from reportlab.lib.pagesizes import letter
import tempfile
import unittest

from llamatron.exporters.pdf import chord_chart, song_printing
from llamatron.exporters.pdf.canvas import NumberedCanvas
from llamatron.math.rational import Rational
from llamatron.model.objects.setlist import Setlist
from llamatron.model.schema.file_format import ChordSymbol
from llamatron.model.values.note import NoteName
from llamatron.music_theory.harmony import heard_chords
from llamatron.user_strings import printing
from tests.exporters import test_song_printing

F = 5
C = 0
PDF_FILE = 'chart.pdf'
ONE = heard_chords.ROMAN_NUMERALS[0]
FOUR = heard_chords.ROMAN_NUMERALS[3]


def printed():
    """Return the test set's song as printed."""
    return song_printing.printed_song(song=Setlist.read_file(test_song_printing.SET_FILE).get_song(test_song_printing.SONG), title=test_song_printing.SONG, parts=test_song_printing.PARTS)


class TestChordChart(unittest.TestCase):

    def test_each_chord_name_has_one_card_in_the_order_first_played_with_its_numerals_and_bars(self):
        cards = chord_chart.chart_cards(printed())
        self.assertEqual([card.name for card in cards], [NoteName.C, NoteName.F, NoteName.B_FLAT])
        f_major = cards[1]
        # F is IV in the verse's C major and I in the chorus's F major, and plays half of each of the three bars.
        self.assertEqual(f_major.numerals, (FOUR, ONE))
        self.assertEqual(f_major.bars, Rational(3, 2))

    def test_a_chord_takes_its_closest_voicing_named_as_fingering(self):
        voicing, inversion = chord_chart.closest_voicing(root=F, symbol=ChordSymbol.MAJOR)
        self.assertEqual((voicing, inversion), ((60, 65, 69), 2))
        card = chord_chart.ChartCard(name=NoteName.F, root=F, symbol=ChordSymbol.MAJOR, numerals=(FOUR,), voicing=voicing, inversion=inversion, bars=Rational(3, 2))
        notes = chord_chart.card_notes(card=card, scale=printed().main_key())
        self.assertIn(printing.MSG_INVERSIONS[2], notes)
        self.assertIn(printing.MSG_BARS.format(bars=2), notes)

    def test_a_power_chord_says_it_has_no_third(self):
        voicing, inversion = chord_chart.closest_voicing(root=C, symbol=ChordSymbol.POWER)
        card = chord_chart.ChartCard(name=NoteName.C, root=C, symbol=ChordSymbol.POWER, numerals=(), voicing=voicing, inversion=inversion, bars=Rational(1))
        self.assertIn(printing.MSG_NO_THIRD, chord_chart.card_notes(card=card, scale=None))

    def test_the_chart_takes_a_page_for_every_eight_cards(self):
        with tempfile.TemporaryDirectory() as folder:
            page = NumberedCanvas(os.path.join(folder, PDF_FILE), pagesize=letter)
            chord_chart.draw_chord_chart(page=page, printed=printed())
            self.assertEqual(page.page_count(), 1)
            page.save()
            self.assertTrue(os.path.getsize(os.path.join(folder, PDF_FILE)))
