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

"""internal_tools/play_demo.py lists the demos' WAV files, numbered, plays the one picked or named with afplay, and shows how far along it is."""

import contextlib
import importlib.util
import io
import os
import pathlib
import tempfile
import unittest
import wave
from unittest import mock

from llamatron.composition.setlist import Setlist

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / 'internal_tools' / 'play_demo.py'
MODULE_NAME = 'play_demo'
# Demos' WAV files of the test's own, written out of order, and a file that isn't one.
WAVES = ['strum.wav', 'arpeggiator.wav', 'hocket_shanty.wav']
NOT_A_WAVE = 'strum.mid'
FIRST_BY_NAME = 'arpeggiator.wav'
SECOND = '2'
LIST_FLAG = '--list'
EXAMPLES = 'examples'
NUMBERED_SET = '08_tie.yml'
NUMBERED_NAME = 'tie'
PLAIN_SET = 'strum.yml'
PLAIN_NAME = 'strum'
LONGER_SET = 'strum_songs.yml'
LONGER_NAME = 'strum_songs'
SONG = 'ballad'
REAL_DEMO = 'entertainer'
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)
TOO_HIGH = '9'
NOT_A_NUMBER = 'strum'
NAMED = 'strum'
# A real WAV file's sound: one channel of 16-bit samples, so many a second, lasting so long.
CHANNELS = 1
SAMPLE_BYTES = 2
FRAME_RATE = 8000
WAVE_SECONDS = 3
SILENT_FRAME = b'\x00\x00'
# A demo 3 minutes long, and moments into it.
LENGTH = 180
HALFWAY = 90
PAST_THE_END = 200
NOT_A_WAVE_TEXT = 'not a wave file'


class FakePlayer:
    """Stands in for afplay's process: running for so many polls, then done, or stopped."""

    __slots__ = ('polls_left', 'returncode', 'terminated', 'interrupt_after')

    def __init__(self, *, polls, interrupt_after=None):
        self.polls_left = polls
        self.returncode = None
        self.terminated = False
        self.interrupt_after = interrupt_after

    def poll(self):
        if self.interrupt_after is not None:
            if self.interrupt_after == 0:
                raise KeyboardInterrupt
            self.interrupt_after -= 1
        if self.polls_left == 0:
            self.returncode = 0
            return 0
        self.polls_left -= 1
        return None

    def terminate(self):
        self.terminated = True

    def wait(self):
        return self.returncode


def write_wave(*, path, seconds):
    """Write a silent WAV file that lasts so many seconds."""
    with wave.open(path, 'wb') as file:
        file.setnchannels(CHANNELS)
        file.setsampwidth(SAMPLE_BYTES)
        file.setframerate(FRAME_RATE)
        file.writeframes(SILENT_FRAME * FRAME_RATE * seconds)


def load_script():
    """Load the tool as a module, since internal_tools/ is not a package."""
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestPlayDemo(unittest.TestCase):

    def setUp(self):
        self.tool = load_script()
        self.scratch = tempfile.TemporaryDirectory()
        self.folder = self.scratch.name
        for name in [*WAVES, NOT_A_WAVE]:
            pathlib.Path(self.folder, name).write_bytes(b'')

    def tearDown(self):
        self.scratch.cleanup()

    def run_tool(self, *, argv, typed=''):
        """Run the tool with afplay replaced, and return its exit code, what it printed and what afplay was given."""
        printed = io.StringIO()
        with mock.patch('builtins.input', return_value=typed), \
                mock.patch.object(self.tool.subprocess, 'Popen', return_value=FakePlayer(polls=0)) as popen, \
                contextlib.redirect_stdout(printed), contextlib.redirect_stderr(printed):
            code = self.tool.main(argv=[*argv, '--folder', self.folder])
        played = [call.args[0] for call in popen.call_args_list]
        return code, printed.getvalue(), played

    def test_the_list_numbers_the_wave_files_by_name_and_plays_the_one_typed(self):
        code, printed, played = self.run_tool(argv=[], typed=SECOND)
        self.assertEqual(code, 0)
        names = sorted(name.removesuffix(self.tool.WAVE_SUFFIX) for name in WAVES)
        for number, name in enumerate(names, start=1):
            self.assertIn(self.tool.DEMO_LINE.format(number=number, name=name), printed)
        self.assertNotIn(NOT_A_WAVE, printed)
        self.assertEqual(played, [[self.tool.PLAYER, os.path.join(self.folder, sorted(WAVES)[1])]])

    def test_a_number_given_plays_that_demo_at_once_and_says_its_number(self):
        code, printed, played = self.run_tool(argv=[SECOND])
        self.assertEqual(code, 0)
        second = sorted(WAVES)[1]
        self.assertEqual(played, [[self.tool.PLAYER, os.path.join(self.folder, second)]])
        self.assertIn(self.tool.NUMBER_PLAYING.format(number=int(SECOND), count=len(WAVES), name=second.removesuffix(self.tool.WAVE_SUFFIX)), printed)
        self.assertNotIn(self.tool.ASK_WHICH, printed)

    def test_a_number_past_the_list_plays_nothing_and_says_how_long_the_list_is(self):
        code, printed, played = self.run_tool(argv=[TOO_HIGH])
        self.assertEqual(code, 1)
        self.assertIn(self.tool.NO_SUCH_NUMBER.format(number=int(TOO_HIGH), count=len(WAVES)), printed)
        self.assertEqual(played, [])

    def test_the_list_alone_is_printed_and_nothing_plays(self):
        code, printed, played = self.run_tool(argv=[LIST_FLAG])
        self.assertEqual(code, 0)
        self.assertIn(self.tool.DEMO_LINE.format(number=1, name=sorted(WAVES)[0].removesuffix(self.tool.WAVE_SUFFIX)), printed)
        self.assertEqual(played, [])

    def test_a_demo_is_matched_to_its_set_by_name_by_a_learning_number_and_by_a_song_of_a_set(self):
        sets = [os.path.join(EXAMPLES, 'learning', NUMBERED_SET), os.path.join(EXAMPLES, 'other', PLAIN_SET), os.path.join(EXAMPLES, 'other', LONGER_SET)]
        self.assertEqual(self.tool.set_of_demo(name=PLAIN_NAME, sets=sets), sets[1])
        self.assertEqual(self.tool.set_of_demo(name=NUMBERED_NAME, sets=sets), sets[0])
        self.assertEqual(self.tool.set_of_demo(name=LONGER_NAME + self.tool.NAME_JOIN + SONG, sets=sets), sets[2])
        self.assertIsNone(self.tool.set_of_demo(name=SONG, sets=sets))

    def test_the_details_of_a_real_demo_name_its_set_and_title(self):
        real = os.path.join(ROOT, EXAMPLES, 'by_genre', 'ragtime', REAL_DEMO + self.tool.SET_SUFFIX)
        wave_path = os.path.join(self.folder, REAL_DEMO + self.tool.WAVE_SUFFIX)
        pathlib.Path(wave_path).write_bytes(b'')
        lines = self.tool.detail_lines(path=wave_path, folder=self.folder, sets=[real])
        self.assertEqual(lines[1], self.tool.DETAIL_SET.format(path=real))
        self.assertEqual(lines[2], self.tool.DETAIL_TITLE.format(title=Setlist.read_file(real).get_title()))
        self.assertEqual(len(self.tool.detail_lines(path=wave_path, folder=self.folder, sets=[])), 1)

    def test_a_number_outside_the_list_or_no_number_plays_nothing(self):
        for typed in [TOO_HIGH, NOT_A_NUMBER, '']:
            code, printed, played = self.run_tool(argv=[], typed=typed)
            self.assertEqual(code, 1)
            self.assertIn(self.tool.NOT_A_CHOICE, printed)
            self.assertEqual(played, [])

    def test_a_demo_named_plays_at_once_without_the_list(self):
        code, printed, played = self.run_tool(argv=[NAMED])
        self.assertEqual(code, 0)
        self.assertNotIn(self.tool.ASK_WHICH, printed)
        self.assertEqual(played, [[self.tool.PLAYER, os.path.join(self.folder, NAMED + self.tool.WAVE_SUFFIX)]])

    def test_a_demo_with_no_wave_file_says_to_make_the_demos(self):
        missing = os.path.join(self.folder, FIRST_BY_NAME)
        os.remove(missing)
        code, printed, played = self.run_tool(argv=[FIRST_BY_NAME.removesuffix(self.tool.WAVE_SUFFIX)])
        self.assertEqual(code, 1)
        self.assertIn(self.tool.NO_SUCH_DEMO.format(path=missing), printed)
        self.assertEqual(played, [])

    def test_a_folder_with_no_wave_files_says_to_make_the_demos(self):
        for name in WAVES:
            os.remove(os.path.join(self.folder, name))
        code, printed, played = self.run_tool(argv=[])
        self.assertEqual(code, 1)
        self.assertIn(self.tool.NO_WAVES.format(folder=self.folder), printed)
        self.assertEqual(played, [])


class TestProgress(unittest.TestCase):

    def setUp(self):
        self.tool = load_script()

    def test_the_bar_fills_with_the_time_played(self):
        empty = self.tool.progress_line(played=0, length=LENGTH)
        half = self.tool.progress_line(played=HALFWAY, length=LENGTH)
        full = self.tool.progress_line(played=LENGTH, length=LENGTH)
        self.assertEqual(empty.count(self.tool.BAR_PLAYED), 0)
        self.assertEqual(half.count(self.tool.BAR_PLAYED), self.tool.BAR_WIDTH // 2)
        self.assertEqual(full.count(self.tool.BAR_TO_PLAY), 0)
        self.assertIn(self.tool.clock(HALFWAY), half)
        self.assertIn(self.tool.clock(LENGTH), half)

    def test_the_time_played_never_passes_the_length(self):
        self.assertEqual(self.tool.progress_line(played=PAST_THE_END, length=LENGTH), self.tool.progress_line(played=LENGTH, length=LENGTH))

    def test_the_clock_reads_minutes_and_seconds(self):
        self.assertEqual(self.tool.clock(LENGTH + 5), self.tool.CLOCK.format(minutes=3, seconds=5))

    def test_a_wave_file_length_is_read_and_a_file_that_is_not_one_has_none(self):
        with tempfile.TemporaryDirectory() as folder:
            real = os.path.join(folder, NAMED + self.tool.WAVE_SUFFIX)
            write_wave(path=real, seconds=WAVE_SECONDS)
            self.assertEqual(self.tool.wave_seconds(real), WAVE_SECONDS)
            fake = os.path.join(folder, FIRST_BY_NAME)
            pathlib.Path(fake).write_text(NOT_A_WAVE_TEXT)
            self.assertIsNone(self.tool.wave_seconds(fake))

    def play_with(self, *, player, seconds):
        """Play a WAV file of so many seconds, or a file that isn't one for None, with player in place of afplay and a clock that moves a second a redraw."""
        moments = iter(range(1000))
        printed = io.StringIO()
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, NAMED + self.tool.WAVE_SUFFIX)
            if seconds is None:
                pathlib.Path(path).write_text(NOT_A_WAVE_TEXT)
            else:
                write_wave(path=path, seconds=seconds)
            with mock.patch.object(self.tool.subprocess, 'Popen', return_value=player):
                code = self.tool.play(path, now=lambda: next(moments), sleep=lambda seconds: None, out=printed)
        return code, printed.getvalue()

    def test_the_line_is_drawn_while_the_demo_plays_and_ends_full(self):
        code, printed = self.play_with(player=FakePlayer(polls=2), seconds=WAVE_SECONDS)
        self.assertEqual(code, 0)
        self.assertIn(self.tool.progress_line(played=1, length=WAVE_SECONDS), printed)
        self.assertIn(self.tool.progress_line(played=2, length=WAVE_SECONDS), printed)
        self.assertTrue(printed.endswith(self.tool.progress_line(played=WAVE_SECONDS, length=WAVE_SECONDS) + self.tool.LINE_END))

    def test_ctrl_c_stops_afplay_and_says_so(self):
        player = FakePlayer(polls=10, interrupt_after=1)
        code, printed = self.play_with(player=player, seconds=WAVE_SECONDS)
        self.assertEqual(code, 0)
        self.assertTrue(player.terminated)
        self.assertIn(self.tool.STOPPED, printed)

    def test_a_file_the_wave_module_cannot_read_still_plays_with_no_line(self):
        code, printed = self.play_with(player=FakePlayer(polls=2), seconds=None)
        self.assertEqual(code, 0)
        self.assertNotIn(self.tool.BAR_TO_PLAY, printed)


if __name__ == '__main__':
    unittest.main()
