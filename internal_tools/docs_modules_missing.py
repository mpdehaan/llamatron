# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Exit 0 when a module the documentation website's package.json pins is missing from node_modules or at another version, so that
internal_tools/build_docs.sh runs npm then, and 1 when every one is there at its version, so that it runs nothing.

    internal_tools/docs_modules_missing.py .cache/docs_site
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
