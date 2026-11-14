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

"""The objects a set file stores: the set, its songs, their tracks, scenes and clips, and the shared patterns, scales, generators, chains and grooves.

Each one extends LlamaData, so it can turn itself into the plain data a set file holds, with
to_data(), and be built back from it, with from_data(). Together they're the composition model:
what the user writes and edits, as opposed to the finished clips that a song exports into.
"""
