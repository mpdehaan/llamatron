# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The importers: a file from outside llamatron made into what a set holds, so far a MIDI file made into a song.

The MIDI import (midi_import.py) reads a file's notes (midi_reading.py), splits each of its
tracks into voices a pattern can hold (voices.py), chooses where the song's scenes split and
which pattern each clip repeats (cutting.py), and writes the song, its patterns and its scales as
a set file holds them (writing.py), which the set reads as it reads a file. comparison.py says
whether two MIDI files play the same notes, which is how an import is proved.
"""
