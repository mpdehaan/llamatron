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
"""The parts the pages are drawn from: one object per row of the pattern editor's step grid, each saying what its cells show and what its keys do, and the Arrange page's length bars and the frame around its cursor.

They draw with Rich text and know nothing of Textual, so that the editors could be shown by
another toolkit, and they hold no data of their own: every value is read and written through the
editor's document, so the pattern stays the one place the steps live.
"""
