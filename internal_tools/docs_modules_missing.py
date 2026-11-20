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

"""Exit 0 when a module the documentation website's package.json pins is missing from node_modules or at another version, so that
internal_tools/build_docs.sh runs npm then, and 1 when every one is there at its version, so that it runs nothing.

    internal_tools/docs_modules_missing.py .docs_site
"""

import json
import pathlib
import sys

PACKAGE = 'package.json'
MODULES = 'node_modules'
PINNED = 'devDependencies'
VERSION = 'version'
MISSING = 0
ALL_THERE = 1


def missing_modules(site):
    """Return the names of the modules the site's package.json pins that node_modules lacks, or holds at another version."""
    site = pathlib.Path(site)
    pinned = json.loads((site / PACKAGE).read_text()).get(PINNED, {})
    missing = []
    for name, version in pinned.items():
        installed = site / MODULES / name / PACKAGE
        if not installed.is_file() or json.loads(installed.read_text()).get(VERSION) != version:
            missing.append(name)
    return missing


def main(arguments):
    return MISSING if missing_modules(arguments[0]) else ALL_THERE


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
