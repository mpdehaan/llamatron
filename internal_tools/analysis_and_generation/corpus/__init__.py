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

"""The corpus as Python objects for meta-analysis (111 A): every dataset fetched into .corpus/ read into one kind of piece, each
piece's measures cached as tables in .corpus/tables/, and analyses that do arithmetic on those tables. Development only, never
imported by llamatron itself, which needs no downloaded data. Every piece keeps its source, and every source its terms and how
far its data can be trusted, so that a source can be measured on its own before it is pooled with others, and so that knowledge
calibrated from it carries its license (.claude/GENRES.md, "Licenses Travel With Knowledge")."""
