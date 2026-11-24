#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
# What it does: import every MIDI file under --input-dir as the Import Wizard cuts it, into set files in --output-dir, and say how long the imports took; --help lists the options

set -eu
# Plain sh, so that sh user_scripts/batch_importer.sh works. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python -m llamatron.importers.batch_import "$@"
