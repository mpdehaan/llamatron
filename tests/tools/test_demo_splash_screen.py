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

"""internal_tools/demo_splash_screen.py, one quick check of its main path: scroll text shows the words given after the title. A tool fails loudly when it is run, so one check is enough (.claude/TESTING.md)."""

import importlib.util
import pathlib
import unittest
from unittest import mock


SCRIPT = pathlib.Path(__file__).resolve().parent.parent.parent / 'internal_tools' / 'demo_splash_screen.py'
MODULE_NAME = 'demo_splash_screen'
SCROLL_FLAG = '--scroll-text'
SOME_WORDS = 'DEMO: Hocket Shanty'
SUCCESS = 0


def load_script():
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestDemoSplashScreen(unittest.TestCase):

    def setUp(self):
        self.tool = load_script()

    def launched_with(self, arguments):
        """Run the tool with the tracker replaced, and return the launch the tracker was given."""
        with mock.patch.object(self.tool, 'LlamatronApp') as app:
            self.assertEqual(self.tool.main(argv=arguments), SUCCESS)
        return app.call_args.kwargs['launch']

    def test_scroll_text_shows_the_words_given_after_the_title(self):
        launch = self.launched_with([SCROLL_FLAG, SOME_WORDS])
        self.assertTrue(launch.test_splash)
        self.assertEqual(launch.scroll_text, SOME_WORDS)

if __name__ == '__main__':
    unittest.main()
