#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: the check Claude runs before committing code: the native code's own checks, llamatron held to the Python's frozen answers, and the paths the documents name

# There is no git hook, so that a person editing documents commits at once; Claude
# stages its files and runs this before committing anything that changes code, tests, examples or
# tools, and commits only when it passes (.claude/rules/TESTING.md).

set -e
cd "$(git rev-parse --show-toplevel)"
changed=$( { git diff --name-only HEAD; git ls-files --others --exclude-standard; } | grep -E '^(src/|examples/|py_legacy/frozen_test_data/|internal_tools/compare_llamatron\.py$)' || true)
if [ -n "$changed" ]; then
    # The native code's own checks: its layout, clippy with every warning an error, its tests and its build (.claude/rules/RUST.md).
    echo 'check before commit: checking the native code with cargo'
    PATH="$HOME/.cargo/bin:$PATH"
    cargo fmt --manifest-path src/Cargo.toml --all --check
    cargo clippy --manifest-path src/Cargo.toml --workspace --release --all-targets --quiet -- -D warnings
    cargo test --manifest-path src/Cargo.toml --workspace --release --quiet
    cargo build --manifest-path src/Cargo.toml --workspace --release --quiet
    # llamatron held to the Python program's frozen answers, every step, over every example and test set.
    for step in load layout migrate save edits pattern_edits render timeline player midi live import screens; do
        # Each step runs once: its summary is shown, and a difference shows what differs and stops the check.
        compared=$(.venv/bin/python internal_tools/compare_llamatron.py "$step") || { echo "$compared"; exit 1; }
        echo "$step: $(echo "$compared" | grep 'sets differ\|stops differ' | tr '\n' ' ')$(echo "$compared" | grep 'wait on\|changed since' | sed 's/^/, /' | tr '\n' ' ')"
    done
fi
# Every path a document names must still exist.
exec .venv/bin/python -m unittest -q python.tests.test_doc_paths
