# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Model: the set as it is stored, in four parts. values/ holds the musical values every part of llamatron works with;
objects/ the objects a set file stores, the set, its songs, tracks, scenes, clips and the shared patterns and named things;
schema/ what a set file may hold: its names, the ranges and defaults of its values, and each setting and row described once; and file/
reading and writing the set file, corrections, migrations, safe YAML and the version a file records."""
