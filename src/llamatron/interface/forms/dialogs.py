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


def said_on_one_line_in_passing(text):
    """Return a line said in passing, dim, kept to the dialog's width."""
    return Said(text=text, one_line=True, dim=True)


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


@dataclass(frozen=True, slots=True, kw_only=True)
class ChoiceRow:
    """One row of a picker's list: its words, whether the cursor is on it, and whether it only heads a group, which is drawn dim
    and never chosen."""

    text: str
    under_cursor: bool = False
    heading: bool = False


@dataclass(frozen=True, slots=True, kw_only=True)
class ChoiceList:
    """A picker's list as it shows: what was typed to search it, or NO_TEXT, and the rows shown, around the cursor."""

    typed: str = NO_TEXT
    rows: tuple = dataclass_field(default_factory=tuple)


@dataclass(frozen=True, slots=True, kw_only=True)
class TypedText:
    """A line being typed: the word before it, where the title alone does not say what is typed, the text, and where the cursor
    is in it, from 0 to the text's length."""

    label: str = NO_TEXT
    text: str = NO_TEXT
    cursor: int = 0


@dataclass(frozen=True, slots=True, kw_only=True)
class DialogRow:
    """One row of a dialog's settings: its label, its value as shown, whether the cursor is on it, drawing the value bold, and
    whether the value cannot be set now, drawing it dim."""

    label: str
    value: str
    under_cursor: bool = False
    blocked: bool = False
