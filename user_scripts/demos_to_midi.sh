#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: every example as one General MIDI file in output/previews/, for any MIDI player

# Export every example, or the sets named, as General MIDI files, each track on a channel of its own with its
# instrument's sound, which a plain MIDI player plays with no DAW behind it:
#
#     sh user_scripts/demos_to_midi.sh
#     sh user_scripts/demos_to_midi.sh examples/learning/02_pachelbel.yml

set -eu
cd "$(dirname "$0")/.."
LLAMATRON=src/target/release/llamatron
if [ ! -x "$LLAMATRON" ]; then
    echo "llamatron is not built, so please build it first: sh build.sh" >&2
    exit 1
fi
PREVIEWS='output/previews'
mkdir -p "$PREVIEWS"
if [ "$#" -eq 0 ]; then
    set -- $(find examples -name '*.yml' -not -path 'examples/midi/*' | sort)
fi
for file in "$@"; do
    "$LLAMATRON" "$file" --to gm --out "$PREVIEWS" --replace
done
