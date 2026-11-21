#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: the check Claude runs before committing code: the tests that cover what changed

# There is no git hook, so that a person editing documents commits at once; Claude
# stages its files and runs this before committing anything that changes code, tests, examples or
# tools, and commits only when it passes (.claude/TESTING.md).

set -e
# Run from the repository's top folder, wherever it is started.
cd "$(git rev-parse --show-toplevel)"
# Two rules are kept by fixers rather than tests: every file's opening imports sorted, and every constant named through its module.
# What a fixer changes is changed in the working tree, so the check stops for it to be looked at and staged again.
# Only the Python files changed since the last commit are rewritten, every other file having passed when it was committed.
before=$(git diff --stat)
changed=$( { git diff --name-only HEAD; git ls-files --others --exclude-standard; } | grep '\.py$' | sort -u | while read -r file; do [ -f "$file" ] && echo "$file"; done)
if [ -n "$changed" ]; then
    # The constants fixer may add an import, which the sorter then puts in its place.
    internal_tools/constants_by_module.sh --write --only $changed > /dev/null
    internal_tools/sort_imports.sh --write --only $changed > /dev/null
fi
if [ "$(git diff --stat)" != "$before" ]; then
    echo 'check before commit: the fixers changed files, which are to be looked at and staged again:'
    git diff --stat
    exit 1
fi
echo 'check before commit: running the tests that cover what changed'
# The classes that cover the changed files, by the map internal_tools/test_map.sh made, and the rule tests; the whole suite when
# a change is one the map can't place. The whole suite runs before every push (internal_tools/push_all.sh).
internal_tools/test_changed.sh
