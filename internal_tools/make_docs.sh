#!/bin/sh
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
#
# Regenerates everything in the documents that comes from the code: the diagrams in
# docs/ARCHITECTURE.md and GUIDE.md, and the tracker's screenshots in docs/screenshots/.
# Run it from the top folder after the virtual environment is set up:
#
#     internal_tools/make_docs.sh
#
# Nothing here needs any tool beyond that environment: the diagrams are Mermaid text, which
# GitHub draws itself, and the screenshots are SVG files the tracker draws from its own screens.

set -e
cd "$(dirname "$0")/.."
.venv/bin/python internal_tools/make_diagrams.py
.venv/bin/python internal_tools/make_screenshots.py
.venv/bin/python internal_tools/demo_summary.py --write-docs
