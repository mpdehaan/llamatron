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

"""The parts of the Document, one module per subject: its file and exports, its undo history, its edits to anything with a name, and its edits to the set, to the current song and to patterns.

Each module holds one class of methods that Document (tui/document.py) is made of. The classes
have no data of their own: they work on the set through what Document keeps, its setlist, its
current song and the `_change` method that makes one change and notes it. Document was one file of
nearly 1,200 lines before, and is split by subject so that everything about saving, or about a
pattern's steps, is found in one place.
"""
