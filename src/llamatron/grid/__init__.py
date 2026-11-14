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

"""The finished clips a song exports into, and the grid that maps them to tracks and scenes.

ClipGrid (clip_grid.py) is what the exporters write out: a Clip (clip.py) for each Scene
(scene.py) and Track (track.py), each clip carrying its notes and its Control values
(control.py). The song the user composes, one of the songs a set file holds, is the Song in
llamatron.composition.song, and SongRenderer plays it into a ClipGrid. positions.py holds the
arithmetic on the notes, chords, rests and held sounds a clip lists, and checks.py the checks
the grid's setters share.
"""
