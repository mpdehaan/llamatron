# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Objects: what a set file stores: the set, its songs, their tracks, scenes and clips, and the shared patterns, scales,
generators, chains and grooves. Each extends LlamaData, so it turns itself into the plain data a set file holds with to_data() and
is built back from it with from_data(): what the user writes and edits, as opposed to the finished clips a song becomes."""
