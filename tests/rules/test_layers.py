# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The rule of the program's layers: a package imports only packages below it, only a package's front doors are imported from outside, and a page imports no other page and only the model's vocabulary.

internal_tools/layers.py says what the layers are and finds the imports that cross them; tests/rules/layer_exceptions.py lists the
crossings that were there when the rule was made. No new crossing may appear, and a crossing that is gone must come off the list
(`internal_tools/layers.sh --prune`), so that the list only shrinks.
"""

import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
TOOL = ROOT / 'internal_tools' / 'layers.py'
TOOL_NAME = 'layers'
NEW_CROSSINGS = 'new imports cross the layers; the object they reach past should answer instead'
GONE_CROSSINGS = 'crossings on the allowed list are gone: run internal_tools/layers.sh --prune'
# Files and modules of the tests' own, as parts under the program.
A_PAGE = ('interface', 'tracker', 'screens', 'set', 'a_page.py')
ANOTHER_PAGE = ('interface', 'tracker', 'screens', 'set', 'another_page')
A_SHARED_PAGE = ('interface', 'tracker', 'screens', 'shared', 'field_page')
A_MODEL_FILE = ('model', 'objects', 'a_model.py')
A_GENERATOR = ('engine', 'generators', 'arp', 'model')
THE_REALIZER = ('engine', 'realizer', 'song_realizer')
A_PLAYER = ('engine', 'realizer', 'pattern_player')
A_SENDER = ('realtime', 'sender_process', 'engine')
THE_REALTIME_DOOR = ('realtime', 'playback_service')
THE_TRANSPORT = ('interface', 'tracker', 'transport.py')
THE_FILE_FORMAT = ('model', 'schema', 'file_format')
THE_LIMITS = ('model', 'schema', 'limits')
SOME_TEXT = ('user_strings', 'labels')


def load_tool():
    spec = importlib.util.spec_from_file_location(TOOL_NAME, TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestLayers(unittest.TestCase):

    def setUp(self):
        self.tool = load_tool()

    def test_no_import_crosses_the_layers_but_those_allowed_and_none_allowed_is_gone(self):
        found = self.tool.crossings()
        listed = self.tool.allowed()
        for rule in self.tool.RULES:
            with self.subTest(rule=rule):
                self.assertEqual([crossing for crossing in found[rule] if crossing not in listed[rule]], [], NEW_CROSSINGS)
                self.assertEqual([crossing for crossing in listed[rule] if crossing not in found[rule]], [], GONE_CROSSINGS)

    def test_a_package_may_import_below_it_and_its_text_and_not_above(self):
        self.assertEqual(self.tool.breaks(file=A_MODEL_FILE, module=A_GENERATOR), [self.tool.ORDER])
        self.assertEqual(self.tool.breaks(file=A_MODEL_FILE, module=SOME_TEXT), [])
        self.assertEqual(self.tool.breaks(file=THE_TRANSPORT, module=THE_FILE_FORMAT), [])

    def test_only_a_packages_front_door_is_imported_from_outside_and_real_time_only_by_its_users(self):
        self.assertEqual(self.tool.breaks(file=THE_TRANSPORT, module=THE_REALIZER), [])
        self.assertEqual(self.tool.breaks(file=THE_TRANSPORT, module=A_PLAYER), [self.tool.DOORS])
        self.assertEqual(self.tool.breaks(file=THE_TRANSPORT, module=THE_REALTIME_DOOR), [])
        self.assertEqual(self.tool.breaks(file=THE_TRANSPORT, module=A_SENDER), [self.tool.DOORS])
        self.assertEqual(self.tool.breaks(file=A_PAGE, module=THE_REALTIME_DOOR), [self.tool.DOORS])

    def test_a_page_imports_the_models_names_alone_and_no_other_page_but_the_shared_ones(self):
        self.assertEqual(self.tool.breaks(file=A_PAGE, module=THE_FILE_FORMAT), [])
        self.assertEqual(self.tool.breaks(file=A_PAGE, module=THE_LIMITS), [self.tool.PAGES])
        self.assertTrue(self.tool.page_breaks(file=A_PAGE, module=ANOTHER_PAGE))
        self.assertFalse(self.tool.page_breaks(file=A_PAGE, module=A_SHARED_PAGE))

    def test_pruning_only_takes_rows_off(self):
        found = {rule: ['kept'] for rule in self.tool.RULES}
        listed = {rule: ['kept', 'gone'] for rule in self.tool.RULES}
        self.assertEqual(self.tool.pruned(found=found, listed=listed), found)
