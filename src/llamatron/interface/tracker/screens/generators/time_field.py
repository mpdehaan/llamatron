# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The field of a time setting, Step, Every or Over, which every page with one shares: the one list of times, after the setting's own first choice."""

from llamatron.interface.tracker.screens.shared.field import ChoiceField
from llamatron.model.schema import file_format
from llamatron.user_strings import labels


def time_field(*, page, label, written, first, store):
    """Return a time setting's field: first, which stands for the setting left blank, then the list of times.

    written is the setting as the file holds it, or None for blank, and store(value) keeps a
    choice, None for first. A value the list doesn't have, like a length typed into a file, is
    offered too, after the list, so that a field never loses what the set holds. A choice that
    is the same as first, like Every's 1 bar, is first and not offered twice.
    """
    times = [time for time in file_format.TIME_CHOICES if time != first]
    current = first if written is None else str(written)
    if current != first and current not in times:
        times.append(current)
    choices = [first, *times]
    return ChoiceField(
        page=page, label=label, choices=choices, current=current, names=[labels.MSG_TIME_NAMES.get(choice, choice) for choice in choices],
        shown=labels.MSG_TIME_NAMES.get(current, current), set=lambda choice: store(None if choice == first else choice), clear=lambda: store(None),
    )
