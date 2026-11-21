# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""internal_tools/docs_modules_missing.py, one quick check of its main path: a module missing or at another version is named. A tool fails loudly when it is run, so one check is enough (.claude/TESTING.md)."""

from internal_tools.docs_modules_missing import main, MISSING, missing_modules
import json
import pathlib
import tempfile
import unittest

VITEPRESS = 'vitepress'
MERMAID = 'mermaid'
PINNED_VERSION = '1.6.3'
OTHER_VERSION = '1.0.0'


def a_site(*, folder, installed):
    """Write a site whose package.json pins two modules, with node_modules holding the ones given at their versions."""
    site = pathlib.Path(folder)
    (site / 'package.json').write_text(json.dumps({'devDependencies': {VITEPRESS: PINNED_VERSION, MERMAID: PINNED_VERSION}}))
    for name, version in installed.items():
        module = site / 'node_modules' / name
        module.mkdir(parents=True)
        (module / 'package.json').write_text(json.dumps({'version': version}))
    return str(site)


class TestDocsModulesMissing(unittest.TestCase):

    def test_a_module_missing_or_at_another_version_is_named(self):
        with tempfile.TemporaryDirectory() as folder:
            site = a_site(folder=folder, installed={VITEPRESS: OTHER_VERSION})
            self.assertEqual(missing_modules(site), [VITEPRESS, MERMAID])
            self.assertEqual(main([site]), MISSING)


if __name__ == '__main__':
    unittest.main()
