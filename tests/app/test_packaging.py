# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The installed package has to carry its template and its llamatron command."""

import contextlib
import io
from pathlib import Path
import tomllib
import unittest

import llamatron
from llamatron.cli import main
from llamatron.exporters import ableton_project

ROOT = Path(__file__).resolve().parents[2]
PROJECT_FILE = 'pyproject.toml'
PACKAGE = 'llamatron'
COMMAND = 'llamatron.cli:main'


class TestPackaging(unittest.TestCase):

    def project(self):
        return tomllib.loads((ROOT / PROJECT_FILE).read_text(encoding='utf-8'))

    def test_the_template_is_inside_the_package(self):
        self.assertTrue(ableton_project.DEFAULT_TEMPLATE.is_file())
        self.assertTrue(ableton_project.DEFAULT_TEMPLATE.is_relative_to(Path(llamatron.__file__).parent))

    def test_setup_includes_the_template(self):
        patterns = self.project()['tool']['setuptools']['package-data'][PACKAGE]
        folder = Path(llamatron.__file__).parent
        self.assertTrue(any(ableton_project.DEFAULT_TEMPLATE in folder.glob(pattern) for pattern in patterns))

    def test_setup_adds_the_llamatron_command(self):
        self.assertEqual(self.project()['project']['scripts'], {PACKAGE: COMMAND})

    def test_the_command_calls_itself_llamatron(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            main(argv=['--help'])
        self.assertIn('usage: llamatron', out.getvalue())


if __name__ == '__main__':
    unittest.main()
