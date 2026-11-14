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

"""What makes a style of music, as rules in code, the user's design: genres and subgenres as genomes of traits, each subgenre
inheriting its parent's and changing some, with ways to compare two styles, measure a song against one, plan the changes that
would move a song into another and generate the bones of a song in one. An expert system, not a model: every rule is written
here, and the generators, the MIDI import and the wizards to come build on it. Nothing in the tracker shows it yet.

Five packages, each building on the ones before: measures/ (what is measured and how values compare), hearing/ (a song turned
into played notes and measured), knowledge/ (the styles, people, songs, forms and theories), judging/ (fit, rules and following
a path) and reporting/ (what the library says). library.py is the one door to the knowledge."""
