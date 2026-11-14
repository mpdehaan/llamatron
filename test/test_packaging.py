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

"""The installed package has to carry its template and its llamatron command."""

import ast
import contextlib
import io
import unittest
from pathlib import Path

import llamatron
from llamatron.cli import main
from llamatron.exporters.ableton_project import DEFAULT_TEMPLATE

ROOT = Path(__file__).resolve().parents[1]


class TestPackaging(unittest.TestCase):

    def setup_settings(self):
        tree = ast.parse((ROOT / 'setup.py').read_text(encoding='utf-8'))
        call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, 'id', '') == 'setup')
        return call.keywords

    def setting(self, name):
        return ast.literal_eval(next(k.value for k in self.setup_settings() if k.arg == name))

    def test_the_template_is_inside_the_package(self):
        self.assertTrue(DEFAULT_TEMPLATE.is_file())
        self.assertTrue(DEFAULT_TEMPLATE.is_relative_to(Path(llamatron.__file__).parent))

    def test_setup_includes_the_template(self):
        patterns = self.setting('package_data')['llamatron']
        folder = Path(llamatron.__file__).parent
        self.assertTrue(any(DEFAULT_TEMPLATE in folder.glob(pattern) for pattern in patterns))

    def test_setup_adds_the_llamatron_command(self):
        self.assertEqual(self.setting('entry_points'), {'console_scripts': ['llamatron = llamatron.cli:main']})

    def test_the_command_calls_itself_llamatron(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            main(argv=['--help'])
        self.assertIn('usage: llamatron', out.getvalue())


if __name__ == '__main__':
    unittest.main()
