# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A packet's piano roll (exporters/pdf/piano_roll.py): a section played several times in a row drawn once, the rows of
bars and their lanes, how tall a lane is drawn, the strip of a page's chord changes, and the pages."""

import os
from reportlab.lib.pagesizes import letter
import tempfile
import unittest

from llamatron.exporters.pdf import piano_roll, song_printing
from llamatron.exporters.pdf.canvas import NumberedCanvas
from llamatron.exporters.pdf.printed_song import PrintedChord, PrintedSong
from llamatron.math.rational import Rational
from llamatron.model.objects.setlist import Setlist
from llamatron.model.schema.file_format import ChordSymbol
from llamatron.model.values.note import NoteName
from tests.exporters import test_song_printing
from tests.exporters.test_chord_chart import printed

BAR = Rational(1)
PDF_FILE = 'roll.pdf'
C = 0
F = 5
G = 7


def chord(*, start, name, root):
    """Return a major chord a bar long, as printed."""
    return PrintedChord(start=start, end=start + BAR, name=name, numeral='', root=root, symbol=ChordSymbol.MAJOR, bass=None)


class TestPianoRoll(unittest.TestCase):

    def test_a_section_played_twice_in_a_row_is_drawn_once(self):
        song = Setlist.read_file(test_song_printing.SET_FILE).get_song(test_song_printing.SONG)
        for scene in song.get_scenes():
            scene.set_section(None)
        song.get_scenes()[1].set_repeat(2)
        repeated = song_printing.printed_song(song=song, title=test_song_printing.SONG, tracks=test_song_printing.TRACKS)
        self.assertEqual(piano_roll.printed_spans(repeated), [(0 * BAR, BAR), (BAR, 2 * BAR), (3 * BAR, 4 * BAR)])

    def test_rows_hold_sixteen_beats_and_their_lanes_span_the_melody_an_octave_at_least(self):
        rows = piano_roll.roll_rows(printed())
        # The verse is two bars of four beats, the chorus one: each section starts a row of its own.
        self.assertEqual([row.bars for row in rows], [(0 * BAR, BAR), (2 * BAR,)])
        self.assertTrue(all(row.high - row.low + 1 >= piano_roll.FEWEST_LANES for row in rows))

    def test_lanes_narrow_so_that_two_rows_fit_a_page(self):
        wide = piano_roll.PrintedRollRow(start=0 * BAR, end=BAR, bars=(0 * BAR,), low=36, high=96)
        self.assertEqual(piano_roll.lane_height(rows=[wide], room=piano_roll.ChordRoom(row=piano_roll.CHORD_HEIGHT, strip=piano_roll.STRIP_HEIGHT)), piano_roll.NARROWEST_LANE)
        narrow = piano_roll.PrintedRollRow(start=0 * BAR, end=BAR, bars=(0 * BAR,), low=60, high=72)
        self.assertEqual(piano_roll.lane_height(rows=[narrow], room=piano_roll.ChordRoom(row=piano_roll.CHORD_HEIGHT, strip=piano_roll.STRIP_HEIGHT)), piano_roll.LANE_HEIGHT)

    def test_the_strip_shows_each_change_once_and_starts_afresh_after_one_left_out(self):
        chords = [chord(start=0 * BAR, name=NoteName.C, root=C), chord(start=BAR, name=NoteName.F, root=F), chord(start=2 * BAR, name=NoteName.C, root=C),
                  chord(start=3 * BAR, name=NoteName.F, root=F), chord(start=4 * BAR, name=NoteName.G, root=G)]
        song = PrintedSong(title=test_song_printing.SONG, melody=(), chords=tuple(chords), keys=(), sections=(), signature=printed().signature, tempo=None, length=5 * BAR)
        strip = piano_roll.page_chords(printed=song, start=0 * BAR, end=5 * BAR)
        self.assertEqual([(item.chord.name, item.follows) for item in strip],
                         [(NoteName.C, False), (NoteName.F, True), (NoteName.C, True), (NoteName.F, False), (NoteName.G, True)])

    def test_the_roll_is_drawn_on_landscape_pages(self):
        with tempfile.TemporaryDirectory() as folder:
            page = NumberedCanvas(os.path.join(folder, PDF_FILE), pagesize=letter)
            piano_roll.draw_piano_roll(page=page, printed=printed())
            self.assertEqual(page.page_count(), 1)

    def test_a_song_printed_without_chords_leaves_no_room_for_them(self):
        with_chords = printed()
        song = PrintedSong(title=with_chords.title, melody=with_chords.melody, chords=(), keys=with_chords.keys, sections=with_chords.sections,
                           signature=with_chords.signature, tempo=with_chords.tempo, length=with_chords.length)
        self.assertEqual(piano_roll.chord_room(song), piano_roll.ChordRoom(row=0, strip=0))
        with tempfile.TemporaryDirectory() as folder:
            page = NumberedCanvas(os.path.join(folder, PDF_FILE), pagesize=letter)
            piano_roll.draw_piano_roll(page=page, printed=song)
            self.assertEqual(page.page_count(), 1)
