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

"""Each kind of export finds and replaces only its own earlier files, even when all four share a directory."""

import contextlib
import fnmatch
import io
import os
import tempfile
import unittest

from llamatron.music.note import Note
from llamatron.exporters.exports import (
    EXPORT_KINDS, EXPORT_KINDS_IN_HELP, EXPORT_LABELS, ExportKind, earlier_export, export_name, make_exporter, shown_export_path, remove_earlier_export,
)
from llamatron.grid.clip import Clip
from llamatron.grid.clip_grid import ClipGrid
from llamatron.grid.clip_row import ClipRow
from llamatron.grid.clip_column import ClipColumn

QUARTER = 0.25
C4 = Note(name='C', octave_number=4, length=QUARTER)
SONG_NAME = 'tune'
# What the files are named after, as the program names a song's exports: <set>_<song>.
EXPORT = 'my_set_tune'
TRACK = 'lead'
AN_EXISTING_FILE = 'notes.txt'

# Names the tests give to their own things, and other values they use.
WRITE_TEXT = 'w'
# The kinds exported here: all but the WAV, which plays the song through FluidSynth, a program this computer may not have, and which test_wave_fluidsynth.py tests with a stand-in.
EXPORTED_HERE = [kind for kind in EXPORT_KINDS_IN_HELP if kind != ExportKind.WAV]


class TestExports(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = temporary.name
        self.grid = ClipGrid()
        track = self.grid.add_column(ClipColumn(name=TRACK))
        self.grid.set_clip(row=self.grid.add_row(ClipRow()), column=track, clip=Clip(notes=[C4]))

    def export_every_kind(self):
        with contextlib.redirect_stdout(io.StringIO()):
            for kind in EXPORTED_HERE:
                make_exporter(kind=kind, directory=self.directory, name=EXPORT, grid=self.grid).export()
        # The WAV's file stands in for what FluidSynth would write, so that its name is found as every kind's is.
        with open(shown_export_path(kind=ExportKind.WAV, directory=self.directory, name=EXPORT), WRITE_TEXT) as file:
            file.write(AN_EXISTING_FILE)

    def test_every_kind_has_a_name_and_the_tracker_offers_them_all_with_live_first(self):
        self.assertEqual(sorted(EXPORT_LABELS), sorted(EXPORT_KINDS_IN_HELP))
        self.assertEqual(sorted(EXPORT_KINDS), sorted(EXPORT_KINDS_IN_HELP))
        self.assertEqual(EXPORT_KINDS[0], ExportKind.ABLETON)

    def test_nothing_is_found_before_a_export(self):
        for kind in EXPORT_KINDS_IN_HELP:
            with self.subTest(kind=kind):
                self.assertEqual(earlier_export(kind=kind, directory=self.directory, name=EXPORT), [])

    def test_each_kind_finds_only_its_own_files(self):
        self.export_every_kind()
        found = {kind: earlier_export(kind=kind, directory=self.directory, name=EXPORT) for kind in EXPORT_KINDS_IN_HELP}
        for kind in EXPORT_KINDS_IN_HELP:
            with self.subTest(kind=kind):
                self.assertTrue(found[kind])
                for other in EXPORT_KINDS_IN_HELP:
                    if other != kind:
                        self.assertFalse(set(found[kind]) & set(found[other]))
        everything = sorted(path for paths in found.values() for path in paths)
        self.assertEqual(everything, sorted(os.path.join(self.directory, name) for name in os.listdir(self.directory)))

    def test_replacing_one_kind_leaves_the_others_and_any_other_file(self):
        self.export_every_kind()
        keep = os.path.join(self.directory, AN_EXISTING_FILE)
        with open(keep, WRITE_TEXT) as file:
            file.write(AN_EXISTING_FILE)
        for kind in EXPORTED_HERE:
            with self.subTest(kind=kind):
                others = [path for other in EXPORT_KINDS_IN_HELP if other != kind for path in earlier_export(kind=other, directory=self.directory, name=EXPORT)]
                remove_earlier_export(kind=kind, directory=self.directory, name=EXPORT)
                self.assertEqual(earlier_export(kind=kind, directory=self.directory, name=EXPORT), [])
                for path in others + [keep]:
                    self.assertTrue(os.path.exists(path))
                with contextlib.redirect_stdout(io.StringIO()):
                    make_exporter(kind=kind, directory=self.directory, name=EXPORT, grid=self.grid).export()

    def test_the_single_file_kinds_point_at_their_file_and_the_others_at_a_pattern_their_files_match(self):
        self.export_every_kind()
        for kind in [ExportKind.ABLETON, ExportKind.MIDI_FILE, ExportKind.GENERAL_MIDI]:
            with self.subTest(kind=kind):
                self.assertEqual(earlier_export(kind=kind, directory=self.directory, name=EXPORT), [shown_export_path(kind=kind, directory=self.directory, name=EXPORT)])
                self.assertTrue(os.path.isfile(shown_export_path(kind=kind, directory=self.directory, name=EXPORT)))
        for kind in [ExportKind.STEMS, ExportKind.CLIP_TREE]:
            with self.subTest(kind=kind):
                shown = shown_export_path(kind=kind, directory=self.directory, name=EXPORT)
                self.assertEqual(os.path.dirname(shown), self.directory)
                for path in earlier_export(kind=kind, directory=self.directory, name=EXPORT):
                    self.assertTrue(fnmatch.fnmatch(path, shown))

    def test_every_file_is_named_after_the_set_and_song(self):
        self.export_every_kind()
        self.assertEqual(sorted(os.listdir(self.directory)), [
            EXPORT + '.als', EXPORT + '.mid', EXPORT + '.wav', EXPORT + '_clip_s_001-t_001-lead.mid', EXPORT + '_gm.mid', EXPORT + '_stem_001-lead.mid',
        ])

    def test_the_name_is_the_set_then_the_song(self):
        self.assertEqual(export_name(setlist='my_set', song=SONG_NAME), EXPORT)


if __name__ == '__main__':
    unittest.main()
