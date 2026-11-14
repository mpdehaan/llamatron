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
"""Every piece of text llamatron shows people, one module for each way the text is used.

errors.py holds what went wrong (ERR_), help.py each page's help (HELP_), and the rest hold the
MSG_ constants: labels.py the names of things on screen, legends.py what keys are called and do,
messages.py what the tracker says, marks.py what it draws, about.py the About dialog, cli.py the
command line and names.py the names the program gives to things. Nothing here does anything, and
no other package defines a constant with one of the three prefixes, so that all the wording can
be read and edited in one place.
"""
