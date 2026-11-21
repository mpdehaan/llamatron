# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""internal_tools/constants_by_module.py rewrites a file so that each constant is named through the module that defines it."""

import importlib.util
import pathlib
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / 'internal_tools' / 'constants_by_module.py'
MODULE_NAME = 'constants_by_module'
# A small project of the tests' own: a module of values, a module that passes one of them on, and the file rewritten.
VALUES = 'llamatron.music.values'
MIDDLE = 'llamatron.music.middle'
TEXT = 'llamatron.strings.text'
USER = 'llamatron.music.user'
VALUES_SOURCE = """
    LOW = 1
    HIGH = 9


    class Kind:
        ONE = 'one'
"""
MIDDLE_SOURCE = """
    from llamatron.music.values import LOW as LOWEST

    OWN = LOWEST + 1
"""
MUSIC_PACKAGE = 'llamatron.music'
OTHER_PACKAGE = 'llamatron.tui'


def load_tool():
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def path_of(name):
    return ROOT / 'src' / pathlib.Path(*name.split('.')).with_suffix('.py')


class TestConstantsByModuleTool(unittest.TestCase):

    def setUp(self):
        self.tool = load_tool()

    def module(self, *, name, source):
        return self.tool.Module(name=name, path=path_of(name), source=textwrap.dedent(source).lstrip('\n'))

    def rewritten(self, *, source, name=USER, prefixes=None):
        """Return a file of the small project rewritten, how many names moved and what was left alone."""
        user = self.module(name=name, source=source)
        project = self.tool.Project([self.module(name=VALUES, source=VALUES_SOURCE), self.module(name=MIDDLE, source=MIDDLE_SOURCE), user])
        return self.tool.rewritten(module=user, project=project, prefixes=prefixes)

    def check(self, *, source, expected, moved, **named):
        result, count, skipped = self.rewritten(source=source, **named)
        self.assertEqual(result, textwrap.dedent(expected).lstrip('\n'))
        self.assertEqual(count, moved)
        return skipped

    def test_a_constant_goes_through_its_module_and_a_class_keeps_its_import(self):
        self.check(moved=2, source="""
            from llamatron.music.values import HIGH, LOW, Kind

            def span():
                return HIGH - LOW, Kind.ONE
        """, expected="""
            from llamatron.music import values
            from llamatron.music.values import Kind

            def span():
                return values.HIGH - values.LOW, Kind.ONE
        """)

    def test_an_import_left_with_no_name_is_replaced_by_the_modules(self):
        self.check(moved=1, source="""
            from llamatron.music.values import HIGH
            TOP = HIGH
        """, expected="""
            from llamatron.music import values
            TOP = values.HIGH
        """)

    def test_a_constant_another_module_passes_on_is_named_by_the_module_that_defines_it_under_its_name_there(self):
        self.check(moved=2, source="""
            from llamatron.music.middle import LOWEST, OWN
            BOTH = LOWEST + OWN
        """, expected="""
            from llamatron.music import values
            from llamatron.music import middle
            BOTH = values.LOW + middle.OWN
        """)

    def test_a_constant_read_through_a_module_that_only_imports_it_is_read_from_the_module_that_defines_it(self):
        self.check(moved=1, source="""
            from llamatron.music import middle
            BOTH = middle.LOWEST + middle.OWN
        """, expected="""
            from llamatron.music import middle
            from llamatron.music import values
            BOTH = values.LOW + middle.OWN
        """)

    def test_a_module_whose_name_the_file_uses_is_imported_under_another_name(self):
        self.check(moved=1, source="""
            from llamatron.music.values import HIGH

            def most(values):
                return max(values + [HIGH])
        """, expected="""
            from llamatron.music import values as values_values

            def most(values):
                return max(values + [values_values.HIGH])
        """)

    def test_a_module_the_file_already_imports_is_used_by_the_name_it_has(self):
        self.check(moved=1, source="""
            from llamatron.music import values as numbers
            from llamatron.music.values import HIGH
            TOP = HIGH + numbers.LOW
        """, expected="""
            from llamatron.music import values as numbers
            TOP = numbers.HIGH + numbers.LOW
        """)

    def test_a_comment_after_a_one_line_import_stays_and_a_classs_attribute_of_the_same_name_hides_nothing(self):
        self.check(moved=1, source="""
            from llamatron.music.values import HIGH  # checked elsewhere


            class Holder:
                HIGH = None

                def top(self):
                    return HIGH
        """, expected="""
            from llamatron.music import values  # checked elsewhere


            class Holder:
                HIGH = None

                def top(self):
                    return values.HIGH
        """)

    def test_a_name_the_file_assigns_itself_is_left_alone_and_said(self):
        source = """
            from llamatron.music.values import HIGH
            HIGH = HIGH + 1
        """
        skipped = self.check(moved=0, source=source, expected=source)
        self.assertEqual(len(skipped), 1)
        self.assertIn(self.tool.WHY_ASSIGNED.format(name='HIGH'), skipped[0])

    def test_the_strings_package_is_left_alone_and_a_prefix_keeps_only_the_constants_defined_under_it(self):
        source = """
            from llamatron.music.values import HIGH
            TOP = HIGH
        """
        self.check(moved=0, source=source, expected=source, name=TEXT)
        self.check(moved=0, source=source, expected=source, prefixes=[OTHER_PACKAGE])
        self.assertEqual(self.rewritten(source=source, prefixes=[MUSIC_PACKAGE])[1], 1)

    def test_what_the_rule_reads_names_each_import_of_a_constant(self):
        user = self.module(name=USER, source="""
            from llamatron.music.values import HIGH, Kind
        """)
        project = self.tool.Project([self.module(name=VALUES, source=VALUES_SOURCE), user])
        found = self.tool.find_names_imported(project=project, module=user)
        self.assertEqual(found, [self.tool.FOUND.format(path=path_of(USER).relative_to(ROOT).as_posix(), line=1, names='HIGH', module=VALUES)])
