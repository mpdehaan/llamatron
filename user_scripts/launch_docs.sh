#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: serve the documentation website, built into output/web_docs/, building it first where it is not built or a document has changed since, on this computer and open it in the browser; Ctrl+C stops it

set -eu
# Plain sh. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

# The site is built where it isn't yet, and again when any document is newer than it, so that what opens is current; the
# build offers to install Node.js first, as it needs it.
SITE_PAGE='output/web_docs/index.html'
if [ ! -f "$SITE_PAGE" ] || [ -n "$(find docs developer_docs -newer "$SITE_PAGE" -print -quit)" ]; then
    sh internal_tools/build_docs.sh
fi
exec .venv/bin/python internal_tools/serve_docs.py "$@"
