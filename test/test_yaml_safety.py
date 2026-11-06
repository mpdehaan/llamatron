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

"""Loading YAML must never run code, so only PyYAML's safe functions are used anywhere.

yaml.load with the wrong loader, yaml.unsafe_load and yaml.full_load can build arbitrary Python
objects from a file, which lets a song file run code. yaml.safe_load only makes plain data.
"""

import glob
import os
import re
import tempfile
import unittest
from pathlib import Path

from llamatron.composition.song_file_error import SongFileError
from rendering import render_file
from llamatron.tui.document import Document

ROOT = Path(__file__).resolve().parent.parent
UNSAFE = re.compile(r'yaml\.(load|load_all|full_load|full_load_all|unsafe_load|unsafe_load_all)\s*\(|Loader\s*=|\bUnsafeLoader\b|\bFullLoader\b')


class TestYamlSafety(unittest.TestCase):

    def test_no_python_file_uses_an_unsafe_yaml_loader(self):
        files = [Path(path) for pattern in ('src/**/*.py', 'test/**/*.py', '*.py')
                 for path in glob.glob(str(ROOT / pattern), recursive=True)]
        self.assertTrue(files)
        for path in files:
            if path.name == 'test_yaml_safety.py':
                continue
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1):
                with self.subTest(file=str(path.relative_to(ROOT)), line=number):
                    self.assertIsNone(UNSAFE.search(line), line.strip())

    def test_a_song_file_that_asks_to_run_code_is_refused(self):
        # A tag like this makes an unsafe loader run a shell command while reading the file.
        text = 'tempo: !!python/object/apply:os.system ["echo unsafe"]\n'
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'unsafe.yml')
            with open(path, 'w') as file:
                file.write(text)
            with self.assertRaises(SongFileError):
                Document.load(path)
            with self.assertRaises(SongFileError):
                render_file(path)


if __name__ == '__main__':
    unittest.main()
