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
"""The importers: a file from outside llamatron made into what a set holds, so far a MIDI file made into a song.

The MIDI import (midi_import.py) reads a file's notes (midi_reading.py), splits each of its
tracks into voices a pattern can hold (voices.py), chooses where the song's scenes split and
which pattern each clip repeats (cutting.py), and writes the song, its patterns and its scales as
a set file holds them (writing.py), which the set reads as it reads a file. comparison.py says
whether two MIDI files play the same notes, which is how an import is proved.
"""
