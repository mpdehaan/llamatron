#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: serve the documentation website, built into output/web_docs/, building it first where it is not built, on this computer and open it in the browser; Ctrl+C stops it

set -eu
# Plain sh. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

# The site is built where it isn't yet; the build offers to install Node.js first, as it needs it.
if [ ! -f output/web_docs/index.html ]; then
    sh internal_tools/build_docs.sh
fi
exec .venv/bin/python internal_tools/serve_docs.py "$@"
