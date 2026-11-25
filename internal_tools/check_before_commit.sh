#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: the check Claude runs before committing code: the tests that cover what changed

# There is no git hook, so that a person editing documents commits at once; Claude
# stages its files and runs this before committing anything that changes code, tests, examples or
# tools, and commits only when it passes (.claude/rules/TESTING.md).

set -e
# Run from the repository's top folder, wherever it is started.
cd "$(git rev-parse --show-toplevel)"
# The Python style fixers (constants_by_module.sh, sort_imports.sh) no longer run here: the user waives the Python style
# rules while llamatron is ported to Rust (.claude/rules/STYLE.md).
native=$( { git diff --name-only HEAD; git ls-files --others --exclude-standard; } | grep '^native/' || true)
if [ -n "$native" ]; then
    # The native code's own checks: its layout, clippy with every warning an error, its tests and its build (.claude/rules/RUST.md).
    echo 'check before commit: checking the native code with cargo'
    PATH="$HOME/.cargo/bin:$PATH"
    cargo fmt --manifest-path native/Cargo.toml --all --check
    cargo clippy --manifest-path native/Cargo.toml --workspace --release --all-targets --quiet -- -D warnings
    cargo test --manifest-path native/Cargo.toml --workspace --release --quiet
    cargo build --manifest-path native/Cargo.toml --workspace --release --quiet
    # llamatron2 held to the Python program, every step the port has reached, over every example and test set.
    for step in load layout migrate save render midi; do
        # Each step runs once: its summary is shown, and a difference shows what differs and stops the check.
        compared=$(.venv/bin/python internal_tools/compare_llamatron2.py "$step") || { echo "$compared"; exit 1; }
        echo "$step: $(echo "$compared" | grep 'sets differ')$(echo "$compared" | grep 'wait on' | sed 's/^/, /')"
    done
fi
# The Python program is frozen while it is ported to Rust (.claude/rules/STYLE.md), so its tests run only when something it
# reads changed; a commit of the native code alone is held by cargo's checks above and the comparisons with Python.
python=$( { git diff --name-only HEAD; git ls-files --others --exclude-standard; } | grep -E '^(src/|tests/|examples/|internal_tools/.*\.py$|requirements\.txt|pyproject\.toml)' || true)
if [ -z "$python" ]; then
    echo 'check before commit: nothing the Python program reads changed, so its tests are not run'
    # Every path a document names must still exist, the native code's included.
    exec .venv/bin/python -m unittest -q tests.rules.test_doc_paths
fi
echo 'check before commit: running the tests that cover what changed'
# The classes that cover the changed files, by the map internal_tools/test_map.sh made, and the rule tests; the whole suite when
# a change is one the map can't place. The whole suite runs before every push (internal_tools/push_all.sh).
internal_tools/test_changed.sh
