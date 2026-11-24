# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""An instrument's preview pattern: how it starts, that it lives inside its instrument in the file and so is renamed, copied
and deleted with it, that the set reaches it only by its key, and that its edits reach the undo history."""

import unittest
import yaml

from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.file.setlist_writer import dump_setlist
from llamatron.model.objects import instrument_previews
from llamatron.model.objects.instrument import Instrument
from llamatron.model.objects.instrument_previews import PreviewOf, PreviewScale
from llamatron.model.objects.named_scale import scale_type_name
from llamatron.model.objects.setlist import Setlist
from llamatron.model.schema.file_format import InstrumentKind, InstrumentSetting, Row, Section, SoundEngine, SoundSetting
from llamatron.model.values.note import NoteName
from llamatron.model.values.scale import ScaleType

LEAD = 'lead'
COPY = 'lead copy'
RENAMED = 'solo'


def a_set():
    """Return a new set with one instrument, its preview made."""
    setlist = Setlist()
    setlist.add_item(section=Section.INSTRUMENTS, name=LEAD, item=Instrument())
    setlist.get_instrument(LEAD).make_preview()
    return setlist


class TestStartingPreviews(unittest.TestCase):

    def test_a_tonal_preview_runs_up_and_down_c_major_on_the_chromatic_scale(self):
        preview = Instrument()
        preview.make_preview()
        pattern = preview.get_preview()
        self.assertEqual(pattern.get_steps(), instrument_previews.PREVIEW_STEPS)
        self.assertFalse(pattern.is_drum())
        self.assertEqual(pattern.get_row(Row.DEGREE), [1, 3, 5, 6, 8, 10, 12, 1, 1, 12, 10, 8, 6, 5, 3, 1])
        self.assertEqual(pattern.get_row(Row.OCTAVE)[7], instrument_previews.PREVIEW_OCTAVE + 1)

    def test_a_drum_engines_preview_plays_c_on_each_quarter_in_the_default_drum_octave(self):
        drum = Instrument(kind=InstrumentKind.BUILT_IN, sound={SoundSetting.ENGINE: SoundEngine.DRUM})
        drum.make_preview()
        pattern = drum.get_preview()
        self.assertTrue(pattern.is_drum())
        played = [step for step, degree in enumerate(pattern.get_row(Row.DEGREE)) if degree == NoteName.C]
        self.assertEqual(played, [0, 4, 8, 12])
        self.assertFalse(any(pattern.get_row(Row.OCTAVE) or []))


class TestPreviewsInTheSet(unittest.TestCase):

    def test_the_set_reaches_a_preview_only_by_its_key_and_its_scale_is_chromatic_on_c(self):
        setlist = a_set()
        self.assertIs(setlist.get_pattern(PreviewOf(LEAD)), setlist.get_instrument(LEAD).get_preview())
        self.assertNotIn(LEAD, setlist.get_pattern_names())
        with self.assertRaises(InvalidValue):
            setlist.get_pattern(LEAD)
        scale = setlist.get_named_scale(PreviewScale())
        self.assertEqual(scale.get_root(), NoteName.C)
        self.assertEqual(scale.get_kind(), scale_type_name(ScaleType.CHROMATIC))

    def test_a_preview_is_written_inside_its_instrument_and_read_back(self):
        setlist = a_set()
        written = yaml.safe_load(dump_setlist(setlist.to_data()))
        self.assertIn(InstrumentSetting.PREVIEW, written[Section.INSTRUMENTS][0])
        again = Setlist.from_data(data=setlist.to_data())
        self.assertEqual(again.get_pattern(PreviewOf(LEAD)).to_data(), setlist.get_pattern(PreviewOf(LEAD)).to_data())

    def test_a_preview_is_renamed_copied_and_deleted_with_its_instrument(self):
        setlist = a_set()
        setlist.copy_item(section=Section.INSTRUMENTS, name=LEAD, new=COPY)
        self.assertIsNot(setlist.get_pattern(PreviewOf(COPY)), setlist.get_pattern(PreviewOf(LEAD)))
        setlist.rename_item(section=Section.INSTRUMENTS, old=LEAD, new=RENAMED)
        self.assertIsNotNone(setlist.get_pattern(PreviewOf(RENAMED)))
        with self.assertRaises(InvalidValue):
            setlist.get_pattern(PreviewOf(LEAD))
        setlist.remove_item(section=Section.INSTRUMENTS, name=RENAMED)
        with self.assertRaises(InvalidValue):
            setlist.get_pattern(PreviewOf(RENAMED))

    def test_an_edit_to_a_preview_reaches_the_sets_kept_data(self):
        setlist = a_set()
        before = setlist.kept_data()
        setlist.get_pattern(PreviewOf(LEAD)).set_value(row=Row.DEGREE, step=0, value=5)
        after = setlist.kept_data()
        self.assertNotEqual(before[Section.INSTRUMENTS][LEAD][InstrumentSetting.PREVIEW], after[Section.INSTRUMENTS][LEAD][InstrumentSetting.PREVIEW])
