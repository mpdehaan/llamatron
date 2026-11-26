#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: write .claude/reference/KEYMAP.md, every key on every page, from a walk of llamatron

# Write the key map again after a key changes:
#
#     internal_tools/key_map.sh
#
# llamatron walks itself on sets that between them hold every kind of page, pressing every key every page offers at each
# kind of place, and the map says what each key does there.

set -eu
cd "$(dirname "$0")/.."
PATH="$HOME/.cargo/bin:$PATH"
cargo build --manifest-path src/Cargo.toml --release --quiet -p llamatron-compare
sets=examples/learning/15_complex_gifts_chain.yml,examples/learning/06_chord_progression_generator.yml,examples/learning/21_guitarify.yml,examples/by_genre/electronic/minimal_techno.yml
src/target/release/llamatron-compare keymap "$sets" .claude/reference/KEYMAP.md
