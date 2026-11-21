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
"""internal_tools/show_keys.py, one quick check of its main path: every class is shown with every binding it lists. A tool fails loudly when it is run, so one check is enough (.claude/TESTING.md)."""

import contextlib
import importlib.util
import io
import pathlib
import unittest


SCRIPT = pathlib.Path(__file__).resolve().parent.parent.parent / 'internal_tools' / 'show_keys.py'
MODULE_NAME = 'show_keys'
SUCCESS = 0


def load_script():
    """Load the tool as a module, since internal_tools/ is not a package."""
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestShowKeys(unittest.TestCase):

    def setUp(self):
        self.tool = load_script()

    def shown(self, arguments, *, expected=SUCCESS):
        """Run the tool and return the lines it printed, checking what it exits with."""
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(self.tool.main(arguments), expected)
        return output.getvalue().splitlines()

    def line_of(self, *, lines, constant):
        return next(line for line in lines if line.split()[:1] == [constant])

    def test_every_class_is_shown_with_every_binding_it_lists(self):
        lines = self.shown([])
        for name, kind in self.tool.binding_classes().items():
            with self.subTest(kind=name):
                self.assertTrue(any(line.split()[:1] == [name] for line in lines))
        listed = sum(len(self.tool.bindings_of(kind)) for kind in self.tool.binding_classes().values())
        self.assertEqual(len([line for line in lines if line.startswith(' ')]), listed)

if __name__ == '__main__':
    unittest.main()
