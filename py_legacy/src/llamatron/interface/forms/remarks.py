# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The lines a page shows under its settings, as plain values: each its words, indented as a settings page's are, and whether
it is said in passing, which the tracker draws dim."""

from dataclasses import dataclass

# How far in a remark starts, as a settings page's lines do.
INDENT = '  '
NO_TEXT = ''


@dataclass(frozen=True, slots=True, kw_only=True)
class Remark:
    """One line under a page's settings: its words, and whether it is said in passing, drawn dim."""

    text: str = NO_TEXT
    dim: bool = False


def remark(text):
    """Return a line of words under the settings, indented as they are."""
    return Remark(text=INDENT + text)


def dim_remark(text):
    """Return a line said in passing under the settings, indented and dim."""
    return Remark(text=INDENT + text, dim=True)


def blank_remark():
    """Return an empty line between remarks."""
    return Remark()
