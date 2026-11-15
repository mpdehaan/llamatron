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

"""The MacroComposer, the user's name for it: a set made from structured data that says what to play. composer.py turns a
song's input, its parts, bands and form, into a set's data, deciding nothing; decomposer.py writes an existing set as an
input; arranger.py makes an input from a song's picks and a style template of style_templates/, a style's traits with how
common each value is; melody.py sketches a tune by rule where a song gives none; players.py names the imaginary players a
song's complexities stand for; notation.py and shaping.py write parts as a pattern's rows and shape their velocity. It
fetches nothing and looks nothing up. internal_tools/macro_compose.sh runs it, and a wizard in the tracker is to use it."""
