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
    for manifest in native/*/Cargo.toml; do
        cargo fmt --manifest-path "$manifest" --check
        cargo clippy --manifest-path "$manifest" --release --all-targets --quiet -- -D warnings
        cargo test --manifest-path "$manifest" --release --quiet
        cargo build --manifest-path "$manifest" --release --quiet
    done
fi
echo 'check before commit: running the tests that cover what changed'
# The classes that cover the changed files, by the map internal_tools/test_map.sh made, and the rule tests; the whole suite when
# a change is one the map can't place. The whole suite runs before every push (internal_tools/push_all.sh).
internal_tools/test_changed.sh
