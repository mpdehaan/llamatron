#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: the tracker builds a set from nothing, key by key, plays it and records the video: internal_tools/tutorial.sh examples/learning/01_hello_world.yml

set -eu
# Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/make_video_tutorial.py "$@"
