# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The rules of a function's shape in the program: a body of at most 30 lines, blocks at most three deep, or four with a reason, at
most five parameters, no reach into another object's private names, no catch of every error but with a reason, at most one
check that an object is of a class of the program's own, and at most 500 lines of code to a file or a class (1000 in engine/ and realtime/), files that are lists
by nature aside.

internal_tools/code_shape.py finds what breaks each rule; tests/rules/shape_exceptions.py lists what broke them when they were
made, a list that only shrinks, and what a rule allows with a reason. No new place may break a rule, a listed place that no longer
breaks its rule must come off the list (`internal_tools/code_shape.sh --prune`), and nothing nests deeper than four.
"""

import importlib.util
import pathlib
import unittest
from tests import rules

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
TOOL = ROOT / 'internal_tools' / 'code_shape.py'
TOOL_NAME = 'code_shape'
NEW_PLACES = "new places break a rule of a function's shape: {places}"
GONE_PLACES = 'places on the allowed list no longer break their rule: run internal_tools/code_shape.sh --prune: {places}'
NO_REASON = 'a place allowed for good needs a reason: {places}'
TOO_DEEP = 'a place allowed four deep with a reason nests deeper than four: {places}'


def the_tool():
    """Return internal_tools/code_shape.py as a module, which lives outside the program's package."""
    spec = importlib.util.spec_from_file_location(TOOL_NAME, TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skip(rules.STYLE_WAIVED)
class TestCodeShape(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tool = the_tool()
        cls.found = cls.tool.breaks()
        cls.allowed, cls.with_reason = cls.tool.exceptions()

    def test_no_new_place_breaks_a_rule(self):
        new = [place for rule in self.tool.RULES for place in self.new_in(rule)]
        self.assertEqual(new, [], msg=NEW_PLACES.format(places='\n'.join(new)))

    def test_a_listed_place_that_no_longer_breaks_its_rule_comes_off_the_list(self):
        gone = [place for rule in self.tool.RULES for place in self.gone_from(rule)]
        self.assertEqual(gone, [], msg=GONE_PLACES.format(places='\n'.join(gone)))

    def test_every_place_allowed_for_good_says_why(self):
        silent = [place for reasons in self.with_reason.values() for place, reason in reasons.items() if not reason]
        self.assertEqual(silent, [], msg=NO_REASON.format(places='\n'.join(silent)))

    def test_nothing_nests_deeper_than_four(self):
        deepest = [place for place in self.with_reason.get(self.tool.DEEP, {}) if place in self.found[self.tool.DEEPEST]]
        self.assertEqual(deepest, [], msg=TOO_DEEP.format(places='\n'.join(deepest)))

    def new_in(self, rule):
        """The places that break a rule and are neither listed nor allowed with a reason."""
        listed = self.allowed.get(rule, ())
        reasoned = self.with_reason.get(rule, {})
        return [place for place in self.found[rule] if place not in listed and place not in reasoned]

    def gone_from(self, rule):
        """The listed places that no longer break a rule."""
        return [place for place in self.allowed.get(rule, ()) if place not in self.found[rule]]


if __name__ == '__main__':
    unittest.main()
