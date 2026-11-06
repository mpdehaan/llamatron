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

"""llamatron's version: three whole numbers separated by dots, shown in the title and saved in files."""

import os
import tempfile
import unittest

import yaml

from llamatron.composition.song import Song
from llamatron.composition.song_file_error import SongFileError
from llamatron.song_writer import dump_song
from llamatron.tui.base import TITLE
from llamatron.tui.document import Document
from llamatron.version import VERSION, is_version, version_numbers


class TestVersion(unittest.TestCase):

    def test_the_version_is_three_whole_numbers(self):
        self.assertTrue(is_version(VERSION))
        self.assertEqual(len(version_numbers(VERSION)), 3)

    def test_versions_compare_number_by_number_not_as_decimals(self):
        self.assertGreater(version_numbers('1.0.10'), version_numbers('1.0.9'))
        self.assertGreater(version_numbers('2.0.0'), version_numbers('1.99.99'))

    def test_anything_else_is_not_a_version(self):
        for text in ['1.0', '1.0.2.3', '1.0.x', '1.0.-2', '', ' 1.0.2', 1.02, None]:
            with self.subTest(text=text):
                self.assertFalse(is_version(text))
        with self.assertRaises(ValueError):
            version_numbers('1.0')

    def test_the_title_shows_the_version(self):
        self.assertEqual(TITLE, f'llamatron {VERSION}')

    def test_a_saved_file_records_the_version_and_reads_back(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'song.yml')
            Document().save(path)
            with open(path) as file:
                text = file.read()
            self.assertTrue(text.startswith(f'version: {VERSION}\n'))
            self.assertEqual(yaml.safe_load(text)['version'], VERSION)
            Song.read_file(path)

    def test_a_song_file_with_a_bad_version_is_refused(self):
        with self.assertRaisesRegex(SongFileError, 'version: expected three whole numbers'):
            Song.from_data({'version': '1.0'})

    def test_a_version_like_1_0_2_stays_text_when_written(self):
        self.assertEqual(yaml.safe_load(dump_song({'version': '1.0.2', 'tracks': {}, 'scenes': []}))['version'], '1.0.2')


if __name__ == '__main__':
    unittest.main()
