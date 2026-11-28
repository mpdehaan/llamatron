# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The version bump writes the version module from its template, its last number one higher and its build time the
moment of the bump, and refuses a module that sets no version."""

import datetime
import importlib.util
import pathlib
import unittest

TOP = pathlib.Path(__file__).resolve().parent.parent.parent
TOOL = TOP / "internal_tools" / "bump_version.py"
SPEC = importlib.util.spec_from_file_location("bump_version", TOOL)
BUMP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUMP)


class BumpVersionTest(unittest.TestCase):
    """What a bump writes, read back as the program reads it."""

    def test_the_last_number_rises_and_the_build_time_is_now(self):
        text = (TOP / BUMP.VERSION_FILE).read_text()
        now = datetime.datetime.now()
        written = BUMP.bumped(text=text, now=now)
        first, second, last = BUMP.numbers_in(text)
        self.assertEqual(BUMP.numbers_in(written), [first, second, last + 1])
        self.assertIn(now.strftime(BUMP.DATE_FORMAT), written)
        self.assertIn(now.strftime(BUMP.TIME_FORMAT), written)

    def test_a_module_with_no_version_is_refused(self):
        with self.assertRaises(ValueError):
            BUMP.numbers_in("")


if __name__ == "__main__":
    unittest.main()
