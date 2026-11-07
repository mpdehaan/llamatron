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

"""Each kind of output finds and replaces only its own earlier files, even when all four share a directory."""

import contextlib
import io
import os
import tempfile
import unittest

from llamatron.note import Note
from llamatron.renderers.outputs import (
    MIDI_KINDS, OUTPUT_KINDS, OUTPUT_NAMES, OutputKind, earlier_output, make_writer, output_path, replace_output,
)
from llamatron.clip_grid import Clip, ClipGrid, Scene, Track

QUARTER = 0.25
C4 = Note('C', 4, QUARTER)
SONG_NAME = 'tune'
TRACK = 'lead'
AN_EXISTING_FILE = 'notes.txt'


class TestOutputs(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = os.path.join(temporary.name, SONG_NAME)
        self.grid = ClipGrid()
        track = self.grid.add_track(Track(TRACK))
        self.grid.set_clip(self.grid.add_scene(Scene()), track, Clip(notes=[C4]))

    def render_every_kind(self):
        with contextlib.redirect_stdout(io.StringIO()):
            for kind in OUTPUT_KINDS:
                make_writer(kind, self.directory, self.grid).render()

    def test_every_kind_has_a_name_and_the_midi_kinds_are_among_them(self):
        self.assertEqual(sorted(OUTPUT_NAMES), sorted(OUTPUT_KINDS))
        for kind in MIDI_KINDS:
            self.assertIn(kind, OUTPUT_KINDS)
        self.assertNotIn(OutputKind.ABLETON, MIDI_KINDS)

    def test_nothing_is_found_before_a_render(self):
        for kind in OUTPUT_KINDS:
            with self.subTest(kind=kind):
                self.assertEqual(earlier_output(kind, self.directory), [])

    def test_each_kind_finds_only_its_own_files(self):
        self.render_every_kind()
        found = {kind: earlier_output(kind, self.directory) for kind in OUTPUT_KINDS}
        for kind in OUTPUT_KINDS:
            with self.subTest(kind=kind):
                self.assertTrue(found[kind])
                for other in OUTPUT_KINDS:
                    if other != kind:
                        self.assertFalse(set(found[kind]) & set(found[other]))
        everything = sorted(path for paths in found.values() for path in paths)
        self.assertEqual(everything, sorted(os.path.join(self.directory, name) for name in os.listdir(self.directory)))

    def test_replacing_one_kind_leaves_the_others_and_any_other_file(self):
        self.render_every_kind()
        keep = os.path.join(self.directory, AN_EXISTING_FILE)
        with open(keep, 'w') as file:
            file.write(AN_EXISTING_FILE)
        for kind in OUTPUT_KINDS:
            with self.subTest(kind=kind):
                others = [path for other in OUTPUT_KINDS if other != kind for path in earlier_output(other, self.directory)]
                replace_output(kind, self.directory)
                self.assertEqual(earlier_output(kind, self.directory), [])
                for path in others + [keep]:
                    self.assertTrue(os.path.exists(path))
                with contextlib.redirect_stdout(io.StringIO()):
                    make_writer(kind, self.directory, self.grid).render()

    def test_the_single_file_kinds_point_at_their_file_and_the_others_at_the_directory(self):
        self.render_every_kind()
        for kind in [OutputKind.ABLETON, OutputKind.MIDI_FILE]:
            with self.subTest(kind=kind):
                self.assertEqual(earlier_output(kind, self.directory), [output_path(kind, self.directory)])
                self.assertTrue(os.path.isfile(output_path(kind, self.directory)))
        for kind in [OutputKind.STEMS, OutputKind.CLIP_TREE]:
            with self.subTest(kind=kind):
                self.assertEqual(output_path(kind, self.directory), self.directory)


if __name__ == '__main__':
    unittest.main()
