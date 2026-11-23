# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A list page's table, as plain values: each column's heading, its width, and which way its cells are lined up."""

from typing import NamedTuple


class Align:
    """Which way text is lined up when fitted to a width."""

    LEFT = 'left'
    RIGHT = 'right'
    CENTER = 'center'


class ListColumn(NamedTuple):
    """One column of a list page: its heading, how many cells wide it is, None for the names' column, which takes the room
    left, and which way its cells are lined up (Align)."""

    heading: str
    width: object
    align: str
