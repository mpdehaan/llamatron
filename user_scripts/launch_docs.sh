#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: serve the documentation website, already built into web_docs/, on this computer and open it in the browser; Ctrl+C stops it

set -eu
# Plain sh. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/serve_docs.py "$@"
