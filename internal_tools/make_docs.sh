#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Regenerates everything in the documents that comes from the code: the diagrams in
# docs/ARCHITECTURE.md and docs/GUIDE.md, and the tracker's screenshots in docs/screenshots/.
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
