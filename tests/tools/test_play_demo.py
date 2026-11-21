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

"""internal_tools/play_demo.py, one quick check of its main path: the list numbers the wave files by name and plays the one typed. A tool fails loudly when it is run, so one check is enough (.claude/TESTING.md)."""

import contextlib
import importlib.util
import io
import os
import pathlib
import tempfile
import unittest
from unittest import mock


SCRIPT = pathlib.Path(__file__).resolve().parent.parent.parent / 'internal_tools' / 'play_demo.py'
MODULE_NAME = 'play_demo'
# Demos' WAV files of the test's own, written out of order, and a file that isn't one.
WAVES = ['strum.wav', 'arpeggiator.wav', 'hocket_shanty.wav']
NOT_A_WAVE = 'strum.mid'
SECOND = '2'


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

if __name__ == '__main__':
    unittest.main()
