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

"""Files saved before 1.0.155 held the set's long text under description, which is now notes; a description is one line."""

SINCE = '1.0.155'
DESCRIPTION = 'description'
NOTES = 'notes'


def is_before(data):
    """A file with no version gives no sign of which its description is, and is taken as current."""
    return False


def moved(*, data, conversion):
    if DESCRIPTION not in data:
        return data
    moved_data = dict(data)
    moved_data[NOTES] = moved_data.pop(DESCRIPTION)
    return moved_data
