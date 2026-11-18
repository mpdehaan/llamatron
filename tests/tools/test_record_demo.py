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
"""Tests of the demo recorder's parts that need no Mac, no port and no screen: how tracks are assigned to the recorder's instruments, how a driver is found, how long a take runs, and what the tool refuses."""

import contextlib
import importlib.util
import io
import os
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock

from llamatron.composition.checks import listed
from llamatron.composition.file_format import FLUIDSYNTH_DEVICE, ClipSlotSetting
from llamatron.realtime.fluidsynth import AUDIO_DEVICE_VARIABLE
from llamatron.music import midi
from llamatron.strings import about, errors
from llamatron.tui.launch import LEAD_IN_SECONDS, LEAD_OUT_SECONDS, SPLASH_SECONDS
from llamatron.tui.uses import looping_scenes
from tests.support.ui_testing import a_song, DRUMS, LEAD
from llamatron.visualizers.modes import MODES

SCRIPT = pathlib.Path(__file__).resolve().parent.parent.parent / 'internal_tools' / 'record_demo.py'
MODULE_NAME = 'record_demo'
PORT = 'IAC Driver Bus 1'
AN_EXAMPLE = 'examples/learning/19_hocket_shanty.yml'
AN_EXAMPLE_NAME = 'Hocket Shanty'
SET_NAME = 'A Set'
OTHER_WORDS = 'live at the barn'
SCROLL_TEXT_OPTION = '--scroll-text'
ANNOUNCE_OPTION = '--announce'
ANNOUNCE = 'announce'
DETAIL_OPTION = '--detail'
DETAIL = 'detail'
ASK_VIEW = 'ask_view'
VISUALIZER_OPTION = '--visualizer'
NO_SCROLL_OPTION = '--no-scroll'
SUCCESS = 0
OTHER_PORT = 'Some Synth'
PORTS = [OTHER_PORT, PORT]
OWN = 'own'
OWN_PORT = 'Own Port'
A_SONG_SECONDS = 30.0
SMALL_LIMIT = 5.0
FIRST_INDEX = 0
NO_SUCH = 'doesnotexist'
PORT_NAMES = 'llamatron.realtime.outputs.output_port_names'
NOTHING_PRINTED = ''
DEVICE_ID = 'blackhole-id'
WINDOW = 72
STARTED = 100.0
STOPPED = 160.0
REGION_ARGUMENT = '10,20,300,200'
SET_PATH = 'a set.yml'
# What the stand-ins for screencapture and avconvert write, to tell the trimmed video from the one recorded.
VIDEO_BYTES = b'recorded'
TRIMMED_BYTES = b'trimmed'
RECORDED_BYTES = b'recorded'
PART_BYTES = b'part'
A_VIDEO = 'take.mov'
OTHER_VIDEO = 'other.mov'
A_TEMPORARY_ENDING = '.sb-1234'
A_FAILURE = 'no room'
# The argument that limits how long a command may run.
TIMEOUT = 'timeout'
RECORDED_SECONDS = 60
# screencapture's flag for how many seconds it records.
SUCCEEDED = 0
FLUID = 'fluid'
MULTI_OUTPUT = 'Multi-Output Device'
SPEAKERS = 'Mac Studio Speakers'


class StandInRecording:
    """Stands in for the screen recording: notes where it records and writes the video when stopped."""

    __slots__ = ('path',)
    made = []

    def __init__(self, *, path, window, audio_device, region=None):
        self.path = path
        StandInRecording.made.append((window, audio_device, region))

    def stop(self):
        pathlib.Path(self.path).write_bytes(VIDEO_BYTES)
        return SUCCEEDED


def load_script():
    """Load the tool as a module, since internal_tools/ is not a package."""
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

SOUND_OPTION = '--sound'
FLUIDSYNTH_OPTION = '--fluidsynth'
A_SET_NAMED = 'some_set.yml'


class TestRecordDemo(unittest.TestCase):

    def setUp(self):
        self.tool = load_script()
        self.document = a_song()
        # A take waits SETTLE_SECONDS on black before the tracker starts, which the tests don't wait for.
        settling = mock.patch.object(self.tool.time, 'sleep')
        self.slept = settling.start()
        self.addCleanup(settling.stop)

    def test_the_driver_is_the_first_port_holding_the_text_ignoring_case_or_none(self):
        self.assertEqual(self.tool.first_matching(names=PORTS, text='iac'), PORT)
        self.assertEqual(self.tool.first_matching(names=PORTS, text='Synth'), OTHER_PORT)
        self.assertIsNone(self.tool.first_matching(names=PORTS, text=NO_SUCH))

    def test_auto_assignment_numbers_the_tracks_from_channel_1_and_goes_round_after_16(self):
        tracks = [LEAD, DRUMS]
        self.assertEqual(self.tool.auto_assignment(tracks), [midi.MIN_CHANNEL, midi.MIN_CHANNEL + 1])
        many = [str(number) for number in range(midi.MAX_CHANNEL + 2)]
        self.assertEqual(self.tool.auto_assignment(many)[midi.MAX_CHANNEL], midi.MIN_CHANNEL)

    def test_a_typed_assignment_gives_each_track_a_channel_or_keeps_its_own_and_refuses_the_wrong_count_or_channel(self):
        tracks = [LEAD, DRUMS]
        self.assertEqual(self.tool.parse_assignment(text='1,1', tracks=tracks), [1, 1])
        self.assertEqual(self.tool.parse_assignment(text=' 3 , - ', tracks=tracks), [3, None])
        with self.assertRaises(ValueError):
            self.tool.parse_assignment(text='1', tracks=tracks)
        with self.assertRaises(ValueError):
            self.tool.parse_assignment(text='1,17', tracks=tracks)
        with self.assertRaises(ValueError):
            self.tool.parse_assignment(text='1,x', tracks=tracks)

    def test_assigning_makes_one_recorder_instrument_per_channel_on_the_port_and_turns_real_time_on(self):
        with contextlib.redirect_stdout(io.StringIO()) as said:
            self.tool.assign_tracks(document=self.document, channels=[2, 2], port=PORT)
        setlist = self.document.setlist()
        name = self.tool.INSTRUMENT_NAME.format(channel=2)
        self.assertEqual(setlist.get_instrument_names(), [name])
        self.assertEqual(setlist.get_instrument(name).get_device(), PORT)
        self.assertEqual(setlist.get_instrument(name).get_channel(), 2)
        self.assertTrue(setlist.is_real_time())
        song = self.document.song()
        self.assertEqual([song.get_track(track).get_instrument_name() for track in (LEAD, DRUMS)], [name, name])
        self.assertIn(name, said.getvalue())

    def test_a_dash_keeps_a_tracks_own_instrument_and_a_track_with_none_stays_silent(self):
        self.document.add_instrument(OWN)
        self.document.set_instrument_device(name=OWN, device=OWN_PORT)
        self.document.set_track_instrument(name=LEAD, instrument=OWN)
        with contextlib.redirect_stdout(io.StringIO()) as said:
            self.tool.assign_tracks(document=self.document, channels=[None, None], port=PORT)
        song = self.document.song()
        self.assertEqual(song.get_track(LEAD).get_instrument_name(), OWN)
        self.assertFalse(song.get_track(DRUMS).get_instrument_name())
        self.assertEqual(self.document.setlist().get_instrument_names(), [OWN])
        self.assertIn(self.tool.TRACK_KEPT.format(track=LEAD, instrument=OWN), said.getvalue())
        self.assertIn(self.tool.TRACK_SILENT.format(track=DRUMS), said.getvalue())

    def test_assigning_nothing_to_any_track_is_refused(self):
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(ValueError):
            self.tool.assign_tracks(document=self.document, channels=[None, None], port=PORT)

    def test_a_take_is_the_splash_the_lead_in_the_song_the_lead_out_the_splash_again_the_hold_and_a_margin_or_the_limit(self):
        expected = SPLASH_SECONDS + LEAD_IN_SECONDS + A_SONG_SECONDS + LEAD_OUT_SECONDS + SPLASH_SECONDS + self.tool.HOLD_SECONDS + self.tool.MARGIN_SECONDS
        self.assertEqual(self.tool.take_seconds(song_seconds=A_SONG_SECONDS, max_seconds=self.tool.DEFAULT_MAX_SECONDS), expected)
        self.assertEqual(self.tool.take_seconds(song_seconds=A_SONG_SECONDS, max_seconds=SMALL_LIMIT), SMALL_LIMIT)

    def test_the_sound_option_chooses_the_daw_or_fluidsynth_and_the_daw_is_the_default(self):
        for argv, expected in [([], False), ([SOUND_OPTION, self.tool.SOUND_DAW], False), ([SOUND_OPTION, self.tool.SOUND_FLUIDSYNTH], True), ([FLUIDSYNTH_OPTION], True)]:
            with self.subTest(argv=argv), mock.patch.object(self.tool, 'record', return_value=self.tool.SUCCESS) as record:
                self.assertEqual(self.tool.main(argv=[A_SET_NAMED, *argv]), self.tool.SUCCESS)
                self.assertEqual(record.call_args.kwargs['fluidsynth'], expected)

    def test_a_driver_nobody_has_stops_the_recorder_before_anything_else(self):
        with mock.patch(PORT_NAMES, return_value=PORTS), contextlib.redirect_stderr(io.StringIO()) as told:
            code = self.tool.main(argv=['some_set.yml', '--use-driver', NO_SUCH])
        self.assertEqual(code, self.tool.FAILURE)
        self.assertIn(NO_SUCH, told.getvalue())
        self.assertIn(PORT, told.getvalue())

    def test_a_scene_whose_every_clip_loops_is_refused_in_the_programs_words(self):
        self.assertIsNone(self.tool.recording_problem(self.document.song()))
        self.document.set_clip_slot_setting(index=FIRST_INDEX, track=LEAD, setting=ClipSlotSetting.LOOP, value=True)
        self.assertEqual(errors.ERR_RECORDING_SONG_LOOPS.format(scenes=listed(looping_scenes(self.document.song()))), self.tool.recording_problem(self.document.song()))

    def test_the_take_waits_for_enter_after_the_ready_line_which_is_the_last_thing_printed(self):
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), mock.patch('builtins.input') as typed:
            self.tool.wait_for_go(go=False)
        typed.assert_called_once()
        self.assertEqual(printed.getvalue().splitlines()[-1], self.tool.SETUP_GO)

    def test_a_take_shows_the_clips_or_the_visualizer_mode_chosen(self):
        with mock.patch('builtins.input', return_value='1'), contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(self.tool.ask_for_view())
        with mock.patch('builtins.input', return_value='2'), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.tool.ask_for_view(), MODES[0].OPTION)
        with mock.patch('builtins.input', return_value=NO_SUCH), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertIs(self.tool.ask_for_view(), False)

    def visualizer_take(self, *, staged, path=SET_PATH, scroll=True, scroll_text=None, announce=False):
        """Record a take of the last visualizer mode, chosen when asked, with everything it runs replaced, and return what the tracker was launched with."""
        # A take gives the set's tracks instruments, so each take is of a set no take has touched.
        self.document = a_song()
        devices = [(DEVICE_ID, self.tool.DEFAULT_AUDIO_DEVICE)]
        region = mock.Mock()
        region.argument.return_value = REGION_ARGUMENT
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(self.tool, 'RECORDINGS', folder), \
                mock.patch.object(self.tool, 'output_port_names', return_value=PORTS), mock.patch.object(self.tool, 'audio_devices', return_value=devices), \
                mock.patch.object(self.tool, 'terminal_window_id', return_value=WINDOW), mock.patch.object(self.tool.Document, 'load', return_value=self.document), \
                mock.patch.object(self.tool, 'cells_region', return_value=region), mock.patch.object(self.tool.subprocess, 'run') as trim, \
                mock.patch.object(self.tool, 'LlamatronApp') as app, \
                mock.patch('builtins.input', return_value=str(len(MODES) + 1)), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            trim.side_effect = lambda command, **named: pathlib.Path(command[command.index(self.tool.OUTPUT_FLAG) + 1]).write_bytes(TRIMMED_BYTES)
            self.tool.record(path=path, driver=PORT, audio_device=self.tool.DEFAULT_AUDIO_DEVICE, assignment=None, max_seconds=SMALL_LIMIT, window_id=None,
                             go=True, ask_view=True, staged=staged, recording=StandInRecording, scroll=scroll, scroll_text=scroll_text, announce=announce)
        return app.call_args.kwargs['launch']

    def test_a_take_scrolls_the_sets_name_from_its_file_unless_told_other_words_or_none(self):
        # DEMO: and the file's name as words, for every set; --scroll-text gives other words and --no-scroll none.
        self.assertEqual(self.tool.scroll_text_of(path=AN_EXAMPLE), about.MSG_DEMO_SCROLL.format(name=AN_EXAMPLE_NAME))
        self.assertEqual(self.tool.scroll_text_of(path=SET_PATH), about.MSG_DEMO_SCROLL.format(name=SET_NAME))
        self.assertEqual(self.tool.scroll_text_of(path=AN_EXAMPLE, scroll_text=OTHER_WORDS), OTHER_WORDS)
        self.assertIsNone(self.tool.scroll_text_of(path=AN_EXAMPLE, scroll=False))

    def test_the_words_go_to_a_batch_take_and_a_plain_take(self):
        for staged in (True, False):
            with self.subTest(staged=staged):
                self.assertEqual(self.visualizer_take(staged=staged, path=AN_EXAMPLE).scroll_text, about.MSG_DEMO_SCROLL.format(name=AN_EXAMPLE_NAME))
                self.assertEqual(self.visualizer_take(staged=staged, scroll_text=OTHER_WORDS).scroll_text, OTHER_WORDS)
                self.assertIsNone(self.visualizer_take(staged=staged, scroll=False).scroll_text)

    def test_announce_goes_to_a_batch_take_and_a_plain_take_and_is_off_unless_asked(self):
        for staged in (True, False):
            with self.subTest(staged=staged):
                self.assertTrue(self.visualizer_take(staged=staged, announce=True).announce)
                self.assertFalse(self.visualizer_take(staged=staged).announce)
        with mock.patch.object(self.tool, 'record', return_value=SUCCESS) as record:
            self.tool.main(argv=[SET_PATH, ANNOUNCE_OPTION])
            self.assertTrue(record.call_args.kwargs[ANNOUNCE])
            self.tool.main(argv=[SET_PATH])
            self.assertFalse(record.call_args.kwargs[ANNOUNCE])

    def test_detail_records_the_clips_without_asking_and_is_off_unless_asked(self):
        with mock.patch.object(self.tool, 'record', return_value=SUCCESS) as record:
            self.tool.main(argv=[SET_PATH, DETAIL_OPTION])
            self.assertTrue(record.call_args.kwargs[DETAIL])
            self.assertFalse(record.call_args.kwargs[ASK_VIEW])
            self.assertIsNone(record.call_args.kwargs['visualizer'])
            self.tool.main(argv=[SET_PATH])
            self.assertFalse(record.call_args.kwargs[DETAIL])
            # The details show on the clips, so a visualizer mode cannot be asked for with them.
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                self.tool.main(argv=[SET_PATH, DETAIL_OPTION, VISUALIZER_OPTION, MODES[0].OPTION])

    def test_the_command_line_passes_the_words_or_none_and_refuses_both(self):
        with mock.patch.object(self.tool, 'record', return_value=SUCCESS) as record:
            self.tool.main(argv=[SET_PATH, SCROLL_TEXT_OPTION, OTHER_WORDS])
            self.assertEqual(record.call_args.kwargs['scroll_text'], OTHER_WORDS)
            self.assertTrue(record.call_args.kwargs['scroll'])
            self.tool.main(argv=[SET_PATH, NO_SCROLL_OPTION])
            self.assertFalse(record.call_args.kwargs['scroll'])
            self.tool.main(argv=[SET_PATH])
            self.assertTrue(record.call_args.kwargs['scroll'])
            self.assertIsNone(record.call_args.kwargs['scroll_text'])
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            self.tool.main(argv=[SET_PATH, SCROLL_TEXT_OPTION, OTHER_WORDS, NO_SCROLL_OPTION])

    def test_a_take_of_a_visualizer_mode_is_a_batch_video_of_that_mode_by_default(self):
        launch = self.visualizer_take(staged=True)
        self.assertTrue(launch.for_recording)
        self.assertTrue(launch.batch_video)
        self.assertEqual(launch.visualizer, MODES[-1].OPTION)

    def test_a_plain_take_of_a_visualizer_mode_shows_it_over_the_clip_area(self):
        launch = self.visualizer_take(staged=False)
        self.assertTrue(launch.for_recording)
        self.assertFalse(launch.batch_video)
        self.assertEqual(launch.visualizer, MODES[-1].OPTION)

    def test_the_take_records_until_the_tracker_quits_and_the_video_loses_its_last_seconds(self):
        devices = [(DEVICE_ID, self.tool.DEFAULT_AUDIO_DEVICE)]
        StandInRecording.made.clear()
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(self.tool, 'RECORDINGS', folder), \
                mock.patch.object(self.tool, 'output_port_names', return_value=PORTS), mock.patch.object(self.tool, 'audio_devices', return_value=devices), \
                mock.patch.object(self.tool, 'terminal_window_id', return_value=WINDOW), mock.patch.object(self.tool.Document, 'load', return_value=self.document), \
                mock.patch.object(self.tool.subprocess, 'run') as trim, mock.patch.object(self.tool.time, 'monotonic', side_effect=[STARTED, STOPPED]), \
                mock.patch.object(self.tool, 'LlamatronApp') as app, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            video = os.path.join(folder, self.tool.file_stem(SET_PATH) + self.tool.VIDEO_SUFFIX)
            trim.side_effect = lambda command, **named: pathlib.Path(command[command.index(self.tool.OUTPUT_FLAG) + 1]).write_bytes(TRIMMED_BYTES)
            code = self.tool.record(path=SET_PATH, driver=PORT, audio_device=self.tool.DEFAULT_AUDIO_DEVICE, assignment=None,
                                    max_seconds=self.tool.DEFAULT_MAX_SECONDS, window_id=None, go=True, recording=StandInRecording)
            self.assertEqual(code, self.tool.SUCCESS)
            self.assertEqual(pathlib.Path(video).read_bytes(), TRIMMED_BYTES)
        self.assertEqual(StandInRecording.made, [(WINDOW, DEVICE_ID, None)])
        launch = app.call_args.kwargs['launch']
        self.assertEqual(launch.hold_seconds, self.tool.HOLD_SECONDS)
        command = trim.call_args.args[0]
        self.assertEqual(float(command[command.index(self.tool.START_FLAG) + 1]), self.tool.CUT_FROM_START)
        self.assertEqual(float(command[command.index(self.tool.DURATION_FLAG) + 1]), STOPPED - STARTED - self.tool.CUT_FROM_START - self.tool.TRIMMED_SECONDS)
        self.slept.assert_any_call(self.tool.SETTLE_SECONDS)

    def trimmed(self, *, folder, side_effect):
        """Trim a video in a folder with a stand-in for avconvert, and return the video's path and what the trim answered or raised."""
        video = os.path.join(folder, A_VIDEO)
        pathlib.Path(video).write_bytes(RECORDED_BYTES)
        with mock.patch.object(self.tool.subprocess, 'run', side_effect=side_effect):
            try:
                return video, self.tool.trim_end(video=video, recorded_seconds=RECORDED_SECONDS)
            except KeyboardInterrupt as stopped:
                return video, stopped

    def write_trimmed(self, command, **named):
        pathlib.Path(command[command.index(self.tool.OUTPUT_FLAG) + 1]).write_bytes(TRIMMED_BYTES)

    def write_part_and_stop(self, command, **named):
        pathlib.Path(command[command.index(self.tool.OUTPUT_FLAG) + 1]).write_bytes(PART_BYTES)
        raise KeyboardInterrupt

    def write_part_and_fail(self, command, **named):
        pathlib.Path(command[command.index(self.tool.OUTPUT_FLAG) + 1]).write_bytes(PART_BYTES)
        raise OSError(A_FAILURE)

    def write_part_and_run_too_long(self, command, **named):
        pathlib.Path(command[command.index(self.tool.OUTPUT_FLAG) + 1]).write_bytes(PART_BYTES)
        raise subprocess.TimeoutExpired(cmd=command, timeout=named[TIMEOUT])

    def test_a_trim_that_runs_too_long_is_stopped_and_the_video_recorded_is_kept(self):
        with tempfile.TemporaryDirectory() as folder:
            video = os.path.join(folder, A_VIDEO)
            pathlib.Path(video).write_bytes(RECORDED_BYTES)
            with mock.patch.object(self.tool.subprocess, 'run', side_effect=self.write_part_and_run_too_long) as run:
                answer = self.tool.trim_end(video=video, recorded_seconds=RECORDED_SECONDS, give_up_after=RECORDED_SECONDS + self.tool.TRIM_SPARE_SECONDS)
            self.assertEqual(run.call_args.kwargs[TIMEOUT], RECORDED_SECONDS + self.tool.TRIM_SPARE_SECONDS)
            self.assertEqual(answer, self.tool.TRIM_GAVE_UP.format(seconds=round(RECORDED_SECONDS + self.tool.TRIM_SPARE_SECONDS)))
            self.assertEqual(os.listdir(folder), [A_VIDEO])
            self.assertEqual(pathlib.Path(video).read_bytes(), RECORDED_BYTES)

    def test_a_trim_with_no_limit_waits_as_long_as_the_trim_takes(self):
        with tempfile.TemporaryDirectory() as folder:
            video = os.path.join(folder, A_VIDEO)
            pathlib.Path(video).write_bytes(RECORDED_BYTES)
            with mock.patch.object(self.tool.subprocess, 'run', side_effect=self.write_trimmed) as run:
                self.tool.trim_end(video=video, recorded_seconds=RECORDED_SECONDS)
            self.assertIsNone(run.call_args.kwargs[TIMEOUT])

    def test_a_trim_keeps_only_the_trimmed_video(self):
        with tempfile.TemporaryDirectory() as folder:
            video, answer = self.trimmed(folder=folder, side_effect=self.write_trimmed)
            self.assertIsNone(answer)
            self.assertEqual(os.listdir(folder), [A_VIDEO])
            self.assertEqual(pathlib.Path(video).read_bytes(), TRIMMED_BYTES)

    def test_a_trim_that_is_stopped_leaves_nothing_but_the_video_recorded(self):
        with tempfile.TemporaryDirectory() as folder:
            video, answer = self.trimmed(folder=folder, side_effect=self.write_part_and_stop)
            self.assertIsInstance(answer, KeyboardInterrupt)
            self.assertEqual(os.listdir(folder), [A_VIDEO])
            self.assertEqual(pathlib.Path(video).read_bytes(), RECORDED_BYTES)

    def test_a_trim_that_fails_says_why_and_leaves_nothing_but_the_video_recorded(self):
        with tempfile.TemporaryDirectory() as folder:
            video, answer = self.trimmed(folder=folder, side_effect=self.write_part_and_fail)
            self.assertIn(A_FAILURE, answer)
            self.assertEqual(os.listdir(folder), [A_VIDEO])
            self.assertEqual(pathlib.Path(video).read_bytes(), RECORDED_BYTES)

    def test_a_trim_removes_what_stopped_trims_left_before(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in (OTHER_VIDEO + self.tool.OLD_TRIMMING_MARK, OTHER_VIDEO + self.tool.OLD_TRIMMING_MARK + A_TEMPORARY_ENDING):
                pathlib.Path(folder, name).write_bytes(PART_BYTES)
            pathlib.Path(folder, OTHER_VIDEO).write_bytes(RECORDED_BYTES)
            os.makedirs(os.path.join(folder, self.tool.TRIMMING_FOLDER))
            pathlib.Path(folder, self.tool.TRIMMING_FOLDER, OTHER_VIDEO).write_bytes(PART_BYTES)
            self.trimmed(folder=folder, side_effect=self.write_trimmed)
            self.assertEqual(sorted(os.listdir(folder)), sorted([A_VIDEO, OTHER_VIDEO]))

    def record_with_fluidsynth(self, *, installed=True, output=None, outputs=()):
        """Record a take with --fluidsynth, every program it runs replaced, and return the exit code, what the tracker was launched with, what was printed and the device FluidSynth was sent to."""
        devices = [(DEVICE_ID, self.tool.DEFAULT_AUDIO_DEVICE)]
        printed = io.StringIO()
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(self.tool, 'RECORDINGS', folder), mock.patch.dict(os.environ), \
                mock.patch.object(self.tool, 'is_installed', return_value=installed), mock.patch.object(self.tool, 'output_port_names', return_value=[]) as ports, \
                mock.patch.object(self.tool, 'fluidsynth_outputs', return_value=list(outputs)), \
                mock.patch.object(self.tool, 'audio_devices', return_value=devices), mock.patch.object(self.tool, 'terminal_window_id', return_value=WINDOW), \
                mock.patch.object(self.tool.Document, 'load', return_value=self.document), \
                mock.patch.object(self.tool.subprocess, 'run') as trim, mock.patch.object(self.tool, 'LlamatronApp') as app, \
                contextlib.redirect_stdout(printed), contextlib.redirect_stderr(printed):
            trim.side_effect = lambda command, **named: pathlib.Path(command[command.index(self.tool.OUTPUT_FLAG) + 1]).write_bytes(TRIMMED_BYTES)
            code = self.tool.record(path=SET_PATH, driver=PORT, audio_device=self.tool.DEFAULT_AUDIO_DEVICE, assignment=None, max_seconds=SMALL_LIMIT,
                                    window_id=None, go=True, fluidsynth=True, fluidsynth_output=output, recording=StandInRecording)
            sent_to = os.environ.get(AUDIO_DEVICE_VARIABLE)
        ports.assert_not_called()
        return code, app, printed.getvalue(), sent_to

    def give_lead_fluidsynth(self):
        self.document.add_instrument(FLUID)
        self.document.set_instrument_device(name=FLUID, device=FLUIDSYNTH_DEVICE)
        self.document.set_track_instrument(name=LEAD, instrument=FLUID)

    def test_with_fluidsynth_the_sets_own_instruments_play_into_the_recorded_device_with_no_port(self):
        self.give_lead_fluidsynth()
        code, app, printed, sent_to = self.record_with_fluidsynth()
        self.assertEqual(code, self.tool.SUCCESS)
        self.assertEqual(sent_to, self.tool.DEFAULT_AUDIO_DEVICE)
        self.assertIn(self.tool.TRACK_FLUIDSYNTH.format(track=LEAD, instrument=FLUID), printed)
        self.assertIn(self.tool.TRACK_SILENT.format(track=DRUMS), printed)
        self.assertNotIn(self.tool.INSTRUMENT_NAME.format(channel=midi.MIN_CHANNEL), self.document.setlist().get_instrument_names())
        self.assertTrue(self.document.setlist().is_real_time())
        self.assertTrue(app.call_args.kwargs['launch'].for_recording)

    def test_with_fluidsynth_an_output_given_is_where_fluidsynth_plays(self):
        self.give_lead_fluidsynth()
        code, _, printed, sent_to = self.record_with_fluidsynth(output=MULTI_OUTPUT)
        self.assertEqual(code, self.tool.SUCCESS)
        self.assertEqual(sent_to, MULTI_OUTPUT)
        self.assertIn(self.tool.SETUP_FLUIDSYNTH_HEARD.format(output=MULTI_OUTPUT, device=self.tool.DEFAULT_AUDIO_DEVICE), printed)

    def test_with_fluidsynth_a_multi_output_device_is_chosen_so_the_take_is_heard_as_it_records(self):
        self.give_lead_fluidsynth()
        code, _, printed, sent_to = self.record_with_fluidsynth(outputs=[SPEAKERS, self.tool.DEFAULT_AUDIO_DEVICE, MULTI_OUTPUT])
        self.assertEqual(code, self.tool.SUCCESS)
        self.assertEqual(sent_to, MULTI_OUTPUT)
        self.assertIn(self.tool.SETUP_FLUIDSYNTH_HEARD.format(output=MULTI_OUTPUT, device=self.tool.DEFAULT_AUDIO_DEVICE), printed)

    def test_the_output_given_wins_and_with_no_multi_output_device_the_recorded_device_is_played_to(self):
        self.assertEqual(self.tool.output_for_fluidsynth(given=SPEAKERS, recorded=self.tool.DEFAULT_AUDIO_DEVICE, outputs=[MULTI_OUTPUT]), SPEAKERS)
        self.assertEqual(self.tool.output_for_fluidsynth(given=None, recorded=self.tool.DEFAULT_AUDIO_DEVICE, outputs=[SPEAKERS]), self.tool.DEFAULT_AUDIO_DEVICE)
        self.assertEqual(self.tool.output_for_fluidsynth(given=None, recorded=self.tool.DEFAULT_AUDIO_DEVICE, outputs=[]), self.tool.DEFAULT_AUDIO_DEVICE)

    def test_fluidsynths_outputs_are_read_from_the_options_line_of_its_shell(self):
        answer = mock.Mock(stdout='> info audio.coreaudio.device\nOptions:       ' + ', '.join([SPEAKERS, MULTI_OUTPUT]) + '\n> quit\n')
        with mock.patch.object(self.tool.subprocess, 'run', return_value=answer):
            self.assertEqual(self.tool.fluidsynth_outputs(), [SPEAKERS, MULTI_OUTPUT])
        with mock.patch.object(self.tool.subprocess, 'run', side_effect=OSError):
            self.assertEqual(self.tool.fluidsynth_outputs(), [])

    def test_with_fluidsynth_not_installed_or_no_track_through_it_nothing_is_recorded(self):
        code, app, printed, _ = self.record_with_fluidsynth(installed=False)
        self.assertEqual(code, self.tool.FAILURE)
        self.assertIn(self.tool.NO_FLUIDSYNTH, printed)
        app.assert_not_called()
        with self.assertRaises(ValueError) as raised, contextlib.redirect_stdout(io.StringIO()):
            self.tool.through_fluidsynth(document=self.document)
        self.assertEqual(str(raised.exception), self.tool.NO_FLUIDSYNTH_TRACK)

    def test_an_interactive_take_records_until_the_tracker_quits_and_welcomes_a_song_that_loops(self):
        devices = [(DEVICE_ID, self.tool.DEFAULT_AUDIO_DEVICE)]
        for track in (LEAD, DRUMS):
            self.document.set_clip_slot_setting(index=FIRST_INDEX, track=track, setting=ClipSlotSetting.LOOP, value=True)
        recordings = []

        class StandInRecording:
            """Stands in for the tutorial's screen recording: writes the video when stopped."""

            __slots__ = ('path',)

            def __init__(self, *, path, window, audio_device, region=None):
                self.path = path
                recordings.append((window, audio_device))

            def stop(self):
                pathlib.Path(self.path).write_bytes(VIDEO_BYTES)
                return self_tool.SUCCESS
        self_tool = self.tool
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(self.tool, 'RECORDINGS', folder), \
                mock.patch.object(self.tool, 'output_port_names', return_value=PORTS), mock.patch.object(self.tool, 'audio_devices', return_value=devices), \
                mock.patch.object(self.tool, 'terminal_window_id', return_value=WINDOW), mock.patch.object(self.tool.Document, 'load', return_value=self.document), \
                mock.patch.object(self.tool.subprocess, 'Popen') as timed_capture, mock.patch.object(self.tool.subprocess, 'run') as trim, \
                mock.patch.object(self.tool, 'LlamatronApp') as app, contextlib.redirect_stdout(io.StringIO()) as printed, contextlib.redirect_stderr(io.StringIO()):
            trim.side_effect = lambda command, **named: pathlib.Path(command[command.index(self.tool.OUTPUT_FLAG) + 1]).write_bytes(TRIMMED_BYTES)
            code = self.tool.record(path=SET_PATH, driver=PORT, audio_device=self.tool.DEFAULT_AUDIO_DEVICE, assignment=None, max_seconds=SMALL_LIMIT,
                                    window_id=None, go=True, interactive=True, recording=StandInRecording)
            video = os.path.join(folder, self.tool.file_stem(SET_PATH) + self.tool.VIDEO_SUFFIX)
            self.assertEqual(pathlib.Path(video).read_bytes(), TRIMMED_BYTES)
        self.assertEqual(code, self.tool.SUCCESS)
        self.assertEqual(recordings, [(WINDOW, DEVICE_ID)])
        timed_capture.assert_not_called()
        launch = app.call_args.kwargs['launch']
        self.assertTrue(launch.interactive)
        self.assertTrue(launch.for_recording)
        self.assertFalse(launch.autoplay)
        self.assertIn(self.tool.INTERACTIVE_TAKE.format(seconds=SMALL_LIMIT), printed.getvalue())

    def test_go_starts_the_take_at_once_without_asking(self):
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), mock.patch('builtins.input') as typed:
            self.tool.wait_for_go(go=True)
        typed.assert_not_called()
        self.assertEqual(printed.getvalue(), NOTHING_PRINTED)
