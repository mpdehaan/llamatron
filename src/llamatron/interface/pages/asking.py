# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Asking a person for something a field needs that is more than a line of text: a time signature, checked as it is typed."""

from llamatron.model.values import time_signature
from llamatron.model.values.time_signature import is_time_signature
from llamatron.user_strings import errors


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
