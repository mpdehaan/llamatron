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

"""The four ways a run of the song wizard starts when the current song was made by the wizard."""

NEW_FROM_LAST = 'new from last'
NEW_FROM_SCRATCH = 'new from scratch'
REPLACE_FROM_LAST = 'replace from last'
REPLACE_FROM_SCRATCH = 'replace from scratch'
# In the order they are offered.
STARTS = [NEW_FROM_LAST, NEW_FROM_SCRATCH, REPLACE_FROM_LAST, REPLACE_FROM_SCRATCH]
# The starts that begin with the choices the current song kept, and the starts that replace the current song.
FROM_LAST = (NEW_FROM_LAST, REPLACE_FROM_LAST)
REPLACING = (REPLACE_FROM_LAST, REPLACE_FROM_SCRATCH)
