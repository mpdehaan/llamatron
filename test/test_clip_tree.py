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

import contextlib
import io
import os
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

import mido

from llamatron.music.chord import Chord, ChordType
from llamatron.music.note import Note, NoteName, Rest
from llamatron.music.time_signature import TimeSignature
from llamatron.exporters.clip_tree import TICKS_PER_BEAT, ClipTree, clip_file_name
from llamatron.exporters.midi_messages import (
    END_OF_TRACK_META, NOTE_OFF_MESSAGE, NOTE_ON_MESSAGE, TEMPO_META, TIME_SIGNATURE_META, TRACK_NAME_META,
)
from llamatron.exporters.timing import VELOCITY
from llamatron.grid.clip import Clip
from llamatron.grid.clip_grid import ClipGrid
from llamatron.grid.clip_row import ClipRow
from llamatron.grid.clip_column import ClipColumn

C4 = Note(name='C', octave_number=4, length=0.25)
D4 = Note(name='D', octave_number=4, length=0.25)
E4 = Note(name='E', octave_number=4, length=0.25)
G4 = Note(name='G', octave_number=4, length=0.25)

# Names the tests give to their own things, and other values they use.
END = 'end'
ELSEWHERE = 'elsewhere'
OUTPUT = 'output'
SONG = 'song'
RIFF = 'Riff'
VERSE = 'verse'
BASS = 'bass'
BIG_BASS_LINE = 'Big  Bass Line'
A = 'a'
B = 'b'
C4_2 = 'C4'
MY_RIFF = 'My Riff'
WB = 'wb'
READ_BYTES = 'rb'
WARNING = 'warning'
# The name the clips are written under, as the tracker and the command line name a song's exports.
EXPORT = 'set_song'
CLIP = EXPORT + '_clip_'


def export(exporter):
    """Export and return what was printed."""
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exporter.export()
    return output.getvalue()

# Time signatures the tests use, as a file writes them.
WALTZ = '3/4'
COMPOUND_DUPLE = '6/8'


def events(path):
    """Return a MIDI file's notes and end as (type, note, tick), with ticks from the start."""
    result = []
    tick = 0
    for message in mido.MidiFile(path).tracks[0]:
        tick += message.time
        if message.type in (NOTE_ON_MESSAGE, NOTE_OFF_MESSAGE):
            result.append((message.type, message.note, tick))
        elif message.type == END_OF_TRACK_META:
            result.append((END, None, tick))
    return result


def on(*, note, beat):
    return (NOTE_ON_MESSAGE, note, round(beat * TICKS_PER_BEAT))


def off(*, note, beat):
    return (NOTE_OFF_MESSAGE, note, round(beat * TICKS_PER_BEAT))


def end(beat):
    return (END, None, round(beat * TICKS_PER_BEAT))


class TestClipTreeFields(unittest.TestCase):

    def test_keeps_directory_and_song(self):
        song = ClipGrid()
        exporter = ClipTree(directory=OUTPUT, grid=song)
        self.assertEqual(exporter.get_directory(), OUTPUT)
        self.assertIs(exporter.get_grid(), song)

    def test_directory_can_be_a_path(self):
        self.assertEqual(ClipTree(directory=Path(OUTPUT), grid=ClipGrid()).get_directory(), Path(OUTPUT))

    def test_rejects_invalid_directories(self):
        for directory in ['', None, 1, ClipGrid()]:
            with self.subTest(directory=directory):
                with self.assertRaises(ValueError):
                    ClipTree(directory=directory, grid=ClipGrid())

    def test_rejects_invalid_songs(self):
        for song in [None, SONG, ClipColumn()]:
            with self.subTest(song=song):
                with self.assertRaises(ValueError):
                    ClipTree(directory=OUTPUT, grid=song)

    def test_fields_can_be_edited(self):
        exporter = ClipTree(directory=OUTPUT, grid=ClipGrid())
        other_song = ClipGrid()
        exporter.set_directory(ELSEWHERE)
        exporter.set_grid(other_song)
        self.assertEqual(exporter.get_directory(), ELSEWHERE)
        self.assertIs(exporter.get_grid(), other_song)

    def test_edited_fields_are_validated(self):
        song = ClipGrid()
        exporter = ClipTree(directory=OUTPUT, grid=song)
        with self.assertRaises(ValueError):
            exporter.set_directory(None)
        with self.assertRaises(ValueError):
            exporter.set_grid(None)
        self.assertEqual(exporter.get_directory(), OUTPUT)
        self.assertIs(exporter.get_grid(), song)

    def test_creating_a_exporter_does_not_create_the_directory(self):
        with tempfile.TemporaryDirectory() as parent:
            directory = os.path.join(parent, OUTPUT)
            ClipTree(directory=directory, grid=ClipGrid())
            self.assertFalse(os.path.exists(directory))


class ExportTestCase(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = temporary.name
        self.song = ClipGrid()
        self.exporter = ClipTree(directory=self.directory, grid=self.song, name=EXPORT)

    def path(self, filename):
        return os.path.join(self.directory, filename)

    def files(self):
        return sorted(os.listdir(self.directory))


class TestFileNames(ExportTestCase):

    def test_one_file_per_filled_slot_named_scene_then_track(self):
        tracks = [self.song.add_column(ClipColumn()) for _ in range(3)]
        scenes = [self.song.add_row(ClipRow()) for _ in range(2)]
        self.song.set_clip(row=scenes[0], column=tracks[0], clip=Clip())
        self.song.set_clip(row=scenes[0], column=tracks[2], clip=Clip())
        self.song.set_clip(row=scenes[1], column=tracks[1], clip=Clip())
        export(self.exporter)
        self.assertEqual(self.files(), [CLIP + 's_001-t_001.mid', CLIP + 's_001-t_003.mid', CLIP + 's_002-t_002.mid'])

    def export_clip_in(self, *, scene_name=None, track_name=None, clip_name=None):
        track = self.song.add_column(ClipColumn(name=track_name))
        scene = self.song.add_row(ClipRow(name=scene_name))
        self.song.set_clip(row=scene, column=track, clip=Clip(name=clip_name))
        export(self.exporter)
        return self.files()

    def test_the_scene_and_track_names_follow_their_numbers(self):
        self.assertEqual(self.export_clip_in(scene_name=VERSE, track_name=BASS), [CLIP + 's_001-verse-t_001-bass.mid'])

    def test_spaces_in_the_names_become_underscores(self):
        self.assertEqual(self.export_clip_in(track_name=BIG_BASS_LINE), [CLIP + 's_001-t_001-Big__Bass_Line.mid'])

    def test_ids_are_zero_padded_to_three_digits(self):
        tracks = [self.song.add_column(ClipColumn()) for _ in range(12)]
        scenes = [self.song.add_row(ClipRow()) for _ in range(3)]
        self.song.set_clip(row=scenes[2], column=tracks[11], clip=Clip())
        export(self.exporter)
        self.assertEqual(self.files(), [CLIP + 's_003-t_012.mid'])

    def test_ids_past_three_digits_still_work(self):
        track = self.song.add_column(ClipColumn())
        for _ in range(1000):
            scene = self.song.add_row(ClipRow())
        self.song.set_clip(row=scene, column=track, clip=Clip())
        export(self.exporter)
        self.assertEqual(self.files(), [CLIP + 's_1000-t_001.mid'])
        self.song.set_clip(row=self.song.add_row(ClipRow()), column=track, clip=Clip())
        os.remove(self.path(CLIP + 's_1000-t_001.mid'))
        export(self.exporter)
        self.assertIn(CLIP + 's_1001-t_001.mid', self.files())

    def test_a_scene_or_track_without_a_name_is_just_its_number(self):
        self.assertEqual(self.export_clip_in(scene_name=None, track_name=''), [CLIP + 's_001-t_001.mid'])

    def test_slashes_in_a_name_cannot_leave_the_directory(self):
        self.assertEqual(self.export_clip_in(scene_name='../up/and\\out'), [CLIP + 's_001-.._up_and_out-t_001.mid'])

    def test_the_clip_name_is_not_used(self):
        self.assertEqual(self.export_clip_in(scene_name=VERSE, clip_name=RIFF), [CLIP + 's_001-verse-t_001.mid'])

    def test_the_name_comes_from_the_directory_unless_given(self):
        nested = self.path(SONG)
        track = self.song.add_column(ClipColumn())
        scene = self.song.add_row(ClipRow())
        self.song.set_clip(row=scene, column=track, clip=Clip())
        export(ClipTree(directory=nested, grid=self.song))
        self.assertEqual(os.listdir(nested), [SONG + '_clip_s_001-t_001.mid'])
        self.assertEqual(clip_file_name(name=EXPORT, scene=scene, track=track), CLIP + 's_001-t_001.mid')

    def test_empty_song_writes_nothing(self):
        self.song.add_column(ClipColumn())
        self.song.add_row(ClipRow())
        export(self.exporter)
        self.assertEqual(self.files(), [])

    def test_creates_a_missing_directory(self):
        nested = self.path(os.path.join(A, B))
        track = self.song.add_column(ClipColumn())
        scene = self.song.add_row(ClipRow())
        self.song.set_clip(row=scene, column=track, clip=Clip())
        export(ClipTree(directory=nested, grid=self.song, name=EXPORT))
        self.assertEqual(os.listdir(nested), [CLIP + 's_001-t_001.mid'])

    def test_accepts_a_path_object(self):
        track = self.song.add_column(ClipColumn())
        scene = self.song.add_row(ClipRow())
        self.song.set_clip(row=scene, column=track, clip=Clip())
        export(ClipTree(directory=Path(self.directory), grid=self.song, name=EXPORT))
        self.assertEqual(self.files(), [CLIP + 's_001-t_001.mid'])


class TestFileContents(ExportTestCase):

    def setUp(self):
        super().setUp()
        self.track = self.song.add_column(ClipColumn())
        self.scene = self.song.add_row(ClipRow())

    def export_clip(self, clip):
        self.song.set_clip(row=self.scene, column=self.track, clip=clip)
        export(self.exporter)
        return self.path(CLIP + 's_001-t_001.mid')

    def tempo(self, path):
        return next(m.tempo for m in mido.MidiFile(path).tracks[0] if m.type == TEMPO_META)

    def time_signature(self, path):
        return next((m.numerator, m.denominator) for m in mido.MidiFile(path).tracks[0] if m.type == TIME_SIGNATURE_META)

    def test_each_file_carries_the_song_time_signature(self):
        self.song.set_time_signature(TimeSignature.from_text(WALTZ))
        self.assertEqual(self.time_signature(self.export_clip(Clip(notes=[C4]))), (3, 4))

    def test_a_clip_with_its_own_time_signature_writes_that_one(self):
        self.song.set_time_signature(TimeSignature.from_text(WALTZ))
        own = Clip(notes=[C4], time_signature=TimeSignature.from_text(COMPOUND_DUPLE))
        self.assertEqual(self.time_signature(self.export_clip(own)), (6, 8))

    def test_notes_play_one_after_another(self):
        path = self.export_clip(Clip(notes=[C4, D4]))
        self.assertEqual(events(path), [
            on(note=48, beat=0), off(note=48, beat=1), on(note=50, beat=1), off(note=50, beat=2), end(2),
        ])

    def test_chord_notes_start_and_stop_together(self):
        path = self.export_clip(Clip(notes=[Chord([C4, E4, G4])]))
        self.assertEqual(events(path), [
            on(note=48, beat=0), on(note=52, beat=0), on(note=55, beat=0),
            off(note=48, beat=1), off(note=52, beat=1), off(note=55, beat=1),
            end(1),
        ])

    def test_positions_can_mix_notes_and_chords(self):
        path = self.export_clip(Clip(notes=[C4, Chord([D4, G4]), E4]))
        self.assertEqual(events(path), [
            on(note=48, beat=0), off(note=48, beat=1),
            on(note=50, beat=1), on(note=55, beat=1), off(note=50, beat=2), off(note=55, beat=2),
            on(note=52, beat=2), off(note=52, beat=3),
            end(3),
        ])

    def test_chord_from_note_to_chord(self):
        path = self.export_clip(Clip(notes=[C4.to_chord(ChordType.MAJOR)]))
        self.assertEqual([e[1] for e in events(path) if e[0] == NOTE_ON_MESSAGE], [48, 52, 55])

    def test_chord_with_a_repeated_pitch_plays_it_once(self):
        path = self.export_clip(Clip(notes=[Chord([C4, Note(name=NoteName.B_SHARP, octave_number=3, length=0.25)])]))
        self.assertEqual(events(path), [on(note=48, beat=0), off(note=48, beat=1), end(1)])

    def test_notes_use_a_fixed_velocity(self):
        path = self.export_clip(Clip(notes=[C4]))
        message = next(m for m in mido.MidiFile(path).tracks[0] if m.type == NOTE_ON_MESSAGE)
        self.assertEqual(message.velocity, VELOCITY)

    def test_each_note_uses_its_own_length(self):
        path = self.export_clip(Clip(notes=[Note(name=NoteName.C, octave_number=4, length=0.5), Note(name=NoteName.D, octave_number=4, length=0.125)]))
        self.assertEqual(events(path), [
            on(note=48, beat=0), off(note=48, beat=2), on(note=50, beat=2), off(note=50, beat=2.5), end(2.5),
        ])

    def test_lengths_are_fractions_of_a_whole_note(self):
        cases = [(1, 4), (0.5, 2), (0.25, 1), (0.125, 0.5), (2, 8)]
        for length, beats in cases:
            with self.subTest(length=length):
                directory = self.path(str(length))
                self.song.set_clip(row=self.scene, column=self.track, clip=Clip(notes=[Note(name=NoteName.C, octave_number=4, length=length)]))
                export(ClipTree(directory=directory, grid=self.song, name=EXPORT))
                self.assertEqual(
                    events(os.path.join(directory, CLIP + 's_001-t_001.mid')),
                    [on(note=48, beat=0), off(note=48, beat=beats), end(beats)],
                )

    def test_length_can_be_a_triplet_fraction(self):
        triplet = Fraction(1, 12)
        notes = [Note(name=NoteName.C, octave_number=4, length=triplet), Note(name=NoteName.D, octave_number=4, length=triplet), Note(name=NoteName.E, octave_number=4, length=triplet)]
        self.assertEqual(events(self.export_clip(Clip(notes=notes))), [
            (NOTE_ON_MESSAGE, 48, 0), (NOTE_OFF_MESSAGE, 48, 160),
            (NOTE_ON_MESSAGE, 50, 160), (NOTE_OFF_MESSAGE, 50, 320),
            (NOTE_ON_MESSAGE, 52, 320), (NOTE_OFF_MESSAGE, 52, 480),
            (END, None, 480),
        ])

    def test_rest_adds_silence_between_notes(self):
        path = self.export_clip(Clip(notes=[C4, Rest(0.5), D4]))
        self.assertEqual(events(path), [
            on(note=48, beat=0), off(note=48, beat=1), on(note=50, beat=3), off(note=50, beat=4), end(4),
        ])

    def test_rest_can_start_a_clip(self):
        path = self.export_clip(Clip(notes=[Rest(0.25), C4]))
        self.assertEqual(events(path), [on(note=48, beat=1), off(note=48, beat=2), end(2)])

    def test_rest_can_end_a_clip(self):
        path = self.export_clip(Clip(notes=[C4, Rest(0.25)]))
        self.assertEqual(events(path), [on(note=48, beat=0), off(note=48, beat=1), end(2)])

    def test_clip_of_only_rests_is_silent(self):
        self.assertEqual(events(self.export_clip(Clip(notes=[Rest(1)]))), [end(4)])

    def test_same_pitch_can_repeat(self):
        path = self.export_clip(Clip(notes=[C4, C4]))
        self.assertEqual(events(path), [
            on(note=48, beat=0), off(note=48, beat=1), on(note=48, beat=1), off(note=48, beat=2), end(2),
        ])

    def test_chord_notes_can_have_different_lengths(self):
        chord = Chord([Note(name=NoteName.C, octave_number=4, length=0.5), Note(name=NoteName.G, octave_number=4, length=0.25)])
        path = self.export_clip(Clip(notes=[chord, D4]))
        self.assertEqual(events(path), [
            on(note=48, beat=0), on(note=55, beat=0), off(note=55, beat=1), off(note=48, beat=2),
            on(note=50, beat=2), off(note=50, beat=3),
            end(3),
        ])

    def test_chord_with_a_repeated_pitch_uses_the_longest_length(self):
        chord = Chord([Note(name=NoteName.C, octave_number=4, length=0.25), Note(name=NoteName.B_SHARP, octave_number=3, length=0.5)])
        path = self.export_clip(Clip(notes=[chord]))
        self.assertEqual(events(path), [on(note=48, beat=0), off(note=48, beat=2), end(2)])

    def test_longer_length_adds_silence(self):
        path = self.export_clip(Clip(notes=[C4], length=1))
        self.assertEqual(events(path), [on(note=48, beat=0), off(note=48, beat=1), end(4)])

    def test_shorter_length_cuts_off_notes(self):
        path = self.export_clip(Clip(notes=[C4, D4, E4], length=0.375))
        self.assertEqual(events(path), [
            on(note=48, beat=0), off(note=48, beat=1), on(note=50, beat=1), off(note=50, beat=1.5), end(1.5),
        ])

    def test_length_at_a_position_boundary_drops_later_notes(self):
        path = self.export_clip(Clip(notes=[C4, D4], length=0.25))
        self.assertEqual(events(path), [on(note=48, beat=0), off(note=48, beat=1), end(1)])

    def test_clip_without_notes_is_empty(self):
        self.assertEqual(events(self.export_clip(Clip())), [end(0)])

    def test_clip_without_notes_can_still_have_a_length(self):
        self.assertEqual(events(self.export_clip(Clip(length=1))), [end(4)])

    def test_uses_the_song_tempo_by_default(self):
        self.assertEqual(self.tempo(self.export_clip(Clip())), mido.bpm2tempo(120))

    def test_uses_the_scene_tempo_over_the_song(self):
        self.scene.set_tempo(90)
        self.assertEqual(self.tempo(self.export_clip(Clip())), mido.bpm2tempo(90))

    def test_minimum_tempo_can_be_written(self):
        self.song.set_tempo(10)
        self.assertEqual(self.tempo(self.export_clip(Clip())), mido.bpm2tempo(10))

    def track_name(self, filename):
        messages = mido.MidiFile(self.path(filename)).tracks[0]
        names = [message.name for message in messages if message.type == TRACK_NAME_META]
        self.assertEqual(len(names), 1)
        return names[0]

    def test_track_name_is_the_file_name_without_the_extension(self):
        self.export_clip(Clip(name=MY_RIFF, notes=[C4]))
        self.assertEqual(self.track_name(CLIP + 's_001-t_001.mid'), CLIP + 's_001-t_001')

    def test_track_name_with_other_characters_can_still_be_saved(self):
        self.track.set_name('Caf\u00e9 \u6771')
        self.song.set_clip(row=self.scene, column=self.track, clip=Clip(notes=[C4]))
        export(self.exporter)
        self.assertEqual(self.files(), [CLIP + 's_001-t_001-Caf\u00e9_\u6771.mid'])
        self.assertEqual(self.track_name(CLIP + 's_001-t_001-Caf\u00e9_\u6771.mid'), CLIP + 's_001-t_001-Caf\u00e9_?')

    def test_file_has_the_expected_resolution_and_format(self):
        midi_file = mido.MidiFile(self.export_clip(Clip()))
        self.assertEqual(midi_file.ticks_per_beat, TICKS_PER_BEAT)
        self.assertEqual(midi_file.type, 0)
        self.assertEqual(len(midi_file.tracks), 1)

    def test_invalid_item_added_to_a_list_writes_nothing(self):
        other_track = self.song.add_column(ClipColumn())
        self.song.set_clip(row=self.scene, column=other_track, clip=Clip(notes=[C4]))
        clip = self.song.set_clip(row=self.scene, column=self.track, clip=Clip())
        clip.get_notes().append(C4_2)
        with self.assertRaises(ValueError):
            self.exporter.export()
        self.assertEqual(self.files(), [])


class TestExistingFiles(ExportTestCase):

    def setUp(self):
        super().setUp()
        self.track = self.song.add_column(ClipColumn())
        self.scene = self.song.add_row(ClipRow())
        self.song.set_clip(row=self.scene, column=self.track, clip=Clip(notes=[C4]))

    def write(self, *, filename, content=b'keep me'):
        with open(self.path(filename), WB) as file:
            file.write(content)

    def read(self, filename):
        with open(self.path(filename), READ_BYTES) as file:
            return file.read()

    def test_no_warning_for_an_empty_directory(self):
        self.assertEqual(export(self.exporter), '')

    def test_unrelated_files_are_kept_without_a_word(self):
        self.write(filename='notes.txt')
        output = export(self.exporter)
        self.assertEqual(self.read('notes.txt'), b'keep me')
        self.assertNotIn(WARNING, output)
        self.assertEqual(self.files(), ['notes.txt', CLIP + 's_001-t_001.mid'])

    def test_stale_files_from_removed_clips_are_kept(self):
        self.write(filename=CLIP + 's_006-t_006.mid')
        output = export(self.exporter)
        self.assertEqual(self.read(CLIP + 's_006-t_006.mid'), b'keep me')
        self.assertNotIn(WARNING, output)
        self.assertEqual(self.files(), [CLIP + 's_001-t_001.mid', CLIP + 's_006-t_006.mid'])

    def test_matching_file_stops_with_a_warning_and_is_kept(self):
        self.write(filename=CLIP + 's_001-t_001.mid')
        output = export(self.exporter)
        self.assertEqual(self.read(CLIP + 's_001-t_001.mid'), b'keep me')
        self.assertIn('warning: stopping', output)
        self.assertIn(CLIP + 's_001-t_001.mid', output)

    def test_matching_file_stops_every_other_file_from_being_written(self):
        other_track = self.song.add_column(ClipColumn())
        self.song.set_clip(row=self.scene, column=other_track, clip=Clip(notes=[C4]))
        self.write(filename=CLIP + 's_001-t_002.mid')
        export(self.exporter)
        self.assertEqual(self.files(), [CLIP + 's_001-t_002.mid'])

    def test_warning_lists_every_matching_file(self):
        other_track = self.song.add_column(ClipColumn())
        self.song.set_clip(row=self.scene, column=other_track, clip=Clip(notes=[C4]))
        self.write(filename=CLIP + 's_001-t_001.mid')
        self.write(filename=CLIP + 's_001-t_002.mid')
        output = export(self.exporter)
        self.assertIn(CLIP + 's_001-t_001.mid, ' + CLIP + 's_001-t_002.mid', output)

    def test_exporting_twice_stops_and_keeps_the_first_files(self):
        export(self.exporter)
        first = self.read(CLIP + 's_001-t_001.mid')
        self.song.get_clip(row=self.scene, column=self.track).set_length(8)
        output = export(self.exporter)
        self.assertEqual(self.read(CLIP + 's_001-t_001.mid'), first)
        self.assertIn('warning: stopping', output)


if __name__ == '__main__':
    unittest.main()
