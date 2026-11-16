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

"""Measuring a song's style from the notes it plays: a tool for research, not a part of the program. It
was the program's genre library, moved here once nothing a person runs used it; the corpus tables are made with it.

Two packages: measures/ (what is measured, each trait a value that compares field by field, and how values compare) and
hearing/ (a song or a MIDI file turned into played notes and measured). strings.py holds the words both show. The tools
beside this folder import it as measuring, their own folder being on the path."""
