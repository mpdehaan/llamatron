# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The forms: what a page shows, as a tree of plain nodes, apart from how the tracker draws it and from Textual.

- moves: the moves a person makes through a form, up, down, left, right and choose, and how a cursor goes.
- cursor: a place among a number of places, which the moves move.
- nodes: the fields a settings page is made of.
- statement_rows: the lines of a table of statements, Bypass When's.
- tab_box: a settings page's tab box, its tabs and columns, and where the cursor goes between its fields.
"""
