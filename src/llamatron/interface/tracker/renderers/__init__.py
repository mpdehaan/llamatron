# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The renderers: the only code that draws the forms' nodes, as Rich text the tracker's pages show.

- settings_page: a settings page, its settings, buttons and remarks, scrolled to the cursor (SettingsPageDrawing).
- fields: a settings page's fields.
- drawn_lines: lines being drawn, with the place of the cursor's.
- statement_rows: a table of statements as a grid.
- tab_box: a tab box, its row of tabs over the box and its columns, and where each field lands in it.
"""
