# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The check of named values finds a number or a name typed in place, and passes over a line that names a value."""

import importlib.util
import pathlib
import unittest

TOOL = pathlib.Path(__file__).resolve().parent.parent.parent / "internal_tools" / "check_named_values.py"
SPEC = importlib.util.spec_from_file_location("check_named_values", TOOL)
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class NamedValuesTest(unittest.TestCase):
    """What a Rust line types in place, by what the check reports of it."""

    def test_a_name_typed_as_text_is_found(self):
        self.assertEqual(CHECK.breakages('    let second = asheville("osc2_pitch", amount);'), ['"osc2_pitch"'])

    def test_a_number_other_than_zero_or_one_is_found(self):
        self.assertEqual(CHECK.breakages("    run(cutoff, 48000);"), ["48000"])

    def test_zero_and_one_pass(self):
        self.assertEqual(CHECK.breakages("    let first = values[0] + 1.0;"), [])

    def test_a_line_naming_a_value_passes(self):
        self.assertEqual(CHECK.breakages("const PREVIEW_CHANNEL: i64 = 15;"), [])
        self.assertEqual(CHECK.breakages("    let shown_rows = 7;"), [])

    def test_shown_text_and_comments_pass(self):
        self.assertEqual(CHECK.breakages('    assert!(moved, "the A gauge moves Slow"); // 48 kHz'), [])

    def test_the_places_that_define_names_are_passed_over(self):
        self.assertTrue(CHECK.passed_over("src/names/src/lib.rs"))
        self.assertFalse(CHECK.passed_over("src/tracker/src/sound_spec.rs"))


if __name__ == "__main__":
    unittest.main()
