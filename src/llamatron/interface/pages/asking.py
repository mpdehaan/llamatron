# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Asking a person for something a field needs that is more than a line of text: a time signature, checked as it is typed, and
a row of numbers edited cell by cell."""

from dataclasses import dataclass

from llamatron.model.values import time_signature
from llamatron.model.values.time_signature import is_time_signature
from llamatron.user_strings import errors



@dataclass(frozen=True, slots=True, kw_only=True)
class RowAsked:
    """A row of numbers a person edits cell by cell in a dialog: its values as they are, the lowest and the highest a cell may
    hold, the fewest and the most cells the row may have, and the usual row, which the dialog gives back on asking."""

    values: list
    lowest: int
    highest: int
    fewest: int
    most: int
    usual: list


def ask_time_signature(*, page, title, current, then, blank_allowed):
    """Ask for a time signature written like 6/8, and pass it on as text, or None for a blank where that's allowed."""
    def answered(text):
        text = text.strip()
        if not text and blank_allowed:
            then(None)
        elif is_time_signature(text):
            then(text)
        else:
            page.refuse(errors.ERR_TYPED_NOT_A_TIME_SIGNATURE.format(text=text, lowest=time_signature.MIN_BEATS, highest=time_signature.MAX_BEATS, units=time_signature.UNITS_LISTED))
    page.ask_text(title=title, value=current, then=answered)
