#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: name every constant through the module that defines it, module.NAME (lists what would change; --write to rewrite)

set -eu
# Plain sh, so that internal_tools/constants_by_module.sh works. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/constants_by_module.py "$@"
