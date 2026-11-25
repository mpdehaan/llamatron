#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# Opens llamatron2, the tracker in Rust, on a set if one is named, building it first, such as:
#     ./llamatron.sh examples/learning/08_tie.yml

set -e

# The program runs from the top folder of the project, where this script is.
cd "$(dirname "$0")"

if [ -x "$HOME/.cargo/bin/cargo" ]; then
    PATH="$HOME/.cargo/bin:$PATH"
fi
# Built afresh every time, so that it is never older than its code; cargo does nothing where nothing changed. Without
# Rust, the build script offers to install it first.
if command -v cargo >/dev/null 2>&1; then
    cargo build --release --quiet --manifest-path native/Cargo.toml -p llamatron-tracker
else
    sh user_scripts/build.sh
fi
exec native/target/release/llamatron2 "$@"
