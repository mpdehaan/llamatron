# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The finished clips a song exports into, and the grid that maps them to tracks and scenes.

ClipGrid (clip_grid.py) is what the exporters write out: a Clip (clip.py) for each Scene
(scene.py) and Track (track.py), each clip carrying its notes and its Control values
(control.py). The song the user composes, one of the songs a set file holds, is the Song in
llamatron.composition.song, and SongRenderer plays it into a ClipGrid. positions.py holds the
arithmetic on the notes, chords, rests and held sounds a clip lists, and checks.py the checks
the grid's setters share.
"""
