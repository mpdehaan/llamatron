# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""What a dialog shows, as plain nodes with nothing of how they are drawn: the paragraphs it says and the answers it offers. The
tracker draws them (interface/tracker/renderers/dialogs.py), the only code that knows how they look."""

from dataclasses import dataclass, field as dataclass_field

NO_TEXT = ''
# An answer's button that shows no key of its own, since ENTER presses the selected one.
NO_KEY = ''


@dataclass(frozen=True, slots=True, kw_only=True)
class Said:
    """One paragraph a dialog says: its words, wrapped to the dialog's width, or kept to one line and cut short where it is too
    wide; drawn dim where it is said in passing. A paragraph with no words is a blank line."""

    text: str = NO_TEXT
    one_line: bool = False
    dim: bool = False


def said(text):
    """Return a paragraph, wrapped to the dialog."""
    return Said(text=text)


def said_on_one_line(text):
    """Return a line kept to the dialog's width, cut short where it is wider, as a list's line is."""
    return Said(text=text, one_line=True)


def said_in_passing(text):
    """Return a line said in passing, dim."""
    return Said(text=text, dim=True)


def blank():
    """Return an empty line between paragraphs."""
    return Said()


@dataclass(frozen=True, slots=True, kw_only=True)
class Answers:
    """A dialog's answers as a row of boxed buttons: each its key's name, or NO_KEY, and its label; and which is selected, or
    None where the cursor is elsewhere."""

    buttons: tuple = dataclass_field(default_factory=tuple)
    selected: object = None


def answers(*, labels, selected, keys=None):
    """Return a row of answers by their labels, each showing its key where keys names them, or no key."""
    if keys is None:
        keys = [NO_KEY] * len(labels)
    return Answers(buttons=tuple(zip(keys, labels)), selected=selected)

