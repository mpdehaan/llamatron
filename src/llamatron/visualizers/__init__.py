# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""The visualizers: what Arrange's clip area can show in place of the clips while a song plays in real time, the user's design of 2026-11-10.

Each mode is a Visualizer (visualizer.py), listed in order in modes.py, which draws the frame for
an area of a given size at a moment as lines of coloured text, from whole-number arithmetic on
numpy arrays (pixels.py turns an array of big pixels into those lines). They know nothing of
Textual: the Arrange page asks for a frame and lays it over the clip area. dev_notes/IDEAS.md, "The
visualizer", holds the plan they are built by, a stage at a time.
"""
