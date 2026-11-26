# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""internal_tools/show_keys.py, one quick check of its main path: every class is shown with every binding it lists. A tool fails loudly when it is run, so one check is enough (.claude/rules/TESTING.md)."""

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
