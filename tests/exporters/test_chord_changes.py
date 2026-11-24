# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A packet's Chord Changes pages (exporters/pdf/chord_changes.py): each move between chords in the order first made, with
how many times, the second chord voiced nearest the first, and the notes that stay, move, are added and are lifted."""

import os
from reportlab.lib.pagesizes import letter
import tempfile
import unittest

from llamatron.exporters.pdf import chord_changes
from llamatron.exporters.pdf.canvas import NumberedCanvas
from llamatron.exporters.pdf.chord_chart import closest_voicing
from llamatron.exporters.pdf.printed_song import PrintedChord
from llamatron.math.rational import Rational
from llamatron.model.schema.file_format import ChordSymbol
from llamatron.model.values.note import NoteName
from llamatron.user_strings import printing
from tests.exporters.test_chord_chart import printed

C = 0
F = 5
PDF_FILE = 'changes.pdf'
BAR = Rational(1)


def chord(*, root, symbol, name):
    """Return a printed chord a bar long at the song's start, for a change's words."""
    return PrintedChord(start=0 * BAR, end=BAR, name=name, numeral='', root=root, symbol=symbol, bass=None)


class TestChordChanges(unittest.TestCase):

    def test_each_move_is_listed_once_in_the_order_first_made_with_how_many_times(self):
        changes = chord_changes.chord_changes(printed())
        self.assertEqual([(change.before.name, change.after.name, change.times) for change in changes],
                         [(NoteName.C, NoteName.F, 2), (NoteName.F, NoteName.C, 1), (NoteName.F, NoteName.B_FLAT, 1)])

    def test_the_second_chord_is_voiced_nearest_the_first_so_that_c_to_f_keeps_c(self):
        first, _ = closest_voicing(root=C, symbol=ChordSymbol.MAJOR)
        change = chord_changes.ChordChange(before=chord(root=C, symbol=ChordSymbol.MAJOR, name=NoteName.C), after=chord(root=F, symbol=ChordSymbol.MAJOR, name=NoteName.F), times=1)
        second = chord_changes.nearest_voicing(chord=change.after, before=first)
        stay, move = chord_changes.change_words(change=change, first=first, second=second, scale=None)
        self.assertEqual(stay, printing.MSG_STAY.format(notes=NoteName.C))
        self.assertIn(printing.MSG_MOVE_TO.format(before=NoteName.E, after=NoteName.F), move)

    def test_a_note_added_or_lifted_is_said_so(self):
        first, _ = closest_voicing(root=C, symbol=ChordSymbol.MAJOR)
        seventh = chord(root=C, symbol=ChordSymbol.DOMINANT7, name=NoteName.C)
        change = chord_changes.ChordChange(before=chord(root=C, symbol=ChordSymbol.MAJOR, name=NoteName.C), after=seventh, times=1)
        second = chord_changes.nearest_voicing(chord=seventh, before=first)
        _, move = chord_changes.change_words(change=change, first=first, second=second, scale=None)
        self.assertEqual(move, printing.MSG_MOVE.format(notes=printing.MSG_ADD_NOTE.format(note=NoteName.B_FLAT)))
        back = chord_changes.ChordChange(before=seventh, after=change.before, times=1)
        _, move = chord_changes.change_words(change=back, first=second, second=first, scale=None)
        self.assertEqual(move, printing.MSG_MOVE.format(notes=printing.MSG_LIFT_NOTE.format(note=NoteName.B_FLAT)))

    def test_the_pages_are_drawn_a_change_a_row(self):
        with tempfile.TemporaryDirectory() as folder:
            page = NumberedCanvas(os.path.join(folder, PDF_FILE), pagesize=letter)
            self.assertTrue(chord_changes.draw_chord_changes(page=page, printed=printed()))
            self.assertEqual(page.page_count(), 1)
