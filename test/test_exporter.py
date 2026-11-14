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
"""The base class every exporter shares, and the rule that every exporter is listed.

exporters/exporter.py holds what the four kinds of export have in common: the directory, the
grid and the name, the check for files in the way, and where a kind's files are, for a kind that
writes one file (WritesOneFile) or several (WritesManyFiles). exporters/exports.py lists the
classes, and the rule here is that no exporter class is left out of that list, so that a new kind
can't be written and then forgotten by --to and the tracker's export dialog.
"""

import contextlib
import importlib
import inspect
import io
import os
import pkgutil
import tempfile
import unittest

import llamatron.exporters
from llamatron.exporters.ableton_project import DEFAULT_TEMPLATE, AbletonProject
from llamatron.exporters.clip_tree import ClipTree
from llamatron.exporters.exporter import Exporter, ExportKind, WritesManyFiles, WritesOneFile
from llamatron.exporters.midi_arrangement import MidiGeneralMidi, MidiSong, MidiStems
from llamatron.exporters.wave_fluidsynth import WaveFluidSynth
from llamatron.exporters.exports import EXPORT_KINDS, EXPORTERS, EXPORT_KINDS_IN_HELP, EXPORT_LABELS
from llamatron.grid.clip_grid import ClipGrid
from llamatron.strings.errors import ERR_BAD_DIRECTORY, ERR_FILES_EXIST, ERR_NEEDS_EXPORT, ERR_NEEDS_FILES, ERR_NOT_A_GRID
from llamatron.support.files import FILE_ENCODING, WRITE_TEXT

EXPORT = 'my_set_tune'
SUBFOLDER = 'out'
HERE = '.'
OTHER_TEMPLATE = 'other.als'
AN_EXISTING_FILE = 'notes.txt'
# A directory whose name holds the characters a glob pattern gives a meaning to.
GLOB_CHARACTERS = 'takes [1] *'
FIRST_PART = 1
SECOND_PART = 2
NOT_A_GRID = 'not a grid'


class OneNote(WritesOneFile, Exporter):
    """A kind of export made for this test: one text file holding the name. A new kind is this much."""

    __slots__ = ()

    KIND = 'one note'
    LABEL = 'One note'
    FILE = '{name}.note'

    def export(self):
        if self.can_write([os.path.basename(self.path())]):
            write(path=self.path(), text=self.get_name())


class ManyNotes(WritesManyFiles, Exporter):
    """A kind of export made for this test: two numbered text files."""

    __slots__ = ()

    KIND = 'many notes'
    LABEL = 'Many notes'
    PART = '{name}_part_{number}.note'
    FILES = '{name}_part_[0-9]*.note'
    FILES_SHOWN = '{name}_part_*.note'

    def filenames(self):
        return [self.PART.format(name=self.get_name(), number=number) for number in (FIRST_PART, SECOND_PART)]

    def export(self):
        if self.can_write(self.filenames()):
            for filename in self.filenames():
                write(path=os.path.join(self.get_directory(), filename), text=filename)


def write(*, path, text):
    with open(path, WRITE_TEXT, encoding=FILE_ENCODING) as file:
        file.write(text)


def exporter_classes():
    """Return every class of the exporters package that says which kind of export it is."""
    found = []
    for module_info in pkgutil.iter_modules(llamatron.exporters.__path__, llamatron.exporters.__name__ + '.'):
        module = importlib.import_module(module_info.name)
        for _, kind in inspect.getmembers(module, inspect.isclass):
            if issubclass(kind, Exporter) and kind.__module__ == module.__name__ and kind.KIND is not None:
                found.append(kind)
    return found


def printed_by(action):
    """Run something, and return what it returned and what it printed."""
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        result = action()
    return result, output.getvalue().strip()


class TestEveryExporterIsListed(unittest.TestCase):

    def test_every_exporter_class_is_listed_under_its_kind_and_nothing_else_is(self):
        self.assertEqual(set(exporter_classes()), set(EXPORTERS.values()))
        self.assertEqual({AbletonProject, MidiSong, MidiStems, ClipTree, MidiGeneralMidi, WaveFluidSynth}, set(EXPORTERS.values()))
        for kind, exporter in EXPORTERS.items():
            with self.subTest(kind=kind):
                self.assertEqual(exporter.KIND, kind)

    def test_every_kind_is_offered_by_the_command_line_and_the_tracker_and_has_a_label(self):
        named = {value for name, value in vars(ExportKind).items() if not name.startswith('_')}
        self.assertEqual(set(EXPORT_KINDS_IN_HELP), named)
        self.assertEqual(sorted(EXPORT_KINDS), sorted(EXPORT_KINDS_IN_HELP))
        for kind in EXPORT_KINDS_IN_HELP:
            with self.subTest(kind=kind):
                self.assertTrue(EXPORT_LABELS[kind])
                self.assertEqual(EXPORT_LABELS[kind], EXPORTERS[kind].LABEL)

    def test_the_live_set_comes_first_since_it_is_the_default(self):
        self.assertEqual(EXPORT_KINDS_IN_HELP[0], ExportKind.ABLETON)
        self.assertEqual(EXPORT_KINDS[0], ExportKind.ABLETON)

    def test_every_exporter_says_where_its_files_are(self):
        for exporter in EXPORTERS.values():
            with self.subTest(exporter=exporter.__name__):
                self.assertTrue(issubclass(exporter, (WritesOneFile, WritesManyFiles)))
                self.assertIn(EXPORT, exporter.shown_path(directory=SUBFOLDER, name=EXPORT))


class TestExporter(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = temporary.name
        self.grid = ClipGrid()

    def test_the_base_class_alone_exports_nothing_and_says_what_a_subclass_needs(self):
        exporter = Exporter(directory=self.directory, grid=self.grid)
        with self.assertRaises(NotImplementedError) as raised:
            exporter.export()
        self.assertEqual(str(raised.exception), ERR_NEEDS_EXPORT.format(kind=Exporter.__name__))
        for question in (Exporter.shown_path, Exporter.earlier_files, Exporter.remove_earlier_files):
            with self.subTest(question=question.__name__):
                with self.assertRaises(NotImplementedError) as raised:
                    question(directory=self.directory, name=EXPORT)
                self.assertEqual(str(raised.exception), ERR_NEEDS_FILES.format(kind=Exporter.__name__))

    def test_the_directory_and_the_grid_are_checked_when_given_and_when_set(self):
        with self.assertRaises(ValueError) as raised:
            Exporter(directory=None, grid=self.grid)
        self.assertEqual(str(raised.exception), ERR_BAD_DIRECTORY.format(value=None))
        with self.assertRaises(ValueError) as raised:
            Exporter(directory=self.directory, grid=NOT_A_GRID)
        self.assertEqual(str(raised.exception), ERR_NOT_A_GRID.format(value=NOT_A_GRID))
        exporter = Exporter(directory=self.directory, grid=self.grid)
        other = ClipGrid()
        exporter.set_directory(SUBFOLDER)
        exporter.set_grid(other)
        self.assertEqual(exporter.get_directory(), SUBFOLDER)
        self.assertIs(exporter.get_grid(), other)
        with self.assertRaises(ValueError):
            exporter.set_grid(None)
        self.assertIs(exporter.get_grid(), other)

    def test_the_files_take_the_name_given_or_else_the_directorys(self):
        self.assertEqual(Exporter(directory=self.directory, grid=self.grid, name=EXPORT).get_name(), EXPORT)
        self.assertEqual(Exporter(directory=os.path.join(self.directory, SUBFOLDER), grid=self.grid).get_name(), SUBFOLDER)
        self.assertEqual(Exporter(directory=os.path.join(self.directory, SUBFOLDER) + os.sep, grid=self.grid).get_name(), SUBFOLDER)
        # The directory the program was started in has a name too, which a dot doesn't say.
        self.assertEqual(Exporter(directory=HERE, grid=self.grid).get_name(), os.path.basename(os.getcwd()))

    def test_only_the_live_set_is_built_from_a_template(self):
        live = AbletonProject.for_song(directory=self.directory, grid=self.grid, name=EXPORT, template=OTHER_TEMPLATE)
        self.assertEqual(live.get_template(), OTHER_TEMPLATE)
        self.assertEqual(AbletonProject.for_song(directory=self.directory, grid=self.grid, name=EXPORT).get_template(), DEFAULT_TEMPLATE)
        for exporter in (MidiSong, MidiStems, ClipTree):
            with self.subTest(exporter=exporter.__name__):
                made = exporter.for_song(directory=self.directory, grid=self.grid, name=EXPORT, template=OTHER_TEMPLATE)
                self.assertIsInstance(made, exporter)
                self.assertEqual(made.get_name(), EXPORT)

    def test_files_can_be_written_when_none_is_in_the_way_and_the_directory_is_made(self):
        nested = os.path.join(self.directory, SUBFOLDER)
        exporter = Exporter(directory=nested, grid=self.grid)
        can, printed = printed_by(lambda: exporter.can_write([AN_EXISTING_FILE]))
        self.assertTrue(can)
        self.assertEqual(printed, '')
        self.assertTrue(os.path.isdir(nested))

    def test_a_file_in_the_way_stops_the_export_with_a_warning_naming_it(self):
        write(path=os.path.join(self.directory, AN_EXISTING_FILE), text=EXPORT)
        exporter = Exporter(directory=self.directory, grid=self.grid)
        can, printed = printed_by(lambda: exporter.can_write([AN_EXISTING_FILE, EXPORT]))
        self.assertFalse(can)
        self.assertEqual(printed, ERR_FILES_EXIST.format(directory=self.directory, files=AN_EXISTING_FILE))


class TestANewKindOfExport(unittest.TestCase):
    """The two kinds made for this test, which need only their names and what they write."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = os.path.join(temporary.name, GLOB_CHARACTERS)
        os.makedirs(self.directory)
        write(path=os.path.join(self.directory, AN_EXISTING_FILE), text=EXPORT)
        self.grid = ClipGrid()

    def others(self):
        return sorted(os.listdir(self.directory))

    def test_a_kind_that_writes_one_file(self):
        exporter = OneNote(directory=self.directory, grid=self.grid, name=EXPORT)
        path = os.path.join(self.directory, OneNote.FILE.format(name=EXPORT))
        self.assertEqual(exporter.path(), path)
        self.assertEqual(OneNote.shown_path(directory=self.directory, name=EXPORT), path)
        self.assertEqual(OneNote.earlier_files(directory=self.directory, name=EXPORT), [])
        exporter.export()
        self.assertEqual(OneNote.earlier_files(directory=self.directory, name=EXPORT), [path])
        # A second export finds the file in the way and writes nothing.
        _, printed = printed_by(exporter.export)
        self.assertEqual(printed, ERR_FILES_EXIST.format(directory=self.directory, files=os.path.basename(path)))
        OneNote.remove_earlier_files(directory=self.directory, name=EXPORT)
        self.assertEqual(self.others(), [AN_EXISTING_FILE])

    def test_a_kind_that_writes_several_files(self):
        exporter = ManyNotes(directory=self.directory, grid=self.grid, name=EXPORT)
        self.assertEqual(ManyNotes.shown_path(directory=self.directory, name=EXPORT), os.path.join(self.directory, ManyNotes.FILES_SHOWN.format(name=EXPORT)))
        self.assertEqual(ManyNotes.earlier_files(directory=self.directory, name=EXPORT), [])
        exporter.export()
        written = [os.path.join(self.directory, filename) for filename in exporter.filenames()]
        # The directory's name holds brackets and a star, which the pattern takes as they are.
        self.assertEqual(ManyNotes.earlier_files(directory=self.directory, name=EXPORT), written)
        # Another song's files, and another kind's, are not this export's.
        OneNote(directory=self.directory, grid=self.grid, name=EXPORT).export()
        self.assertEqual(ManyNotes.earlier_files(directory=self.directory, name=EXPORT), written)
        self.assertEqual(ManyNotes.earlier_files(directory=self.directory, name=SUBFOLDER), [])
        ManyNotes.remove_earlier_files(directory=self.directory, name=EXPORT)
        self.assertEqual(self.others(), sorted([AN_EXISTING_FILE, OneNote.FILE.format(name=EXPORT)]))


if __name__ == '__main__':
    unittest.main()
