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

"""The llamatron command: exporting a set's songs to each kind of output, and the options it refuses."""

import contextlib
import glob
import gzip
import io
import os
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest import mock

import mido
import yaml

from llamatron.visualizers.modes import MODES
from llamatron.cli import main
from llamatron.exporters.midi_arrangement import MULTI_TRACK_FILE, SONG_FILE, STEM_FILE
from llamatron.exporters.exports import EXPORTERS, export_name
from llamatron.exporters.exports import ExportKind
from llamatron.composition.file_format import Row
from llamatron.composition.setlist import Setlist
from llamatron.composition.setlist_writer import dump_setlist
from llamatron.composition.song_file_error import SongFileError
from llamatron.strings.cli import MSG_CLI_CHANGED, MSG_CLI_WOULD_CHANGE
from llamatron.strings.errors import ERR_LAUNCH_NEEDS_SET, ERR_NEEDS_FORCE, ERR_PRINTED, ERR_RECORDING_SONG_LOOPS
from rendering import as_setlist, dump_song_data
from song_testing import BASIC, LEAD, lead_data

SIXTEENTH = '1/16'
NOTHING = ''
# The two sets with values out of range, made for the tests.
SAMPLE_SETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sample_sets')
OUT_OF_RANGE = 'out_of_range.yml'
OUT_OF_RANGE_AND_BROKEN = 'out_of_range_and_broken.yml'
KICK = 'kick'
A = 'a'
HIT = 'hit'
SEED_A = '5'
SEED_B = '6'
READ_BYTES = 'rb'
# The kinds exported here: all but the WAV, which plays the song through FluidSynth, a program this computer may not have, and which test_wave_fluidsynth.py tests with a stand-in.
EXPORTED_HERE = [kind for kind in EXPORTERS if kind != ExportKind.WAV]
OUT = 'out'
VALID_YAML = 'valid YAML'
WRITE_TEXT = 'w'
LIVESET = 'LiveSet'
ONE = 'one'
VALUE = 'Value'
WB = 'wb'
KEEP_ME = 'keep me'
MIDICLIP = 'MidiClip'
MIDITRACK = 'MidiTrack'
SCENES = 'Scenes'
NAME = 'Name'
TRACKS = 'Tracks'
# The set file's name, which names its one song too, so its exports are named tune_tune.
SONG_NAME = 'tune'
EXPORT = export_name(setlist=SONG_NAME, song=SONG_NAME)
LIVE_SET = EXPORT + '.als'
CLIP_FILES = [EXPORT + '_clip_s_001-one-t_001-lead.mid', EXPORT + '_clip_s_001-one-t_002-kick.mid']
SECOND_SONG = 'second'
# The keyword the tracker's app takes its song by.
DOCUMENT_ARGUMENT = 'document'
LAUNCH_ARGUMENT = 'launch'
CURSOR_ON_OPEN_ARGUMENT = 'cursor_on_open'
# The basic song's lead clip, as its text has it, and the same clip looping, which makes a scene whose every clip loops.
LEAD_CLIP = 'lead: { pattern: a }'
LOOPING_LEAD_CLIP = 'lead: { pattern: a, loop: true }'
# The place in the recording refusal that names the scenes, after which the text is checked no further.
RECORDING_LOOPS_PLACE = '{scenes}'


class TestCli(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.parent = temporary.name
        self.song = os.path.join(self.parent, 'tune.yml')
        with open(self.song, WRITE_TEXT) as file:
            file.write(BASIC)
        self.out = os.path.join(self.parent, OUT)

    def run_cli(self, *arguments):
        if '--to' not in arguments:
            arguments = ('--to', ExportKind.ABLETON, *arguments)
        return self.run_exactly(self.song, '--out', self.out, *arguments)

    def run_exactly(self, *arguments):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                code = main(argv=list(arguments))
            except SystemExit as stop:
                code = stop.code
        return code, stdout.getvalue(), stderr.getvalue()

    def test_without_to_it_opens_the_tracker(self):
        # The tracker's main runs for real, with only the app's run patched out, so that the call into it is checked.
        with mock.patch('llamatron.tui.app.LlamatronApp') as app:
            self.assertEqual(self.run_exactly()[0], 0)
            app.return_value.run.assert_called_once_with()
            self.assertIsNone(app.call_args.kwargs[DOCUMENT_ARGUMENT])
            self.assertEqual(self.run_exactly(self.song)[0], 0)
            self.assertEqual(app.call_args.kwargs[DOCUMENT_ARGUMENT].get_path(), self.song)
        self.assertFalse(os.path.exists(self.out))

    def out_of_range_set(self, name):
        """Put one of the sample sets, which hold values out of range, where the set file is, and return what the file holds."""
        shutil.copy(os.path.join(SAMPLE_SETS, name), self.song)
        with open(self.song, READ_BYTES) as file:
            return file.read()

    def written_files(self):
        return os.listdir(self.out) if os.path.exists(self.out) else []

    def test_a_set_with_values_out_of_range_is_not_exported_and_the_error_says_to_pass_force(self):
        before = self.out_of_range_set(OUT_OF_RANGE)
        _, corrections = Setlist.read_file_corrected(self.song)
        for kind in EXPORTED_HERE:
            with self.subTest(kind=kind):
                code, stdout, stderr = self.run_cli('--to', kind)
                self.assertEqual(code, 1)
                self.assertEqual(stdout, NOTHING)
                lines = stderr.splitlines()
                self.assertEqual(lines[:-1], [MSG_CLI_WOULD_CHANGE.format(change=correction.described()) for correction in corrections])
                self.assertEqual(lines[-1], ERR_PRINTED.format(problem=ERR_NEEDS_FORCE.format(path=self.song)))
                self.assertEqual(self.written_files(), [])
        self.assertEqual(self.out_of_range_set(OUT_OF_RANGE), before)

    def test_force_exports_it_with_each_value_changed_says_what_changed_and_leaves_the_file_alone(self):
        before = self.out_of_range_set(OUT_OF_RANGE)
        _, corrections = Setlist.read_file_corrected(self.song)
        code, stdout, stderr = self.run_cli('--to', ExportKind.MIDI_FILE, '--force')
        self.assertEqual(code, 0)
        self.assertEqual(stderr.splitlines(), [MSG_CLI_CHANGED.format(change=correction.described()) for correction in corrections])
        self.assertTrue(self.written_files())
        for name in self.written_files():
            mido.MidiFile(os.path.join(self.out, name))
        with open(self.song, READ_BYTES) as file:
            self.assertEqual(file.read(), before)

    def test_force_exports_every_kind(self):
        self.out_of_range_set(OUT_OF_RANGE)
        for kind in EXPORTED_HERE:
            with self.subTest(kind=kind):
                code, _, _ = self.run_cli('--to', kind, '--force', '--replace')
                self.assertEqual(code, 0)
        self.assertTrue(self.written_files())

    def test_force_does_not_export_a_set_with_a_problem_nothing_can_correct(self):
        self.out_of_range_set(OUT_OF_RANGE_AND_BROKEN)
        with self.assertRaises(SongFileError) as refused:
            Setlist.read_file_corrected(self.song)
        for arguments in [[], ['--force']]:
            with self.subTest(arguments=arguments):
                code, _, stderr = self.run_cli(*arguments)
                self.assertEqual(code, 1)
                self.assertEqual(stderr.splitlines(), [ERR_PRINTED.format(problem=refused.exception)])
                self.assertEqual(self.written_files(), [])

    def test_force_changes_nothing_about_a_set_with_nothing_wrong(self):
        code, _, stderr = self.run_cli('--to', ExportKind.MIDI_FILE, '--force')
        self.assertEqual(code, 0)
        self.assertEqual(stderr, NOTHING)
        self.assertTrue(self.written_files())

    def test_export_options_need_to(self):
        for arguments in [['--out', self.out], ['--replace'], ['--template', self.song], ['--seed', '0'], ['--force']]:
            with self.subTest(arguments=arguments), mock.patch('llamatron.tui.app.main') as tracker:
                code, _, stderr = self.run_exactly(self.song, *arguments)
                self.assertEqual(code, 2)
                self.assertIn('only works with --to', stderr)
                tracker.assert_not_called()

    def test_seed_renders_the_same_take_every_time_and_another_seed_another(self):
        with open(self.song, WRITE_TEXT) as file:
            file.write(dump_song_data(lead_data(*[[1, SIXTEENTH]] * 100, rows={Row.PROBABILITY: [50] * 100})))
        takes = {}
        for seed in [SEED_A, SEED_A, SEED_B]:
            out = os.path.join(self.parent, OUT + seed)
            self.assertEqual(self.run_exactly(self.song, '--to', ExportKind.CLIP_TREE, '--out', out, '--seed', seed)[0], 0)
            takes.setdefault(seed, []).append([open(path, READ_BYTES).read() for path in sorted(glob.glob(os.path.join(out, '*.mid')))])
        self.assertEqual(takes[SEED_A][0], takes[SEED_A][1])
        self.assertNotEqual(takes[SEED_A][0], takes[SEED_B][0])

    def test_the_launch_options_reach_the_tracker_and_need_a_set(self):
        with mock.patch('llamatron.tui.app.LlamatronApp') as app:
            self.assertEqual(self.run_exactly(self.song, '--autoplay-quit-when-finished', '--launch-for-recording', '--max-seconds', '30')[0], 0)
            launch = app.call_args.kwargs[LAUNCH_ARGUMENT]
            self.assertTrue(launch.autoplay and launch.quit_when_finished and launch.for_recording)
            self.assertEqual(launch.max_seconds, 30)
        with mock.patch('llamatron.tui.app.LlamatronApp') as app:
            self.assertEqual(self.run_exactly(self.song, '--visualizer', MODES[0].OPTION)[0], 0)
            launch = app.call_args.kwargs[LAUNCH_ARGUMENT]
            self.assertEqual(launch.visualizer, MODES[0].OPTION)
            self.assertTrue(launch.autoplay)
        for arguments in [['--autoplay'], ['--autoplay-quit-when-finished'], ['--launch-for-recording'], ['--max-seconds', '30'], ['--visualizer', MODES[0].OPTION]]:
            with self.subTest(arguments=arguments), mock.patch('llamatron.tui.app.main') as tracker:
                code, _, stderr = self.run_exactly(*arguments)
                self.assertEqual(code, 2)
                self.assertIn(ERR_LAUNCH_NEEDS_SET, stderr)
                tracker.assert_not_called()
            with self.subTest(arguments=arguments), mock.patch('llamatron.tui.app.main') as tracker:
                code, _, stderr = self.run_exactly(self.song, '--to', *arguments)
                self.assertEqual(code, 2)
                self.assertIn(arguments[0], stderr)
                tracker.assert_not_called()

    def test_with_no_set_named_the_main_screens_cursor_starts_on_open(self):
        with mock.patch('llamatron.tui.app.LlamatronApp') as app:
            self.assertEqual(self.run_exactly()[0], 0)
            self.assertTrue(app.call_args.kwargs[CURSOR_ON_OPEN_ARGUMENT])
        with mock.patch('llamatron.tui.app.LlamatronApp') as app:
            self.assertEqual(self.run_exactly(self.song)[0], 0)
            self.assertFalse(app.call_args.kwargs[CURSOR_ON_OPEN_ARGUMENT])

    def test_launched_for_recording_a_song_with_a_scene_whose_every_clip_loops_is_refused(self):
        # The basic song's kick loops beside a lead that ends, which plays to its end; with the lead looping too the scene would never end.
        with open(self.song, WRITE_TEXT) as file:
            file.write(BASIC.replace(LEAD_CLIP, LOOPING_LEAD_CLIP))
        with mock.patch('llamatron.tui.app.LlamatronApp') as app:
            code, _, stderr = self.run_exactly(self.song, '--launch-for-recording')
            self.assertEqual(code, 1)
            self.assertIn(ERR_RECORDING_SONG_LOOPS.split(RECORDING_LOOPS_PLACE)[0], stderr)
            app.assert_not_called()
            self.assertEqual(self.run_exactly(self.song, '--autoplay')[0], 0)

    def test_to_needs_a_set(self):
        code, _, stderr = self.run_exactly('--to', ExportKind.ABLETON)
        self.assertEqual(code, 2)
        self.assertIn('--to needs a set file', stderr)

    def two_songs(self):
        """Write the set with a second song, a copy of the first, and return the two songs' names."""
        data = as_setlist(yaml.safe_load(BASIC))
        first = next(iter(data['songs']))
        data['songs'][SECOND_SONG] = dict(data['songs'][first])
        with open(self.song, WRITE_TEXT) as file:
            file.write(dump_setlist(data))
        return [first, SECOND_SONG]

    def clip_files(self, song):
        """Return the clip files a song of the set exports, named after the set and the song."""
        return [name.replace(EXPORT, export_name(setlist=SONG_NAME, song=song)) for name in CLIP_FILES]

    def test_every_song_of_a_set_is_named_after_the_set_and_the_song(self):
        names = self.two_songs()
        code, stdout, _ = self.run_cli('--to', ExportKind.CLIP_TREE)
        self.assertEqual(code, 0)
        self.assertEqual(sorted(os.listdir(self.out)), sorted(file for name in names for file in self.clip_files(name)))
        for name in names:
            self.assertIn(f'for song ({name})', stdout)

    def test_song_exports_one_song_only(self):
        self.two_songs()
        code, _, _ = self.run_cli('--to', ExportKind.CLIP_TREE, '--song', SECOND_SONG)
        self.assertEqual(code, 0)
        self.assertEqual(sorted(os.listdir(self.out)), self.clip_files(SECOND_SONG))

    def test_song_needs_to_and_a_song_the_set_has(self):
        with mock.patch('llamatron.tui.app.main') as tracker:
            code, _, stderr = self.run_exactly(self.song, '--song', SONG_NAME)
        self.assertEqual(code, 2)
        self.assertIn('only works with --to', stderr)
        tracker.assert_not_called()
        code, _, stderr = self.run_cli('--song', 'nowhere')
        self.assertEqual(code, 1)
        self.assertIn('no song called (nowhere)', stderr)

    def test_without_out_the_output_goes_beside_the_set(self):
        self.assertEqual(self.run_exactly(self.song, '--to', ExportKind.CLIP_TREE)[0], 0)
        self.assertEqual(sorted(os.listdir(self.parent)), sorted(CLIP_FILES + [os.path.basename(self.song)]))

    def test_writes_an_ableton_set(self):
        self.assertEqual(self.run_cli()[0], 0)
        self.assertEqual(os.listdir(self.out), [LIVE_SET])
        with gzip.open(os.path.join(self.out, LIVE_SET)) as file:
            live_set = ET.fromstring(file.read()).find(LIVESET)
        self.assertEqual(
            [t.find('Name/EffectiveName').get(VALUE) for t in live_set.find(TRACKS).findall(MIDITRACK)],
            [LEAD, KICK],
        )

    def test_live_clips_are_named_after_their_patterns_and_scenes_after_the_scene(self):
        self.run_cli()
        with gzip.open(os.path.join(self.out, LIVE_SET)) as file:
            live_set = ET.fromstring(file.read()).find(LIVESET)
        self.assertEqual([scene.find(NAME).get(VALUE) for scene in live_set.find(SCENES)], [ONE])
        clips = [clip.find(NAME).get(VALUE) for clip in live_set.find(TRACKS).iter(MIDICLIP)]
        # Each clip is in Session View and Arrangement View.
        self.assertEqual(sorted(set(clips)), [A, HIT])

    def test_writes_midi_files_numbered_from_1(self):
        self.run_cli('--to', ExportKind.CLIP_TREE)
        self.assertEqual(sorted(os.listdir(self.out)), CLIP_FILES)
        played = mido.MidiFile(os.path.join(self.out, CLIP_FILES[0]))
        self.assertEqual(played.tracks[0].name, os.path.splitext(CLIP_FILES[0])[0])

    def test_to_on_its_own_writes_an_ableton_set(self):
        code, _, _ = self.run_exactly(self.song, '--out', self.out, '--to')
        self.assertEqual(code, 0)
        self.assertEqual(os.listdir(self.out), [LIVE_SET])

    def test_to_midi_writes_one_file_with_a_tempo_track_and_a_track_per_track(self):
        self.run_cli('--to', ExportKind.MIDI_FILE)
        name = SONG_FILE.format(name=EXPORT)
        self.assertEqual(os.listdir(self.out), [name])
        midi = mido.MidiFile(os.path.join(self.out, name))
        self.assertEqual(midi.type, MULTI_TRACK_FILE)
        self.assertEqual([track.name for track in midi.tracks], [EXPORT, LEAD, KICK])

    def test_to_stems_writes_a_file_per_track_numbered_from_1(self):
        self.run_cli('--to', ExportKind.STEMS)
        expected = [STEM_FILE.format(name=EXPORT, number=1, track=LEAD), STEM_FILE.format(name=EXPORT, number=2, track=KICK)]
        self.assertEqual(sorted(os.listdir(self.out)), expected)

    def test_replacing_stems_keeps_a_clip_tree_in_the_same_folder(self):
        self.run_cli('--to', ExportKind.CLIP_TREE)
        self.run_cli('--to', ExportKind.STEMS)
        code, stdout, _ = self.run_cli('--to', ExportKind.STEMS, '--replace')
        self.assertEqual(code, 0)
        self.assertNotIn('warning: stopping', stdout)
        self.assertEqual(len(os.listdir(self.out)), 4)

    def test_stops_with_a_warning_if_the_output_exists(self):
        self.run_cli()
        code, stdout, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn('warning: stopping', stdout)

    def test_replace_regenerates_a_set(self):
        self.run_cli()
        with open(os.path.join(self.out, LIVE_SET), WB) as file:
            file.write(b'old')
        self.assertEqual(self.run_cli('--replace')[0], 0)
        with open(os.path.join(self.out, LIVE_SET), READ_BYTES) as file:
            self.assertNotEqual(file.read(), b'old')

    def test_replace_keeps_everything_else(self):
        os.makedirs(self.out)
        keep = os.path.join(self.out, 'notes.txt')
        with open(keep, WRITE_TEXT) as file:
            file.write(KEEP_ME)
        self.run_cli('--to', ExportKind.CLIP_TREE, '--replace')
        self.run_cli('--to', ExportKind.CLIP_TREE, '--replace')
        self.assertTrue(os.path.exists(keep))
        self.assertEqual(sorted(os.listdir(self.out)), ['notes.txt'] + CLIP_FILES)

    def test_errors_are_explained_without_a_traceback(self):
        with open(self.song, WRITE_TEXT) as file:
            file.write('tempo: 120\n')
        code, _, stderr = self.run_cli()
        self.assertEqual(code, 1)
        self.assertIn('error:', stderr)

    def test_bad_yaml_is_explained(self):
        with open(self.song, WRITE_TEXT) as file:
            file.write('tempo: [\n')
        code, _, stderr = self.run_cli()
        self.assertEqual(code, 1)
        self.assertIn(VALID_YAML, stderr)
