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

"""A method that only returns what its object holds is named for that: get_x, or is_x, has_x or can_x for yes or no.

So a method named otherwise is known to work something out or to have an effect. The methods
listed here keep a plain name: each is one that other classes answer by working something out,
so its name is the question's, or says yes or no with a verb, as a clip that loops does.
"""

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE = ROOT / 'src'
PYTHON_FILES = '*.py'
HELD_NAMES = ('get_', 'is_', 'has_', 'can_')
PRIVATE = '_'
SELF = 'self'
MISNAMED = '{path}:{line}: {owner}.{name} returns what is held, so its name starts with one of {names}'

# Questions that other classes answer by working something out, and yes or no said with a verb: (class, method).
PLAIN_NAMES = (
    ('RowDescription', 'changes_with_drums'),
    ('Choice', 'nearest'),
    ('Arp', 'end_state'),
    ('AutoRatchet', 'end_state'),
    ('VoiceLeading', 'end_state'),
    ('ClipColumn', 'plays_through_fluidsynth'),
    ('WizardChoices', 'holds_offers'),
    ('WizardChoices', 'plays_quiet_notes'),
    ('RegisterSolo', 'before_step'),
    ('SteppedClock', 'now'),
    ('Memory', 'checks'),
    ('KeyBinding', 'shown_label'),
    ('MadePreview', 'document'),
    ('PatternPreview', 'document'),
    ('ListPage', 'takes_text'),
    ('Page', 'crumb_trail'),
    ('PlayerBranch', 'key'),
)


def statements_of(function):
    """Return a function's statements, leaving out its docstring."""
    return [statement for statement in function.body if not (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant))]


def returns_what_is_held(function):
    """Return whether a method does nothing but return one of its object's own attributes, not a constant of its class."""
    statements = statements_of(function)
    if len(statements) != 1 or not isinstance(statements[0], ast.Return):
        return False
    value = statements[0].value
    held = isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name) and value.value.id == SELF
    return held and not value.attr.isupper()


def misnamed_methods(*, path, tree):
    """Return a line for each method of a file that returns what is held under a plain name it is not listed to keep."""
    found = []
    for owner in ast.walk(tree):
        if not isinstance(owner, ast.ClassDef):
            continue
        for method in owner.body:
            if not isinstance(method, ast.FunctionDef) or method.name.startswith((*HELD_NAMES, PRIVATE)):
                continue
            if returns_what_is_held(method) and (owner.name, method.name) not in PLAIN_NAMES:
                found.append(MISNAMED.format(path=path, line=method.lineno, owner=owner.name, name=method.name, names=', '.join(HELD_NAMES)))
    return found


class TestGetterNames(unittest.TestCase):

    def test_a_method_that_returns_what_is_held_says_so(self):
        found = []
        for path in sorted(SOURCE.rglob(PYTHON_FILES)):
            found += misnamed_methods(path=path.relative_to(ROOT), tree=ast.parse(path.read_text(), filename=str(path)))
        self.assertEqual(found, [])

    def test_every_plain_name_listed_is_still_one(self):
        plain = set()
        for path in sorted(SOURCE.rglob(PYTHON_FILES)):
            for owner in ast.walk(ast.parse(path.read_text(), filename=str(path))):
                if isinstance(owner, ast.ClassDef):
                    plain |= {(owner.name, method.name) for method in owner.body if isinstance(method, ast.FunctionDef) and returns_what_is_held(method)}
        self.assertEqual([listed for listed in PLAIN_NAMES if listed not in plain], [])

    def test_a_plain_name_is_found_and_a_worked_out_answer_is_not(self):
        held = ast.parse('class Thing:\n    def name(self):\n        return self._name\n')
        worked_out = ast.parse('class Thing:\n    def name(self):\n        return self._name.upper()\n')
        named = ast.parse('class Thing:\n    def get_name(self):\n        return self._name\n')
        self.assertEqual(len(misnamed_methods(path=SOURCE, tree=held)), 1)
        self.assertEqual(misnamed_methods(path=SOURCE, tree=worked_out), [])
        self.assertEqual(misnamed_methods(path=SOURCE, tree=named), [])
