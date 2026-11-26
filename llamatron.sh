#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# Opens llamatron, the tracker in Rust, on a set if one is named, such as:
#     ./llamatron.sh examples/learning/08_tie.yml

set -e

# The program runs from the top folder of the project, where this script is.
cd "$(dirname "$0")"

if [ ! -x native/target/release/llamatron ]; then
    echo 'llamatron is not built, so please build it first:'
    echo '    sh build.sh'
    exit 1
fi
exec native/target/release/llamatron "$@"
