# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The batch importer (user_scripts/batch_importer.sh): every MIDI file under a folder, at any depth, imported into set files
in one flat folder, or into one set, and the files it cannot import said and passed over."""

import contextlib
import io
import os
import tempfile
import unittest

from llamatron.importers import batch_import
from llamatron.model.objects.setlist import Setlist
from tests.importers.test_midi_import import melody, midi_of

FOLDER = 'old_songs'
TUNE = 'tune'
OTHER = 'other'
BROKEN = 'broken'
MIDI_SUFFIX = '.mid'
SET_SUFFIX = '.yml'
WRITE_BYTES = 'wb'
NOT_MIDI = b'not a MIDI file'


class TestBatchImport(unittest.TestCase):

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.input_dir = os.path.join(self.temporary.name, FOLDER)
        self.output_dir = os.path.join(self.temporary.name, 'sets')
        nested = os.path.join(self.input_dir, 'deeper')
        os.makedirs(nested)
        midi_of(tracks=[('lead', 0, melody(pitches=[60, 62, 64, 65]))]).save(os.path.join(self.input_dir, TUNE + MIDI_SUFFIX))
        midi_of(tracks=[('lead', 0, melody(pitches=[67, 65, 64, 62]))]).save(os.path.join(nested, OTHER + MIDI_SUFFIX))
        with open(os.path.join(self.input_dir, BROKEN + MIDI_SUFFIX), WRITE_BYTES) as file:
            file.write(NOT_MIDI)

    def run_importer(self, *extra):
        said = io.StringIO()
        with contextlib.redirect_stdout(said):
            batch_import.main(arguments=[batch_import.OPTION_INPUT, self.input_dir, batch_import.OPTION_OUTPUT, self.output_dir, *extra])
        return said.getvalue()

    def test_each_file_is_a_set_of_its_own_in_a_flat_folder_with_its_song_named_after_it(self):
        said = self.run_importer()
        written = sorted(os.listdir(self.output_dir))
        self.assertEqual(written, ['deeper' + batch_import.FOLDER_JOIN + OTHER + SET_SUFFIX, TUNE + SET_SUFFIX])
        setlist = Setlist.read_file(os.path.join(self.output_dir, TUNE + SET_SUFFIX))
        self.assertEqual(setlist.get_song_names(), [TUNE])
        self.assertIn(BROKEN, said)

    def test_every_file_can_be_a_song_of_one_set_named_after_the_folder(self):
        self.run_importer(batch_import.OPTION_ONE_SET)
        self.assertEqual(os.listdir(self.output_dir), [FOLDER + SET_SUFFIX])
        setlist = Setlist.read_file(os.path.join(self.output_dir, FOLDER + SET_SUFFIX))
        self.assertEqual(sorted(setlist.get_song_names()), [OTHER, TUNE])

    def test_the_longest_pattern_and_the_finest_grid_are_asked_for_and_refused_when_wrong(self):
        options = batch_import.parser().parse_args([batch_import.OPTION_INPUT, FOLDER, batch_import.OPTION_OUTPUT, FOLDER])
        self.assertEqual(options.bars_per_pattern, batch_import.midi_import_values.WIZARD_LONGEST_BARS)
        self.assertEqual(options.quantize, batch_import.cutting.FINEST_STEP_SIZE)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            batch_import.parser().parse_args([batch_import.OPTION_INPUT, FOLDER, batch_import.OPTION_OUTPUT, FOLDER, batch_import.OPTION_QUANTIZE, '1/128'])
