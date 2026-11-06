# llamatron: a Python language and framework for producing MIDI clips.
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

"""Playing a song's composition objects into finished clips, which the renderers then write.

SongRenderer is where it starts: it writes out each scene, and has each track's cell played by
a CellPlayer, which plays its patterns a pass at a time with a PatternPlayer. The other classes
here are the parts those share: the order steps play in, running totals, grabs and morphing.
"""
