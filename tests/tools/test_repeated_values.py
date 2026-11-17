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
"""internal_tools/repeated_values.py lists the strings written out in Python source that repeat a value the program already names."""

import importlib.util
import pathlib
import unittest

from llamatron.composition.file_format import PatternSetting, ScaleSetting
from llamatron.music.note import NoteName

SCRIPT = pathlib.Path(__file__).resolve().parent.parent.parent / 'internal_tools' / 'repeated_values.py'
MODULE_NAME = 'repeated_values'
# Source that writes two of the program's values out, names a third by its constant and holds a word of its own.
SOURCE = '''"""A docstring that says {steps} and is left alone."""
data = {{{root!r}: {note!r}}}
steps = PatternSetting.STEPS
own = 'a word of the test alone'
'''.format(steps=PatternSetting.STEPS, root=ScaleSetting.ROOT, note=NoteName.A)
DATA_LINE = 2


def load_tool():
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestRepeatedValues(unittest.TestCase):

    def setUp(self):
        self.tool = load_tool()
        self.values = self.tool.named_values()

    def test_the_programs_values_are_known_by_the_constant_that_names_each(self):
        self.assertIn(ScaleSetting.ROOT, self.values)
        self.assertIn(NoteName.A, self.values)
        self.assertTrue(self.values[PatternSetting.STEPS].endswith(self.tool.CONSTANT_NAME.format(owner='', name='STEPS')))

    def test_a_value_written_out_is_listed_with_its_line_and_a_docstring_and_a_tests_own_word_are_not(self):
        found = self.tool.repeated_in(source=SOURCE, values=self.values)
        self.assertEqual([(line, value) for line, value, _ in found], [(DATA_LINE, NoteName.A), (DATA_LINE, ScaleSetting.ROOT)])

    def test_source_that_names_every_value_lists_nothing(self):
        self.assertEqual(self.tool.repeated_in(source='steps = PatternSetting.STEPS\n', values=self.values), [])
