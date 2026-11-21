# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The installed package has to carry its template and its llamatron command."""

import ast
import contextlib
import io
from pathlib import Path
import unittest

import llamatron
from llamatron.cli import main
from llamatron.exporters import ableton_project

ROOT = Path(__file__).resolve().parents[2]


class TestPackaging(unittest.TestCase):

    def setup_settings(self):
        tree = ast.parse((ROOT / 'setup.py').read_text(encoding='utf-8'))
        call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, 'id', '') == 'setup')
        return call.keywords

    def setting(self, name):
        return ast.literal_eval(next(k.value for k in self.setup_settings() if k.arg == name))

    def test_the_template_is_inside_the_package(self):
        self.assertTrue(ableton_project.DEFAULT_TEMPLATE.is_file())
        self.assertTrue(ableton_project.DEFAULT_TEMPLATE.is_relative_to(Path(llamatron.__file__).parent))

    def test_setup_includes_the_template(self):
        patterns = self.setting('package_data')['llamatron']
        folder = Path(llamatron.__file__).parent
        self.assertTrue(any(ableton_project.DEFAULT_TEMPLATE in folder.glob(pattern) for pattern in patterns))

    def test_setup_adds_the_llamatron_command(self):
        self.assertEqual(self.setting('entry_points'), {'console_scripts': ['llamatron = llamatron.cli:main']})

    def test_the_command_calls_itself_llamatron(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            main(argv=['--help'])
        self.assertIn('usage: llamatron', out.getvalue())


if __name__ == '__main__':
    unittest.main()
