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

"""Loading YAML must never run code, so only PyYAML's safe loaders are used anywhere.

yaml.load with the wrong loader, yaml.unsafe_load and yaml.full_load can build arbitrary Python
objects from a file, which lets a song file run code. yaml.safe_load only makes plain data, and
so does llamatron.safe_yaml.load_safely, which is the one place that names a loader: SafeLoader,
or CSafeLoader when PyYAML has libyaml, which is the same safe loader on a faster parser.
"""

import glob
import os
import re
import tempfile
import unittest
from pathlib import Path

import yaml

from llamatron.composition.song_file_error import SongFileError
from llamatron.safe_yaml import SAFE_LOADER, load_safely, uses_c_parser
from rendering import render_file
from llamatron.tui.document import Document

ROOT = Path(__file__).resolve().parent.parent
# The one module allowed to name a loader, and the loaders it may name.
LOADER_MODULE = 'safe_yaml.py'
SAFE_LOADERS = [yaml.SafeLoader, getattr(yaml, 'CSafeLoader', yaml.SafeLoader)]
# A tag like this makes an unsafe loader run a shell command while reading the file.
RUNS_CODE = 'tempo: !!python/object/apply:os.system ["echo unsafe"]\n'
EXAMPLES = sorted(glob.glob(str(ROOT / 'examples' / '*.yml')))
UNSAFE = re.compile(r'yaml\.(load|load_all|full_load|full_load_all|unsafe_load|unsafe_load_all)\s*\(|Loader\s*=|\bUnsafeLoader\b|\bFullLoader\b')


class TestYamlSafety(unittest.TestCase):

    def test_no_python_file_uses_an_unsafe_yaml_loader(self):
        files = [Path(path) for pattern in ('src/**/*.py', 'test/**/*.py', 'tools/**/*.py', '*.py')
                 for path in glob.glob(str(ROOT / pattern), recursive=True)]
        self.assertTrue(files)
        for path in files:
            if path.name in (Path(__file__).name, LOADER_MODULE):
                continue
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1):
                with self.subTest(file=str(path.relative_to(ROOT)), line=number):
                    self.assertIsNone(UNSAFE.search(line), line.strip())

    def test_the_loader_in_use_is_one_of_the_safe_ones(self):
        self.assertIn(SAFE_LOADER, SAFE_LOADERS)
        self.assertEqual(uses_c_parser(), SAFE_LOADER is not yaml.SafeLoader)

    def test_load_safely_refuses_to_run_code(self):
        with self.assertRaises(yaml.YAMLError):
            load_safely(RUNS_CODE)

    def test_load_safely_reads_every_example_as_safe_load_does(self):
        # Whichever parser is in use, it has to agree with the pure-Python one on real files.
        self.assertTrue(EXAMPLES)
        for path in EXAMPLES:
            with self.subTest(path=path), open(path) as first, open(path) as second:
                self.assertEqual(load_safely(first), yaml.safe_load(second))

    def test_a_song_file_that_asks_to_run_code_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'unsafe.yml')
            with open(path, 'w') as file:
                file.write(RUNS_CODE)
            with self.assertRaises(SongFileError):
                Document.load(path)
            with self.assertRaises(SongFileError):
                render_file(path)


if __name__ == '__main__':
    unittest.main()
