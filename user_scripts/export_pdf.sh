#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
# What it does: make a song of a set into its learning packet, a PDF beside the set; --help lists the options

set -eu
# Plain sh, so that sh user_scripts/export_pdf.sh works. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python -m llamatron.exporters.pdf.pdf_script "$@"
