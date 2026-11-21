# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The objects a set file stores: the set, its songs, their tracks, scenes and clips, and the shared patterns, scales, generators, chains and grooves.

Each one extends LlamaData, so it can turn itself into the plain data a set file holds, with
to_data(), and be built back from it, with from_data(). Together they're the composition model:
what the user writes and edits, as opposed to the finished clips that a song exports into.
"""
