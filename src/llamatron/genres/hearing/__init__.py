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

"""Measuring a song from what it plays, the user's design: a song is rendered through llamatron's own objects down to notes, and
measured from those notes alone, never from how its set file is laid out, so that nothing is assumed about its structure. The
measures are expressed in the traits of genres/measures/traits.py, so that a song compares with a style the way two styles compare."""
