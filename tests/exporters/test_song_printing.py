# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A song made into what the PDF export prints (exporters/pdf/song_printing.py): the tracks chosen merged into one and read
as a lead sheet, the tune its skyline without a low cluster, the chords estimated a bar or half bar at a time, the keys, the
sections, and the tracks a PDF takes by default."""

import os
import unittest

from llamatron.exporters.pdf import song_printing
from llamatron.exporters.pdf.printed_song import PrintedNote
from llamatron.exporters.pdf.song_printing import TrackNotes
from llamatron.math.rational import Rational
from llamatron.model.objects.setlist import Setlist
from llamatron.model.schema.file_format import SectionKind
from llamatron.model.values.note import NoteName
from llamatron.music_theory.harmony import chord_estimate, heard_chords

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
TRACKS = frozenset({LEAD, FIDDLE, PIANO})


def the_song():
    """Return the test set's song: three one-bar scenes, a verse twice in C Major and a chorus in F Major."""
    return Setlist.read_file(SET_FILE).get_song(SONG)


class TestSongPrinting(unittest.TestCase):

    def test_the_tune_is_the_skyline_of_the_tracks_merged_each_note_ending_where_the_next_begins(self):
        melody = song_printing.printed_song(song=the_song(), title=SONG, tracks=TRACKS).melody
        # The fiddle's high C is struck with the lead's first note, and the lead's next note ends it; the piano's chords sound
        # below them all and are no part of the tune.
        self.assertEqual(melody[0], PrintedNote(start=0 * BAR, end=QUARTER, pitch=C5))
        self.assertEqual(melody[1], PrintedNote(start=QUARTER, end=HALF, pitch=D4))

    def test_a_track_left_out_is_not_printed(self):
        printed = song_printing.printed_song(song=the_song(), title=SONG, tracks=frozenset({LEAD, PIANO}))
        self.assertNotIn(C5, [note.pitch for note in printed.melody])
        self.assertEqual(printed.melody[0], PrintedNote(start=0 * BAR, end=QUARTER, pitch=C4))

    def test_the_chords_are_estimated_a_bar_or_half_bar_at_a_time_in_each_scenes_key(self):
        chords = song_printing.printed_song(song=the_song(), title=SONG, tracks=frozenset({PIANO}), level=chord_estimate.ChordLevel.TRIADS).chords
        shown = [(chord.start, chord.end, chord.name, chord.numeral) for chord in chords]
        # The piano's bar of C then F splits into halves, which clearly differ.
        self.assertEqual(shown[:2], [(0 * BAR, HALF, NoteName.C, ONE), (HALF, BAR, NoteName.F, FOUR)])
        # In the chorus, in F, the chord a fourth above is B flat, numbered IV.
        self.assertEqual(shown[-1], (2 * BAR + HALF, 3 * BAR, NoteName.B_FLAT, FOUR))

    def test_a_note_doubling_the_tune_at_the_octave_counts_as_the_tune(self):
        tune = [PrintedNote(start=0 * BAR, end=QUARTER, pitch=C5)]
        below = PrintedNote(start=0 * BAR, end=QUARTER, pitch=C4)
        other = PrintedNote(start=0 * BAR, end=QUARTER, pitch=D4)
        self.assertEqual(song_printing.doubled_tune(merged=[tune[0], below, other], melody=tune), [tune[0], below])

    def test_as_played_hears_a_chord_a_beat(self):
        chords = song_printing.printed_song(song=the_song(), title=SONG, tracks=TRACKS, level=chord_estimate.ChordLevel.AS_PLAYED).chords
        self.assertTrue(chords)
        self.assertTrue(all(chord.end - chord.start >= QUARTER for chord in chords))

    def test_a_low_cluster_the_top_line_drops_into_is_cut_from_the_tune(self):
        tune = [PrintedNote(start=step * QUARTER, end=(step + 1) * QUARTER, pitch=C5 + step % 5) for step in range(20)]
        bass = [PrintedNote(start=(20 + step) * QUARTER, end=(21 + step) * QUARTER, pitch=F3 - 12) for step in range(5)]
        self.assertEqual(song_printing.without_low_cluster(tune + bass), tune)
        self.assertEqual(song_printing.without_low_cluster(tune), tune)

    def test_a_key_begins_wherever_the_scenes_scale_changes(self):
        printed = song_printing.printed_song(song=the_song(), title=SONG, tracks=TRACKS)
        self.assertEqual([(key.start, key.scale.get_root()) for key in printed.keys], [(0 * BAR, NoteName.C), (2 * BAR, NoteName.F)])
        self.assertEqual(printed.main_key().get_root(), NoteName.C)

    def test_sections_follow_the_section_setting(self):
        printed = song_printing.printed_song(song=the_song(), title=SONG, tracks=TRACKS)
        self.assertEqual([(section.start, section.name) for section in printed.sections], [(0 * BAR, SectionKind.VERSE), (2 * BAR, SectionKind.CHORUS)])

    def test_without_the_section_setting_each_scene_is_a_section_and_one_played_again_is_counted(self):
        song = the_song()
        for scene in song.get_scenes():
            scene.set_section(None)
        song.get_scenes()[1].set_repeat(2)
        printed = song_printing.printed_song(song=song, title=SONG, tracks=TRACKS)
        names = [scene.get_name() for scene in song.get_scenes()]
        self.assertEqual([(section.start, section.name, section.times) for section in printed.sections],
                         [(0 * BAR, names[0], 1), (BAR, names[1], 2), (3 * BAR, names[2], 1)])

    def test_every_track_playing_pitched_notes_is_taken_by_default_and_the_drums_never(self):
        tracks = song_printing.track_notes(song_printing.rendered(the_song()))
        self.assertEqual(song_printing.default_tracks(tracks), {LEAD, FIDDLE, PIANO})
        self.assertNotIn(KICK, song_printing.default_tracks([TrackNotes(name=KICK, drum=True, notes=(PrintedNote(start=0 * BAR, end=QUARTER, pitch=C4),))]))
