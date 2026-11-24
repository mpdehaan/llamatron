#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: what pycodestyle says, less what it is told to ignore: a look, not a rule, see .claude/rules/STYLE.md

set -eu
# Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

# What pycodestyle leaves out (the user's decision): lines run as long as they need to read as one thought, and the blank-line
# counts around definitions and at the end of a file aren't rules here; nothing pycodestyle reports is a rule unless
# .claude/rules/STYLE.md says so. Naming what to ignore replaces pycodestyle's own default list, so that list (E121, E123, E126,
# E226, E24, E704, W503, W504) is repeated here.
IGNORED='E501,E302,E305,W391,E121,E123,E126,E226,E24,E704,W503,W504'
exec .venv/bin/python -m pycodestyle --ignore="$IGNORED" --statistics src tests internal_tools
