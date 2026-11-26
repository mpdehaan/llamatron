# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The forms: what a page shows, as a tree of plain nodes, apart from how the tracker draws it and from Textual.

- grouped_choices: a picker's choices in groups under headings, which a page shows (Page.ask_grouped).
- table: a list page's columns (ListColumn) and which way a cell is lined up (Align).
- remarks: the lines under a page's settings as plain values, each its words and whether it is dim.
- moves: the moves a person makes through a form, up, down, left, right and choose, and how a cursor goes.
- cursor: a place among a number of places, which the moves move.
- navigator: how the cursor goes through a settings page's form, and which move brings it nearer a field (FormNavigator).
- nodes: the fields a settings page is made of.
- statement_rows: the lines of a table of statements, Bypass When's.
- percentages: a percentage of what it scales as a field shows it.
- text: numbers, names in order, tempos and clock times as a form shows them.
- tab_box: a settings page's tab box, its tabs and columns, and where the cursor goes between its fields.
"""
