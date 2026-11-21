# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The parts of the Document, one module per subject: its file and exports, its undo history, its edits to anything with a name, and its edits to the set, to the current song and to patterns.

Each module holds one class of methods that Document (tui/document.py) is made of. The classes
have no data of their own: they work on the set through what Document keeps, its setlist, its
current song and the `change` method that makes one change and notes it. Document was one file of
nearly 1,200 lines before, and is split by subject so that everything about saving, or about a
pattern's steps, is found in one place.
"""
