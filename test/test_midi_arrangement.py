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

"""The MIDI file and the stems lay the scenes end to end, with every track the same length, and leave muted tracks out."""

import contextlib
import io
import os
import tempfile
import unittest

import mido

from llamatron.music.note import Note
from llamatron.music.time_signature import TimeSignature
from llamatron.exporters.midi_arrangement import (
    MidiSong,
    MidiStems,
    MULTI_TRACK_FILE,
    SINGLE_TRACK_FILE,
    SONG_FILE,
    STEM_FILE,
)
from llamatron.exporters.midi_messages import (
    CONTROL_CHANGE_MESSAGE,
    END_OF_TRACK_META,
    TIME_SIGNATURE_META,
    NOTE_OFF_MESSAGE,
    NOTE_ON_MESSAGE,
    TEMPO_META,
    TICKS_PER_BEAT,
)
from llamatron.grid.clip import Clip
from llamatron.grid.clip_grid import ClipGrid
from llamatron.grid.control import Control
from llamatron.grid.clip_row import ClipRow
from llamatron.grid.clip_column import ClipColumn
from llamatron.strings.errors import ERR_FILES_EXIST

QUARTER = 0.25
C4 = Note(name='C', octave_number=4, length=QUARTER)
D4 = Note(name='D', octave_number=4, length=QUARTER)
E4 = Note(name='E', octave_number=4, length=QUARTER)
G4 = Note(name='G', octave_number=4, length=QUARTER)
# The song in the tests: two scenes, and three tracks, one of them muted.
SONG_NAME = 'tune'
BASS = 'bass'
LEAD = 'lead'
SILENT = 'SILENT grab source'
SONG_TEMPO = 120
SECOND_SCENE_TEMPO = 90
# The first scene lasts two beats (the bass's two quarters), the second four (the lead's), so the song lasts six.
FIRST_SCENE_BEATS = 2
SONG_BEATS = 6
# A CC value the lead sends halfway through its clip in the second scene.
MOD_WHEEL = 1
MOD_VALUE = 64
MOD_TIME = 0.5
MOD_BEAT = FIRST_SCENE_BEATS + 2
NO_SLIDE = False
# How the test reads a track: (type, number, tick) for notes, (set_tempo, bpm, tick) for tempos and (end, None, tick) at the end.
END = 'end'
NO_NUMBER = None
AN_EXISTING_FILE = 'notes.txt'
# A name given to the exporters in place of the directory's, as the tracker and the command line do.
GIVEN_NAME = 'my_set_tune'
# Stems and the song's tracks count from the first track; the tempo track comes first in the song file.
FIRST_STEM = 1
# The time signature the tests set, and its metronome in MIDI clocks: 24 a quarter note, so 36 a dotted quarter.
COMPOUND_DUPLE = '6/8'
DOTTED_QUARTER_CLOCKS = 36
TEMPO_TRACK = 0
FIRST_SOUNDING_TRACK = 1

# Names the tests give to their own things, and other values they use.
WRITE_TEXT = 'w'


def beat(number):
    return number * TICKS_PER_BEAT


def on(*, note, at):
    return (NOTE_ON_MESSAGE, note, beat(at))


def off(*, note, at):
    return (NOTE_OFF_MESSAGE, note, beat(at))


def tempo(*, bpm, at):
    return (TEMPO_META, bpm, beat(at))


def end(at):
    return (END, NO_NUMBER, beat(at))


def read_track(track):
    """Return a mido track's notes, tempo changes and end as (type, number, tick) tuples, with ticks from the start."""
    result = []
    tick = 0
    for message in track:
        tick += message.time
        if message.type in (NOTE_ON_MESSAGE, NOTE_OFF_MESSAGE):
            result.append((message.type, message.note, tick))
        elif message.type == TEMPO_META:
            result.append((TEMPO_META, round(mido.tempo2bpm(message.tempo)), tick))
        elif message.type == END_OF_TRACK_META:
            result.append((END, NO_NUMBER, tick))
    return result


def control_changes(track):
    """Return a mido track's CC messages as (number, value, tick)."""
    result = []
    tick = 0
    for message in track:
        tick += message.time
        if message.type == CONTROL_CHANGE_MESSAGE:
            result.append((message.control, message.value, tick))
    return result


def export(exporter):
    """Export and return what was printed."""
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exporter.export()
    return output.getvalue()


class ArrangementTestCase(unittest.TestCase):
    """A grid where the lead plays nothing in the first scene, the second scene has its own tempo, and one track is muted."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = os.path.join(temporary.name, SONG_NAME)
        self.grid = ClipGrid(tempo=SONG_TEMPO)
        self.bass = self.grid.add_column(ClipColumn(name=BASS))
        self.lead = self.grid.add_column(ClipColumn(name=LEAD))
        self.silent = self.grid.add_column(ClipColumn(name=SILENT, mute=True))
        self.first = self.grid.add_row(ClipRow())
        self.second = self.grid.add_row(ClipRow(tempo=SECOND_SCENE_TEMPO))
        self.grid.set_clip(row=self.first, column=self.bass, clip=Clip(notes=[C4, D4]))
        self.grid.set_clip(row=self.first, column=self.silent, clip=Clip(notes=[E4]))
        self.grid.set_clip(row=self.second, column=self.bass, clip=Clip(notes=[E4]))
        self.grid.set_clip(row=self.second, column=self.lead, clip=Clip(
            notes=[G4, G4, G4, G4], controls=[Control(time=MOD_TIME, number=MOD_WHEEL, value=MOD_VALUE, slide=NO_SLIDE)],
        ))

    def path(self, filename):
        return os.path.join(self.directory, filename)

    def stem_name(self, *, number, track):
        return STEM_FILE.format(name=SONG_NAME, number=number, track=track)

    def song_file(self):
        export(MidiSong(directory=self.directory, grid=self.grid))
        return mido.MidiFile(self.path(SONG_FILE.format(name=SONG_NAME)))

    def stems(self):
        """Export the stems and return them in track order, as mido files."""
        export(MidiStems(directory=self.directory, grid=self.grid))
        names = [self.stem_name(number=FIRST_STEM, track=BASS), self.stem_name(number=FIRST_STEM + 1, track=LEAD)]
        return [mido.MidiFile(self.path(name)) for name in names]


class TestMidiSong(ArrangementTestCase):

    def test_one_file_holds_a_tempo_track_and_a_track_per_unmuted_track(self):
        midi = self.song_file()
        self.assertEqual(midi.type, MULTI_TRACK_FILE)
        self.assertEqual([track.name for track in midi.tracks], [SONG_NAME, BASS, LEAD])

    def test_every_track_ends_at_the_end_of_the_song(self):
        for track in self.song_file().tracks:
            with self.subTest(track=track.name):
                self.assertEqual(read_track(track)[-1], end(SONG_BEATS))

    def test_every_file_starts_with_the_time_signature(self):
        self.grid.set_time_signature(TimeSignature.from_text(COMPOUND_DUPLE))
        tracks = [self.song_file().tracks[TEMPO_TRACK], *[stem.tracks[0] for stem in self.stems()]]
        for track in tracks:
            with self.subTest(track=track.name):
                signatures = [(message.numerator, message.denominator, message.clocks_per_click, message.time) for message in track if message.type == TIME_SIGNATURE_META]
                self.assertEqual(signatures, [(6, 8, DOTTED_QUARTER_CLOCKS, 0)])

    def test_the_tempo_track_changes_tempo_where_the_second_scene_starts(self):
        midi = self.song_file()
        self.assertEqual(read_track(midi.tracks[TEMPO_TRACK]), [
            tempo(bpm=SONG_TEMPO, at=0), tempo(bpm=SECOND_SCENE_TEMPO, at=FIRST_SCENE_BEATS), end(SONG_BEATS),
        ])

    def test_a_track_silent_in_the_first_scene_is_padded_so_that_it_lines_up(self):
        midi = self.song_file()
        self.assertEqual(read_track(midi.tracks[FIRST_SOUNDING_TRACK + 1]), [
            on(note=G4.get_midi_number(), at=2), off(note=G4.get_midi_number(), at=3),
            on(note=G4.get_midi_number(), at=3), off(note=G4.get_midi_number(), at=4),
            on(note=G4.get_midi_number(), at=4), off(note=G4.get_midi_number(), at=5),
            on(note=G4.get_midi_number(), at=5), off(note=G4.get_midi_number(), at=6),
            end(SONG_BEATS),
        ])

    def test_clips_follow_one_another_at_their_scenes_starts(self):
        midi = self.song_file()
        self.assertEqual(read_track(midi.tracks[FIRST_SOUNDING_TRACK]), [
            on(note=C4.get_midi_number(), at=0), off(note=C4.get_midi_number(), at=1), on(note=D4.get_midi_number(), at=1), off(note=D4.get_midi_number(), at=2),
            on(note=E4.get_midi_number(), at=2), off(note=E4.get_midi_number(), at=3),
            end(SONG_BEATS),
        ])

    def test_cc_values_move_with_their_clip(self):
        midi = self.song_file()
        self.assertEqual(control_changes(midi.tracks[FIRST_SOUNDING_TRACK + 1]), [(MOD_WHEEL, MOD_VALUE, beat(MOD_BEAT))])

    def test_a_tempo_that_does_not_change_is_set_only_once(self):
        grid = ClipGrid(tempo=SONG_TEMPO)
        track = grid.add_column(ClipColumn(name=BASS))
        for _ in range(2):
            grid.set_clip(row=grid.add_row(ClipRow()), column=track, clip=Clip(notes=[C4]))
        export(MidiSong(directory=self.directory, grid=grid))
        midi = mido.MidiFile(self.path(SONG_FILE.format(name=SONG_NAME)))
        self.assertEqual(read_track(midi.tracks[TEMPO_TRACK]), [tempo(bpm=SONG_TEMPO, at=0), end(2)])

    def test_an_existing_file_stops_the_export_with_a_warning(self):
        os.makedirs(self.directory)
        path = self.path(SONG_FILE.format(name=SONG_NAME))
        with open(path, WRITE_TEXT) as file:
            file.write(AN_EXISTING_FILE)
        printed = export(MidiSong(directory=self.directory, grid=self.grid))
        self.assertEqual(printed.strip(), ERR_FILES_EXIST.format(directory=self.directory, files=os.path.basename(path)))
        with open(path) as file:
            self.assertEqual(file.read(), AN_EXISTING_FILE)

    def test_other_files_are_kept_without_a_word(self):
        os.makedirs(self.directory)
        with open(self.path(AN_EXISTING_FILE), WRITE_TEXT) as file:
            file.write(AN_EXISTING_FILE)
        printed = export(MidiSong(directory=self.directory, grid=self.grid))
        self.assertEqual(printed, '')
        self.assertEqual(sorted(os.listdir(self.directory)), [AN_EXISTING_FILE, SONG_FILE.format(name=SONG_NAME)])

    def test_the_name_is_the_directory_unless_given(self):
        export(MidiSong(directory=self.directory, grid=self.grid, name=GIVEN_NAME))
        export(MidiStems(directory=self.directory, grid=self.grid, name=GIVEN_NAME))
        self.assertEqual(sorted(os.listdir(self.directory)), [
            SONG_FILE.format(name=GIVEN_NAME),
            STEM_FILE.format(name=GIVEN_NAME, number=FIRST_STEM, track=BASS),
            STEM_FILE.format(name=GIVEN_NAME, number=FIRST_STEM + 1, track=LEAD),
        ])

    def test_bad_arguments_are_refused(self):
        with self.assertRaises(ValueError):
            MidiSong(directory=None, grid=self.grid)
        with self.assertRaises(ValueError):
            MidiSong(directory=self.directory, grid=None)


class TestMidiStems(ArrangementTestCase):

    def test_one_file_per_unmuted_track_named_in_track_order(self):
        export(MidiStems(directory=self.directory, grid=self.grid))
        self.assertEqual(sorted(os.listdir(self.directory)), [self.stem_name(number=FIRST_STEM, track=BASS), self.stem_name(number=FIRST_STEM + 1, track=LEAD)])

    def test_every_stem_is_a_single_track_file_the_length_of_the_song(self):
        for midi, name in zip(self.stems(), [BASS, LEAD]):
            with self.subTest(track=name):
                self.assertEqual(midi.type, SINGLE_TRACK_FILE)
                self.assertEqual(len(midi.tracks), 1)
                self.assertEqual(midi.tracks[0].name, name)
                self.assertEqual(read_track(midi.tracks[0])[-1], end(SONG_BEATS))

    def test_every_stem_carries_the_tempo_changes(self):
        for midi in self.stems():
            tempos = [event for event in read_track(midi.tracks[0]) if event[0] == TEMPO_META]
            self.assertEqual(tempos, [tempo(bpm=SONG_TEMPO, at=0), tempo(bpm=SECOND_SCENE_TEMPO, at=FIRST_SCENE_BEATS)])

    def test_stems_play_what_the_song_files_tracks_play(self):
        song = self.song_file()
        for stem, track in zip(self.stems(), song.tracks[FIRST_SOUNDING_TRACK:]):
            with self.subTest(track=track.name):
                notes = [event for event in read_track(stem.tracks[0]) if event[0] != TEMPO_META]
                self.assertEqual(notes, read_track(track))
                self.assertEqual(control_changes(stem.tracks[0]), control_changes(track))

    def test_an_existing_stem_stops_the_export_with_a_warning(self):
        os.makedirs(self.directory)
        name = self.stem_name(number=FIRST_STEM + 1, track=LEAD)
        with open(self.path(name), WRITE_TEXT) as file:
            file.write(AN_EXISTING_FILE)
        printed = export(MidiStems(directory=self.directory, grid=self.grid))
        self.assertEqual(printed.strip(), ERR_FILES_EXIST.format(directory=self.directory, files=name))
        self.assertEqual(os.listdir(self.directory), [name])


if __name__ == '__main__':
    unittest.main()
