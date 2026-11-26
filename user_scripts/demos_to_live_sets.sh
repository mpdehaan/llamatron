#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: every example as an Ableton Live set beside it

# Export every example as an Ableton Live set beside its file, replacing earlier exports:
#
#     sh user_scripts/demos_to_live_sets.sh

set -eu
cd "$(dirname "$0")/.."
LLAMATRON=src/target/release/llamatron
if [ ! -x "$LLAMATRON" ]; then
    echo "llamatron is not built, so please build it first: sh build.sh" >&2
    exit 1
fi
find examples -name '*.yml' -not -path 'examples/midi/*' | sort | while read -r file; do
    "$LLAMATRON" "$file" --to ableton --replace
done
