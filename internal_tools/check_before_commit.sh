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
    # The Rust's own checks: its layout, clippy with every warning an error, its tests in the quick dev build, and the
    # release build the comparisons run (.claude/rules/RUST.md).
    # Every value with a meaning is named: no line the change adds types a number or a name in place
    # (.claude/rules/STYLE.md).
    echo 'check before commit: checking that every value is named'
    .venv/bin/python internal_tools/check_named_values.py
    echo 'check before commit: checking the Rust with cargo'
    PATH="$HOME/.cargo/bin:$PATH"
    cargo fmt --manifest-path src/Cargo.toml --all --check
    cargo clippy --manifest-path src/Cargo.toml --workspace --release --all-targets --quiet -- -D warnings
    cargo test --manifest-path src/Cargo.toml --workspace --quiet
    cargo build --manifest-path src/Cargo.toml --workspace --release --quiet
    # The comparisons a change can affect, by the crates it changed: everything for the set's own layers, the examples,
    # the frozen answers or the comparison itself; the push runs every step whatever changed.
    steps=''
    add() { for step in "$@"; do case " $steps " in *" $step "*) ;; *) steps="$steps $step" ;; esac; done; }
    for path in $changed; do
        case "$path" in
            src/model/*|src/math/*|src/strings/*|src/compare/*|src/Cargo.*|examples/*|py_legacy/*|internal_tools/*)
                add load layout migrate save edits pattern_edits render timeline player midi live import screens ;;
            src/engine/*) add render timeline player midi live import screens ;;
            src/exporters/*) add midi live ;;
            src/importers/*) add import ;;
            src/tracker/*) add edits timeline player screens ;;
        esac
    done
    # llamatron held to the Python program's frozen answers, the steps side by side; a difference shows what differs and
    # stops the check.
    results=$(mktemp -d)
    for step in $steps; do
        ( .venv/bin/python internal_tools/compare_llamatron.py "$step" > "$results/$step" 2>&1; echo $? > "$results/$step.code" ) &
    done
    wait
    failed=0
    for step in $steps; do
        if [ "$(cat "$results/$step.code")" != 0 ]; then
            cat "$results/$step"
            failed=1
        fi
        echo "$step: $(grep 'sets differ\|stops differ' "$results/$step" | tr '\n' ' ')"
    done
    rm -rf "$results"
    [ "$failed" = 0 ] || exit 1
    # The crash sweep: every key every page offers, at each kind of place, on sets that between them hold every kind of
    # page, where the tracker changed; a key that panics fails the check, with the keys that reach it.
    case " $steps " in
        *" screens "*)
            swept=examples/learning/15_complex_gifts_chain.yml,examples/learning/06_chord_progression_generator.yml,examples/learning/21_guitarify.yml,examples/by_genre/electronic/minimal_techno.yml
            mkdir -p /tmp/claude/llamatron
            sweep=/tmp/claude/llamatron/crash_sweep.txt
            src/target/release/llamatron-compare explore "$swept" > "$sweep" || { grep '^panic' "$sweep"; exit 1; }
            echo "crash sweep: $(head -1 "$sweep")" ;;
    esac
fi
# The architecture diagram is made from the code, and fails the check where it is out of date.
.venv/bin/python internal_tools/make_diagrams.py --check || { echo 'the architecture diagram is out of date: run internal_tools/make_diagrams.py'; exit 1; }
# Every path a document names must still exist.
exec .venv/bin/python -m unittest -q python.tests.test_doc_paths python.tests.test_record python.tests.test_check_named_values
