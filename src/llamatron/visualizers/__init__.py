# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The visualizers: what Arrange's clip area can show in place of the clips while a song plays in real time.

Each mode is a Visualizer (visualizer.py), listed in order in modes.py, which draws the frame for
an area of a given size at a moment as lines of coloured text, from whole-number arithmetic on
numpy arrays (pixels.py turns an array of big pixels into those lines). They know nothing of
Textual: the Arrange page asks for a frame and lays it over the clip area. .claude/IDEAS.yml, "The
visualizer", holds the plan they are built by, a stage at a time.
"""
