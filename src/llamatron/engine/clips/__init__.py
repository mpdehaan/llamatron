# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Clips: the finished clips a song is realized into, and the grid that maps them to tracks and scenes.

ClipGrid (clip_grid.py) is what the exporters write out: a Clip (clip.py) for each scene and track, each clip carrying its notes
and its Control values (control.py). positions.py holds the arithmetic on the notes, chords, rests and held sounds a clip lists,
and row_clock.py the time at each step of a row."""
