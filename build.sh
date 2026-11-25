#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: build llamatron2, the tracker in Rust, with its backend, offering to install Rust first

# Build llamatron2, which ./llamatron.sh runs:
#
#     sh build.sh
#
# It checks what building needs and offers to install what is missing, installing nothing unless you say yes, through
# internal_tools/build_backend.sh, which builds the backend too; then it builds the tracker into
# native/target/release/llamatron2. Running it again rebuilds only what changed.

set -eu
cd "$(dirname "$0")"

sh internal_tools/build_backend.sh
if [ -x "$HOME/.cargo/bin/cargo" ]; then
    PATH="$HOME/.cargo/bin:$PATH"
fi
cargo build --release --manifest-path native/Cargo.toml -p llamatron-tracker
echo 'llamatron2 is built: ./llamatron.sh opens it.'
