# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The PDF export (exporters/pdf/pdf_export.py, chord_sequence.py and pdf_script.py): the packet of the pages ticked, named
<set>_<song>__packet.pdf, the Chord Sequence's bars and keys, and the command line's options."""

import contextlib
import io
import os
import tempfile
import unittest

from llamatron.exporters.pdf import chord_sequence, pdf_export, pdf_script
from llamatron.exporters.pdf.pdf_export import PacketPage, PdfChoices, PdfKind
from llamatron.model.objects.named_scale import NamedScale
from llamatron.model.objects.setlist import Setlist
from llamatron.model.schema.file_format import ScaleKind
from llamatron.model.values.note import NoteName
from llamatron.music_theory.harmony import heard_chords
from llamatron.user_strings import printing
from tests.exporters import test_song_printing
from tests.exporters.test_chord_chart import printed

NAME = 'printed_printed'
FOUR = heard_chords.ROMAN_NUMERALS[3]


class TestPdfExport(unittest.TestCase):

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.song = Setlist.read_file(test_song_printing.SET_FILE).get_song(test_song_printing.SONG)

    def test_the_packet_is_one_pdf_named_after_the_set_and_song(self):
        written = pdf_export.export_pdfs(song=self.song, title=test_song_printing.SONG, directory=self.temporary.name, name=NAME, choices=PdfChoices(tracks=test_song_printing.TRACKS))
        self.assertEqual(written, [pdf_export.pdf_path(directory=self.temporary.name, name=NAME, kind=PdfKind.PACKET)])
        self.assertTrue(os.path.getsize(written[0]))

    def test_nothing_ticked_writes_nothing(self):
        choices = PdfChoices(packet_pages=(), tracks=test_song_printing.TRACKS)
        self.assertEqual(pdf_export.export_pdfs(song=self.song, title=test_song_printing.SONG, directory=self.temporary.name, name=NAME, choices=choices), [])
        self.assertEqual(os.listdir(self.temporary.name), [])

    def test_the_chord_sequence_holds_each_bars_chords_and_names_a_key_in_the_main_key(self):
        song = printed()
        bars = chord_sequence.section_bars(printed=song, start=0 * song.length, end=song.bar_length())
        self.assertEqual([[chord.name for chord in chords] for _, chords in bars], [[NoteName.C, NoteName.F]])
        f_major = NamedScale(root=NoteName.F, kind=ScaleKind.MAJOR)
        c_major = NamedScale(root=NoteName.C, kind=ScaleKind.MAJOR)
        self.assertEqual(chord_sequence.key_line(scale=f_major, main=c_major),
                         printing.MSG_KEY_IN.format(key=printing.MSG_KEY.format(key=chord_sequence.key_name(f_major)), numeral=FOUR, main=chord_sequence.key_name(c_major)))

    def test_the_script_writes_the_pages_named_with_the_tracks_named(self):
        said = io.StringIO()
        with contextlib.redirect_stdout(said):
            pdf_script.main(arguments=[test_song_printing.SET_FILE, pdf_script.OPTION_OUTPUT, self.temporary.name, pdf_script.OPTION_PAGES, PacketPage.CHORD_CHART,
                                       pdf_script.OPTION_TRACKS, test_song_printing.LEAD + pdf_script.LIST_JOIN + test_song_printing.PIANO])
        self.assertEqual(len(os.listdir(self.temporary.name)), 1)
        self.assertIn(self.temporary.name, said.getvalue())

    def test_the_script_takes_the_tracks_named_or_every_pitched_track(self):
        named = pdf_script.parser().parse_args([test_song_printing.SET_FILE, pdf_script.OPTION_TRACKS, test_song_printing.FIDDLE])
        self.assertEqual(named.tracks, [test_song_printing.FIDDLE])
        self.assertEqual(pdf_export.default_tracks(self.song), {test_song_printing.LEAD, test_song_printing.FIDDLE, test_song_printing.PIANO})

    def test_the_script_refuses_a_page_the_packet_has_not(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            pdf_script.parser().parse_args([test_song_printing.SET_FILE, pdf_script.OPTION_PAGES, test_song_printing.SONG])
