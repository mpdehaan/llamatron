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

"""The Glide row, a toggle drawn with the dot like Tie: the user chose the dot over a bar into the next step on 2026-11-09, since the bar didn't read well."""

from llamatron.tui.components.toggle_row import ToggleRow
from llamatron.tui import keybindings


class GlideRow(ToggleRow):
    """Space toggles the glide, and Bksp turns it off, on a step with a note."""

    KEYS = keybindings.GlideRow

    __slots__ = ()
