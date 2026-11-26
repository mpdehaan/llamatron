#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: retake the documents' screenshots in docs/screenshots/, from llamatron itself

# Retake the screenshots the guide and the README show, as SVG files:
#
#     internal_tools/screenshots.sh
#
# llamatron opens each shot's set, presses the keys that reach its screen, and writes the screen as an SVG, which git
# keeps as text. internal_tools/rebuild_docs.sh runs it before a push, and commits only the shots that changed.

set -eu
cd "$(dirname "$0")/.."
PATH="$HOME/.cargo/bin:$PATH"
cargo build --manifest-path src/Cargo.toml --release --quiet -p llamatron-compare
src/target/release/llamatron-compare screenshots docs/screenshots
