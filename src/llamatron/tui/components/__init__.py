# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The parts the pages are drawn from: one object per row of the pattern editor's step grid, each saying what its cells show and what its keys do, and the Arrange page's length bars and the frame around its cursor.

They draw with Rich text and know nothing of Textual, so that the editors could be shown by
another toolkit, and they hold no data of their own: every value is read and written through the
editor's document, so the pattern stays the one place the steps live.
"""
