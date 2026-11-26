#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: profiles every example's render, the key presses or the real-time pipeline with Python's sampling profiler
# (Tachyon, profiling.sampling), which reads the stacks from outside at a thousand samples a second, so that the program runs at
# nearly full speed and the garbage collector's time shows; --flamegraph writes a flame graph into .sample_profiles/
#
#   internal_tools/sample_profile.sh renders                 # where a render's time goes, the top functions printed
#   internal_tools/sample_profile.sh keys --flamegraph       # the key presses, as .sample_profiles/keys.html
#   internal_tools/sample_profile.sh realtime                # the real-time report, every process and thread sampled

set -eu
# Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

USAGE='usage: internal_tools/sample_profile.sh renders|keys|realtime [--flamegraph]'
OUTPUT=.sample_profiles
case "${1:-}" in
    renders) target=internal_tools/time_renders.py; threads='' ;;
    keys) target=internal_tools/time_keys.py; threads='' ;;
    realtime) target=internal_tools/realtime_report.py; threads='--subprocesses --all-threads' ;;
    *) echo "$USAGE"; exit 1 ;;
esac
if [ "${2:-}" = "--flamegraph" ]; then
    mkdir -p "$OUTPUT"
    # shellcheck disable=SC2086
    exec .venv/bin/python -m profiling.sampling run --mode cpu $threads --flamegraph -o "$OUTPUT/$1.html" "$target"
fi
# shellcheck disable=SC2086
exec .venv/bin/python -m profiling.sampling run --mode cpu $threads --sort tottime -l 30 "$target"
