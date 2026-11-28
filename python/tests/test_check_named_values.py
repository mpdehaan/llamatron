# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The check of named values reports exactly the lines of a sample of Rust that type a value in place.

The sample, `data/named_values_sample.rs`, marks each line the check must report with the comment `flagged`.
"""

import importlib.util
import pathlib
import unittest

HERE = pathlib.Path(__file__).resolve().parent
TOOL = HERE.parent.parent / "internal_tools" / "check_named_values.py"
SAMPLE = HERE / "data" / "named_values_sample.rs"
FLAGGED_MARK = "// flagged"
SPEC = importlib.util.spec_from_file_location("check_named_values", TOOL)
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class NamedValuesTest(unittest.TestCase):
    """What the check reports of the sample, line by line."""

    def test_exactly_the_marked_lines_are_reported(self):
        text = SAMPLE.read_text()
        definitions = CHECK.definition_lines(text)
        reported, marked = set(), set()
        for number, line in enumerate(text.splitlines(), 1):
            if FLAGGED_MARK in line:
                marked.add(number)
            if number not in definitions and CHECK.breakages(line):
                reported.add(number)
        self.assertEqual(reported, marked)

    def test_the_places_that_define_names_are_passed_over(self):
        self.assertTrue(CHECK.passed_over("src/names/src/lib.rs"))
        self.assertFalse(CHECK.passed_over("src/tracker/src/sound_spec.rs"))


if __name__ == "__main__":
    unittest.main()
