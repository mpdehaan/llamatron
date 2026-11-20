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

"""The map of tests to source files: which classes a change needs, and which lines of a file running say a class used it."""

from internal_tools import test_map
import unittest

SOURCE_FILE = 'src/llamatron/composition/naming.py'
ANOTHER_SOURCE_FILE = 'src/llamatron/generators/arp.py'
NEW_SOURCE_FILE = 'src/llamatron/composition/brand_new.py'
RULE_CLASS = 'tests.rules.test_slots.TestSlots'
NAMING_CLASS = 'tests.composition.test_naming.TestNaming'
ARP_CLASS = 'tests.generators.test_arp.TestArp'
EXAMPLES_CLASS = 'tests.app.test_examples.TestExamples'
EVERY_CLASS = [RULE_CLASS, NAMING_CLASS, ARP_CLASS, EXAMPLES_CLASS]
BY_FILE = {SOURCE_FILE: [NAMING_CLASS], ANOTHER_SOURCE_FILE: [ARP_CLASS]}


def needed(changed):
    return test_map.needed(changed=changed, by_file=BY_FILE, every_class=EVERY_CLASS)


class TestWhatAChangeNeeds(unittest.TestCase):

    def test_a_source_file_needs_the_classes_that_ran_it_and_the_rule_tests(self):
        self.assertEqual(needed([SOURCE_FILE]), sorted([NAMING_CLASS, RULE_CLASS]))

    def test_a_test_file_needs_its_own_classes(self):
        self.assertEqual(needed(['tests/generators/test_arp.py']), sorted([ARP_CLASS, RULE_CLASS]))

    def test_an_example_needs_the_tests_that_read_examples(self):
        self.assertIn(EXAMPLES_CLASS, needed(['examples/learning/01_hello_world.yml']))

    def test_notes_only_for_claude_need_only_the_rule_tests(self):
        self.assertEqual(needed(['.claude/QUEUE.md']), [RULE_CLASS])

    def test_a_file_the_map_cannot_place_needs_everything(self):
        self.assertEqual(needed([NEW_SOURCE_FILE]), test_map.EVERYTHING)
        self.assertEqual(needed(['tests/support/ui_testing.py']), test_map.EVERYTHING)
        self.assertEqual(needed(['setup.py']), test_map.EVERYTHING)


class TestImportLines(unittest.TestCase):

    def test_a_functions_body_is_not_run_by_importing_and_its_header_is(self):
        lines = test_map.import_lines(SOURCE_FILE)
        source = (test_map.ROOT / SOURCE_FILE).read_text().split('\n')
        header = next(number for number, line in enumerate(source, start=1) if line.startswith('def '))
        self.assertIn(header, lines)
        self.assertNotIn(header + 2, lines)


if __name__ == '__main__':
    unittest.main()
