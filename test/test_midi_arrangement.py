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

"""The MIDI file and the stems lay the scenes end to end, with every track the same length, and leave muted tracks out."""

import contextlib
import io
import os
import tempfile
import unittest

import mido

from llamatron.note import Note
from llamatron.renderers.midi_arrangement import (
    MSG_FILES_EXIST, MSG_OTHER_FILES, MULTI_TRACK_FILE, SINGLE_TRACK_FILE, SONG_FILE, STEM_FILE, MidiSong, MidiStems,
)
from llamatron.renderers.midi_messages import (
    CONTROL_CHANGE_MESSAGE, END_OF_TRACK_META, NOTE_OFF_MESSAGE, NOTE_ON_MESSAGE, TEMPO_META, TICKS_PER_BEAT,
)
from llamatron.clip_grid import Clip, ClipGrid, Control, Scene, Track

QUARTER = 0.25
C4 = Note('C', 4, QUARTER)
D4 = Note('D', 4, QUARTER)
E4 = Note('E', 4, QUARTER)
G4 = Note('G', 4, QUARTER)
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
# Stems and the song's tracks count from the first track; the tempo track comes first in the song file.
FIRST_STEM = 1
TEMPO_TRACK = 0
FIRST_SOUNDING_TRACK = 1


def beat(number):
    return number * TICKS_PER_BEAT


def on(note, at):
    return (NOTE_ON_MESSAGE, note, beat(at))


def off(note, at):
    return (NOTE_OFF_MESSAGE, note, beat(at))


def tempo(bpm, at):
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


def render(writer):
    """Render and return what was printed."""
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        writer.render()
    return output.getvalue()


class ArrangementTestCase(unittest.TestCase):
    """A grid where the lead plays nothing in the first scene, the second scene has its own tempo, and one track is muted."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = os.path.join(temporary.name, SONG_NAME)
        self.grid = ClipGrid(tempo=SONG_TEMPO)
        self.bass = self.grid.add_track(Track(BASS))
        self.lead = self.grid.add_track(Track(LEAD))
        self.silent = self.grid.add_track(Track(SILENT, mute=True))
        self.first = self.grid.add_scene(Scene())
        self.second = self.grid.add_scene(Scene(tempo=SECOND_SCENE_TEMPO))
        self.grid.set_clip(self.first, self.bass, Clip(notes=[C4, D4]))
        self.grid.set_clip(self.first, self.silent, Clip(notes=[E4]))
        self.grid.set_clip(self.second, self.bass, Clip(notes=[E4]))
        self.grid.set_clip(self.second, self.lead, Clip(
            notes=[G4, G4, G4, G4], controls=[Control(MOD_TIME, MOD_WHEEL, MOD_VALUE, NO_SLIDE)],
        ))

    def path(self, filename):
        return os.path.join(self.directory, filename)

    def stem_name(self, number, track):
        return STEM_FILE.format(name=SONG_NAME, number=number, track=track)

    def song_file(self):
        render(MidiSong(self.directory, self.grid))
        return mido.MidiFile(self.path(SONG_FILE.format(name=SONG_NAME)))

    def stems(self):
        """Render the stems and return them in track order, as mido files."""
        render(MidiStems(self.directory, self.grid))
        names = [self.stem_name(FIRST_STEM, BASS), self.stem_name(FIRST_STEM + 1, LEAD)]
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

    def test_the_tempo_track_changes_tempo_where_the_second_scene_starts(self):
        midi = self.song_file()
        self.assertEqual(read_track(midi.tracks[TEMPO_TRACK]), [
            tempo(SONG_TEMPO, 0), tempo(SECOND_SCENE_TEMPO, FIRST_SCENE_BEATS), end(SONG_BEATS),
        ])

    def test_a_track_silent_in_the_first_scene_is_padded_so_that_it_lines_up(self):
        midi = self.song_file()
        self.assertEqual(read_track(midi.tracks[FIRST_SOUNDING_TRACK + 1]), [
            on(G4.midi_number, 2), off(G4.midi_number, 3),
            on(G4.midi_number, 3), off(G4.midi_number, 4),
            on(G4.midi_number, 4), off(G4.midi_number, 5),
            on(G4.midi_number, 5), off(G4.midi_number, 6),
            end(SONG_BEATS),
        ])

    def test_clips_follow_one_another_at_their_scenes_starts(self):
        midi = self.song_file()
        self.assertEqual(read_track(midi.tracks[FIRST_SOUNDING_TRACK]), [
            on(C4.midi_number, 0), off(C4.midi_number, 1), on(D4.midi_number, 1), off(D4.midi_number, 2),
            on(E4.midi_number, 2), off(E4.midi_number, 3),
            end(SONG_BEATS),
        ])

    def test_cc_values_move_with_their_clip(self):
        midi = self.song_file()
        self.assertEqual(control_changes(midi.tracks[FIRST_SOUNDING_TRACK + 1]), [(MOD_WHEEL, MOD_VALUE, beat(MOD_BEAT))])

    def test_a_tempo_that_does_not_change_is_set_only_once(self):
        grid = ClipGrid(tempo=SONG_TEMPO)
        track = grid.add_track(Track(BASS))
        for _ in range(2):
            grid.set_clip(grid.add_scene(Scene()), track, Clip(notes=[C4]))
        render(MidiSong(self.directory, grid))
        midi = mido.MidiFile(self.path(SONG_FILE.format(name=SONG_NAME)))
        self.assertEqual(read_track(midi.tracks[TEMPO_TRACK]), [tempo(SONG_TEMPO, 0), end(2)])

    def test_an_existing_file_stops_the_render_with_a_warning(self):
        os.makedirs(self.directory)
        path = self.path(SONG_FILE.format(name=SONG_NAME))
        with open(path, 'w') as file:
            file.write(AN_EXISTING_FILE)
        printed = render(MidiSong(self.directory, self.grid))
        self.assertEqual(printed.strip(), MSG_FILES_EXIST.format(directory=self.directory, files=os.path.basename(path)))
        with open(path) as file:
            self.assertEqual(file.read(), AN_EXISTING_FILE)

    def test_other_files_are_kept_and_mentioned(self):
        os.makedirs(self.directory)
        with open(self.path(AN_EXISTING_FILE), 'w') as file:
            file.write(AN_EXISTING_FILE)
        printed = render(MidiSong(self.directory, self.grid))
        self.assertEqual(printed.strip(), MSG_OTHER_FILES.format(directory=self.directory, count=1, files=AN_EXISTING_FILE))
        self.assertEqual(sorted(os.listdir(self.directory)), [AN_EXISTING_FILE, SONG_FILE.format(name=SONG_NAME)])

    def test_bad_arguments_are_refused(self):
        with self.assertRaises(ValueError):
            MidiSong(None, self.grid)
        with self.assertRaises(ValueError):
            MidiSong(self.directory, None)


class TestMidiStems(ArrangementTestCase):

    def test_one_file_per_unmuted_track_named_in_track_order(self):
        render(MidiStems(self.directory, self.grid))
        self.assertEqual(sorted(os.listdir(self.directory)), [self.stem_name(FIRST_STEM, BASS), self.stem_name(FIRST_STEM + 1, LEAD)])

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
            self.assertEqual(tempos, [tempo(SONG_TEMPO, 0), tempo(SECOND_SCENE_TEMPO, FIRST_SCENE_BEATS)])

    def test_stems_play_what_the_song_files_tracks_play(self):
        song = self.song_file()
        for stem, track in zip(self.stems(), song.tracks[FIRST_SOUNDING_TRACK:]):
            with self.subTest(track=track.name):
                notes = [event for event in read_track(stem.tracks[0]) if event[0] != TEMPO_META]
                self.assertEqual(notes, read_track(track))
                self.assertEqual(control_changes(stem.tracks[0]), control_changes(track))

    def test_an_existing_stem_stops_the_render_with_a_warning(self):
        os.makedirs(self.directory)
        name = self.stem_name(FIRST_STEM + 1, LEAD)
        with open(self.path(name), 'w') as file:
            file.write(AN_EXISTING_FILE)
        printed = render(MidiStems(self.directory, self.grid))
        self.assertEqual(printed.strip(), MSG_FILES_EXIST.format(directory=self.directory, files=name))
        self.assertEqual(os.listdir(self.directory), [name])


if __name__ == '__main__':
    unittest.main()
