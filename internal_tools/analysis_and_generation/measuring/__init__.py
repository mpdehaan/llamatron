# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Measuring a song's style from the notes it plays: a tool for research, not a part of the program. It
was the program's genre library, moved here once nothing a person runs used it; the corpus tables are made with it.

Two packages: measures/ (what is measured, each trait a value that compares field by field, and how values compare) and
hearing/ (a song or a MIDI file turned into played notes and measured). strings.py holds the words both show. The tools
beside this folder import it as measuring, their own folder being on the path."""
