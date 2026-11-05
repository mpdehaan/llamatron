# llamatron: a Python language and framework for producing MIDI clips.
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

import mido

from llamatron.chord import Chord
from llamatron.importers.clip_tree import ClipTreeImporter
from llamatron.note import Note, Rest
from llamatron.renderers.clip_tree import ClipTree
from llamatron.song import Clip, Scene, Song, Track

C4 = Note('C', 4, 0.25)
D4 = Note('D', 4, 0.5)


class ImporterTestCase(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = temporary.name

    def path(self, filename):
        return os.path.join(self.directory, filename)

    def load(self):
        return ClipTreeImporter(self.directory).load()

    def write_song(self, song):
        with contextlib.redirect_stdout(io.StringIO()):
            ClipTree(self.directory, song).render()

    def round_trip(self, clip):
        """Render one clip, load it back, and return the loaded clip."""
        song = Song()
        track = song.add_track(Track())
        scene = song.add_scene(Scene())
        song.set_clip(scene, track, clip)
        self.write_song(song)
        loaded = self.load()
        return loaded.get_clip(loaded.scenes[0], loaded.tracks[0])

    def write_midi(self, filename, messages, ticks_per_beat=480):
        midi_file = mido.MidiFile(ticks_per_beat=ticks_per_beat, tracks=[mido.MidiTrack(messages)])
        midi_file.save(self.path(filename))


class TestNoteFromMidiNumber(unittest.TestCase):

    def test_makes_the_note(self):
        self.assertEqual(Note.from_midi_number(48), Note('C', 4))
        self.assertEqual(Note.from_midi_number(127), Note('G', 10))
        self.assertEqual(Note.from_midi_number(0), Note('C', 0))

    def test_uses_sharps(self):
        self.assertEqual(Note.from_midi_number(49).name, 'C#')

    def test_takes_a_length(self):
        self.assertEqual(Note.from_midi_number(48, 0.25).length, 0.25)

    def test_rejects_invalid_numbers(self):
        for midi_number in [-1, 128, 48.0, '48', None, True]:
            with self.subTest(midi_number=midi_number):
                with self.assertRaises(ValueError):
                    Note.from_midi_number(midi_number)


class TestRoundTrip(ImporterTestCase):

    def test_notes_keep_their_pitch_and_length(self):
        clip = self.round_trip(Clip(notes=[C4, D4]))
        self.assertEqual(clip.notes, [C4, D4])
        self.assertIsNone(clip.length)

    def test_rests_come_back(self):
        clip = self.round_trip(Clip(notes=[Rest(0.25), C4, Rest(0.5), D4]))
        self.assertEqual(clip.notes, [Rest(0.25), C4, Rest(0.5), D4])

    def test_chords_come_back(self):
        chord = Chord([C4, Note('E', 4, 0.25), Note('G', 4, 0.25)])
        self.assertEqual(self.round_trip(Clip(notes=[chord, D4])).notes, [chord, D4])

    def test_chords_with_mixed_lengths_come_back(self):
        chord = Chord([Note('C', 4, 0.5), Note('G', 4, 0.25)])
        self.assertEqual(self.round_trip(Clip(notes=[chord, D4])).notes, [chord, D4])

    def test_silence_at_the_end_becomes_a_set_length(self):
        clip = self.round_trip(Clip(notes=[C4], length=1))
        self.assertEqual(clip.notes, [C4])
        self.assertEqual(clip.length, 1)

    def test_rest_at_the_end_becomes_a_set_length(self):
        clip = self.round_trip(Clip(notes=[C4, Rest(0.25)]))
        self.assertEqual(clip.notes, [C4])
        self.assertEqual(clip.length, 0.5)

    def test_triplets_stay_exact(self):
        triplet = Fraction(1, 12)
        notes = [Note('C', 4, triplet), Note('D', 4, triplet), Note('E', 4, triplet)]
        self.assertEqual(self.round_trip(Clip(notes=notes)).notes, notes)

    def test_same_pitch_can_repeat(self):
        self.assertEqual(self.round_trip(Clip(notes=[C4, C4])).notes, [C4, C4])

    def test_empty_clip_comes_back_empty(self):
        clip = self.round_trip(Clip())
        self.assertEqual(clip.notes, [])
        self.assertIsNone(clip.length)

    def test_silent_clip_keeps_its_length(self):
        clip = self.round_trip(Clip(length=1))
        self.assertEqual(clip.notes, [])
        self.assertEqual(clip.length, 1)

    def test_spellings_come_back_as_sharps(self):
        clip = self.round_trip(Clip(notes=[Note('Db', 4, 0.25)]))
        self.assertEqual(clip.notes[0], Note('C#', 4, 0.25))
        self.assertEqual(clip.notes[0].name, 'C#')

    def test_loaded_clips_render_to_the_same_messages(self):
        song = Song()
        track = song.add_track(Track())
        scene = song.add_scene(Scene(tempo=90))
        chord = Chord([Note('C', 4, 0.5), Note('G', 4, 0.25)])
        song.set_clip(scene, track, Clip(notes=[Rest(0.25), C4, chord, D4], length=2))
        self.write_song(song)
        with tempfile.TemporaryDirectory() as other:
            ClipTree(other, self.load()).render()
            self.assertEqual(
                mido.MidiFile(os.path.join(other, '001-001.mid')).tracks[0],
                mido.MidiFile(self.path('001-001.mid')).tracks[0],
            )


class TestSongLayout(ImporterTestCase):

    def test_places_clips_by_scene_and_track(self):
        song = Song()
        tracks = [song.add_track(Track()) for _ in range(2)]
        scenes = [song.add_scene(Scene()) for _ in range(2)]
        song.set_clip(scenes[0], tracks[1], Clip(notes=[C4]))
        song.set_clip(scenes[1], tracks[0], Clip(notes=[D4]))
        self.write_song(song)

        loaded = self.load()
        self.assertEqual(len(loaded.scenes), 2)
        self.assertEqual(len(loaded.tracks), 2)
        self.assertIsNone(loaded.get_clip(loaded.scenes[0], loaded.tracks[0]))
        self.assertEqual(loaded.get_clip(loaded.scenes[0], loaded.tracks[1]).notes, [C4])
        self.assertEqual(loaded.get_clip(loaded.scenes[1], loaded.tracks[0]).notes, [D4])
        self.assertIsNone(loaded.get_clip(loaded.scenes[1], loaded.tracks[1]))

    def test_clip_name_comes_from_the_file_name(self):
        clip = self.round_trip(Clip('My Riff', notes=[C4]))
        self.assertEqual(clip.name, 'My_Riff')

    def test_clip_without_a_name_has_none(self):
        self.assertIsNone(self.round_trip(Clip(notes=[C4])).name)

    def test_tempo_goes_on_the_scene(self):
        song = Song()
        track = song.add_track(Track())
        scene = song.add_scene(Scene(tempo=90))
        song.set_clip(scene, track, Clip(notes=[C4]))
        self.write_song(song)
        loaded = self.load()
        self.assertEqual(loaded.scenes[0].tempo, 90)

    def test_gaps_in_the_numbering_are_not_kept(self):
        for filename in ['001-001.mid', '006-004.mid']:
            self.write_midi(filename, [])
        loaded = self.load()
        self.assertEqual([scene.id for scene in loaded.scenes], [0, 1])
        self.assertEqual([track.id for track in loaded.tracks], [0, 1])

    def test_scenes_sort_as_numbers(self):
        self.write_midi('003-001.mid', [mido.Message('note_on', note=48), mido.Message('note_off', note=48, time=480)])
        self.write_midi('011-001.mid', [mido.Message('note_on', note=50), mido.Message('note_off', note=50, time=480)])
        loaded = self.load()
        self.assertEqual(
            [loaded.get_clip(scene, loaded.tracks[0]).notes[0].midi_number for scene in loaded.scenes],
            [48, 50],
        )

    def test_loads_file_names_with_and_without_padding(self):
        for filename in ['001-001.mid', '002-001.mid']:
            self.write_midi(filename, [])
        self.assertEqual(len(self.load().scenes), 2)

    def test_padded_and_unpadded_names_for_one_slot_are_rejected(self):
        for filename in ['001-001.mid', '1-1.mid']:
            self.write_midi(filename, [])
        with self.assertRaises(ValueError):
            self.load()

    def test_ignores_other_files(self):
        self.write_midi('001-001.mid', [])
        with open(self.path('notes.txt'), 'w') as file:
            file.write('keep me')
        self.write_midi('song.mid', [])
        self.assertEqual(len(self.load().scenes), 1)

    def test_empty_directory_gives_an_empty_song(self):
        loaded = self.load()
        self.assertEqual(loaded.scenes, [])
        self.assertEqual(loaded.tracks, [])

    def test_missing_directory_raises(self):
        with self.assertRaises(FileNotFoundError):
            ClipTreeImporter(self.path('missing')).load()

    def test_rejects_invalid_directories(self):
        for directory in ['', None, 1]:
            with self.subTest(directory=directory):
                with self.assertRaises(ValueError):
                    ClipTreeImporter(directory)

    def test_directory_can_be_edited_and_is_validated(self):
        importer = ClipTreeImporter('first')
        importer.directory = 'second'
        self.assertEqual(importer.directory, 'second')
        with self.assertRaises(ValueError):
            importer.directory = None
        self.assertEqual(importer.directory, 'second')

    def test_rejects_two_files_for_one_slot(self):
        self.write_midi('001-001-Old.mid', [])
        self.write_midi('001-001-New.mid', [])
        with self.assertRaises(ValueError):
            self.load()


class TestFilesFromElsewhere(ImporterTestCase):

    def clip_from(self, messages, **options):
        self.write_midi('001-001.mid', messages, **options)
        loaded = self.load()
        return loaded.get_clip(loaded.scenes[0], loaded.tracks[0])

    def test_note_on_with_no_velocity_ends_a_note(self):
        clip = self.clip_from([
            mido.Message('note_on', note=48, velocity=100),
            mido.Message('note_on', note=48, velocity=0, time=480),
        ])
        self.assertEqual(clip.notes, [C4])

    def test_other_resolutions_keep_the_same_lengths(self):
        clip = self.clip_from([
            mido.Message('note_on', note=48),
            mido.Message('note_off', note=48, time=96),
        ], ticks_per_beat=96)
        self.assertEqual(clip.notes, [C4])

    def test_file_without_a_tempo_leaves_the_scene_alone(self):
        self.write_midi('001-001.mid', [])
        self.assertIsNone(self.load().scenes[0].tempo)

    def test_rejects_overlapping_notes(self):
        with self.assertRaises(ValueError):
            self.clip_from([
                mido.Message('note_on', note=48),
                mido.Message('note_on', note=50, time=240),
                mido.Message('note_off', note=48, time=240),
                mido.Message('note_off', note=50, time=240),
            ])

    def test_rejects_notes_that_never_end(self):
        with self.assertRaises(ValueError):
            self.clip_from([mido.Message('note_on', note=48)])

    def test_rejects_notes_that_end_without_starting(self):
        with self.assertRaises(ValueError):
            self.clip_from([mido.Message('note_off', note=48)])

    def test_rejects_a_note_that_starts_again_before_ending(self):
        with self.assertRaises(ValueError):
            self.clip_from([
                mido.Message('note_on', note=48),
                mido.Message('note_on', note=48, time=240),
            ])


if __name__ == '__main__':
    unittest.main()
