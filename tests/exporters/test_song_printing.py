# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A song made into what the PDF export prints (exporters/pdf/song_printing.py): the melody tracks merged into one line, the
chord tracks heard as one chord a beat in each scene's key, the keys, the sections, and each track's part by default."""

import os
import unittest

from llamatron.exporters.pdf import song_printing
from llamatron.exporters.pdf.printed_song import PrintedNote
from llamatron.exporters.pdf.song_printing import PrintedPart, TrackNotes
from llamatron.math.rational import Rational
from llamatron.model.objects.setlist import Setlist
from llamatron.model.schema.file_format import SectionKind
from llamatron.model.values.note import NoteName
from llamatron.model.values.time_signature import TimeSignature
from llamatron.music_theory.harmony import heard_chords

SET_FILE = os.path.join('tests', 'data', 'pdf_export', 'printed.yml')
SONG = 'printed'
LEAD = 'lead'
FIDDLE = 'fiddle'
PIANO = 'piano'
KICK = 'kick'
QUARTER = Rational(1, 4)
HALF = Rational(1, 2)
BAR = Rational(1)
C4 = 60
D4 = 62
F3 = 53
C5 = 72
# The Roman numerals of the chords on the first and fourth degrees.
ONE = heard_chords.ROMAN_NUMERALS[0]
FOUR = heard_chords.ROMAN_NUMERALS[3]
PARTS = {LEAD: PrintedPart.MELODY, FIDDLE: PrintedPart.MELODY, PIANO: PrintedPart.CHORDS}


def the_song():
    """Return the test set's song: three one-bar scenes, a verse twice in C Major and a chorus in F Major."""
    return Setlist.read_file(SET_FILE).get_song(SONG)


class TestSongPrinting(unittest.TestCase):

    def test_the_melody_tracks_merge_into_their_highest_line_each_note_ending_where_the_next_begins(self):
        printed = song_printing.printed_song(song=the_song(), title=SONG, parts=PARTS)
        melody = printed.melody
        # The fiddle's high C is struck with the lead's first note, and the lead's next note ends it.
        self.assertEqual(melody[0], PrintedNote(start=0 * BAR, end=QUARTER, pitch=C5))
        self.assertEqual(melody[1], PrintedNote(start=QUARTER, end=HALF, pitch=D4))
        # The chorus has only the fiddle's lower answer, which is the melody there.
        self.assertEqual(melody[-2].pitch, F3)
        self.assertEqual(len(melody), 10)

    def test_a_track_left_out_is_not_printed(self):
        printed = song_printing.printed_song(song=the_song(), title=SONG, parts={LEAD: PrintedPart.MELODY, PIANO: PrintedPart.CHORDS})
        self.assertNotIn(C5, [note.pitch for note in printed.melody])
        self.assertEqual(printed.melody[0], PrintedNote(start=0 * BAR, end=QUARTER, pitch=C4))

    def test_the_chords_are_heard_a_beat_at_a_time_and_joined_while_their_numeral_holds(self):
        chords = song_printing.printed_song(song=the_song(), title=SONG, parts=PARTS).chords
        shown = [(chord.start, chord.end, chord.name, chord.numeral) for chord in chords]
        self.assertEqual(shown[:4], [
            (0 * BAR, HALF, NoteName.C, ONE), (HALF, BAR, NoteName.F, FOUR), (BAR, BAR + HALF, NoteName.C, ONE), (BAR + HALF, 2 * BAR, NoteName.F, FOUR),
        ])
        # In the chorus, in F, the same F chord is I and starts anew, and the chord a fourth above is B flat.
        self.assertEqual(shown[4:], [(2 * BAR, 2 * BAR + HALF, NoteName.F, ONE), (2 * BAR + HALF, 3 * BAR, NoteName.B_FLAT, FOUR)])

    def test_a_key_begins_wherever_the_scenes_scale_changes(self):
        printed = song_printing.printed_song(song=the_song(), title=SONG, parts=PARTS)
        self.assertEqual([(key.start, key.scale.get_root()) for key in printed.keys], [(0 * BAR, NoteName.C), (2 * BAR, NoteName.F)])
        self.assertEqual(printed.main_key().get_root(), NoteName.C)

    def test_sections_follow_the_section_setting_and_without_it_the_key(self):
        song = the_song()
        printed = song_printing.printed_song(song=song, title=SONG, parts=PARTS)
        self.assertEqual([(section.start, section.name) for section in printed.sections], [(0 * BAR, SectionKind.VERSE), (2 * BAR, SectionKind.CHORUS)])
        for scene in song.get_scenes():
            scene.set_section(None)
        printed = song_printing.printed_song(song=song, title=SONG, parts=PARTS)
        names = [scene.get_name() for scene in song.get_scenes()]
        self.assertEqual([(section.start, section.name) for section in printed.sections], [(0 * BAR, names[0]), (2 * BAR, names[2])])

    def test_each_track_plays_its_role_by_default_and_the_drums_are_left_out(self):
        song = the_song()
        tracks = song_printing.track_notes(song_printing.rendered(song))
        parts = song_printing.default_parts(tracks=tracks, signature=song.get_time_signature())
        self.assertEqual(parts[LEAD], PrintedPart.MELODY)
        self.assertEqual(parts[PIANO], PrintedPart.CHORDS)
        self.assertEqual(parts[KICK], PrintedPart.LEFT_OUT)

    def test_a_line_seldom_heard_is_not_the_melody_and_the_highest_chords_carry_it(self):
        bars = 8
        signature = TimeSignature(beats=4, unit=4)
        rare = TrackNotes(name=FIDDLE, drum=False, notes=(PrintedNote(start=0 * BAR, end=QUARTER, pitch=C5), PrintedNote(start=QUARTER, end=HALF, pitch=D4)))
        chords = []
        for bar in range(bars):
            for pitch in (C4, C4 + 4, C4 + 7):
                chords.append(PrintedNote(start=bar * BAR, end=(bar + 1) * BAR, pitch=pitch + 12))
        right_hand = TrackNotes(name=PIANO, drum=False, notes=tuple(chords))
        parts = song_printing.default_parts(tracks=[rare, right_hand], signature=signature)
        self.assertEqual(parts, {FIDDLE: PrintedPart.LEFT_OUT, PIANO: PrintedPart.MELODY})
