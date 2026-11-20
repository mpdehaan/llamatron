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

"""The check that tells internal_tools/build_docs.sh whether npm has anything to install: a module missing or at another version."""

from internal_tools.docs_modules_missing import ALL_THERE, main, MISSING, missing_modules
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

    def test_nothing_is_missing_when_every_pinned_module_is_there_at_its_version(self):
        with tempfile.TemporaryDirectory() as folder:
            site = a_site(folder=folder, installed={VITEPRESS: PINNED_VERSION, MERMAID: PINNED_VERSION})
            self.assertEqual(missing_modules(site), [])
            self.assertEqual(main([site]), ALL_THERE)

    def test_a_module_missing_or_at_another_version_is_named(self):
        with tempfile.TemporaryDirectory() as folder:
            site = a_site(folder=folder, installed={VITEPRESS: OTHER_VERSION})
            self.assertEqual(missing_modules(site), [VITEPRESS, MERMAID])
            self.assertEqual(main([site]), MISSING)


if __name__ == '__main__':
    unittest.main()
