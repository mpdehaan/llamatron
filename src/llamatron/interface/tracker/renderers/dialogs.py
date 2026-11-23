# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""How the tracker draws what a dialog shows (interface/forms/dialogs.py): its paragraphs, wrapped or cut to the dialog's width,
dim where said in passing, its answers as a row of boxed buttons, and a picker's list."""

from rich.text import Text

from llamatron.interface.tracker import drawing
from llamatron.interface.tracker.components.button_row import button_row
from llamatron.interface.tracker.drawing import cursor_mark, fit, Style, wrapped
from llamatron.user_strings import marks


def said_lines(*, paragraphs, width):
    """Return the lines of a dialog's paragraphs at a width."""
    lines = []
    for paragraph in paragraphs:
        lines += _paragraph_lines(paragraph=paragraph, width=width)
    return lines


def answer_lines(answers):
    """Return the three lines of a dialog's answers, the selected one double-lined."""
    return button_row(buttons=list(answers.buttons), selected=answers.selected)


def message_lines(*, paragraphs, answers, width):
    """Return what a message or a question shows: its paragraphs, a blank line, and its answers."""
    return [*said_lines(paragraphs=paragraphs, width=width), Text(drawing.NOTHING), *answer_lines(answers)]


def choice_lines(*, choices, width):
    """Return a picker's list: what was typed, dim, then each row after its cursor's mark, cut to the width, a heading dim."""
    lines = []
    if choices.typed:
        lines.append(Text(fit(text=drawing.SPACE + marks.MSG_SEARCH_SHOWN.format(text=choices.typed), width=width), style=Style.DIM))
    for row in choices.rows:
        text = fit(text=cursor_mark(row.under_cursor) + row.text, width=width)
        if row.heading:
            lines.append(Text(text, style=Style.DIM))
        else:
            lines.append(Text(text))
    return lines


def _paragraph_lines(*, paragraph, width):
    if paragraph.one_line:
        return [Text(fit(text=paragraph.text, width=width).rstrip())]
    if paragraph.dim:
        return [Text(line.plain, style=Style.DIM) for line in wrapped(text=paragraph.text, width=width)]
    return wrapped(text=paragraph.text, width=width)
