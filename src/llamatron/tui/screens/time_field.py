# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""The field of a time setting, Step, Every or Over, which every page with one shares: the one list of times, after the setting's own first choice."""

from llamatron.composition.file_format import TIME_CHOICES
from llamatron.strings.labels import MSG_TIME_NAMES
from llamatron.tui.screens.field import ChoiceField


def time_field(*, page, label, written, first, store):
    """Return a time setting's field: first, which stands for the setting left blank, then the list of times.

    written is the setting as the file holds it, or None for blank, and store(value) keeps a
    choice, None for first. A value the list doesn't have, like a length typed into a file, is
    offered too, after the list, so that a field never loses what the set holds. A choice that
    is the same as first, like Every's 1 bar, is first and not offered twice.
    """
    times = [time for time in TIME_CHOICES if time != first]
    current = first if written is None else str(written)
    if current != first and current not in times:
        times.append(current)
    choices = [first, *times]
    return ChoiceField(
        page=page, label=label, choices=choices, current=current, names=[MSG_TIME_NAMES.get(choice, choice) for choice in choices],
        shown=MSG_TIME_NAMES.get(current, current), set=lambda choice: store(None if choice == first else choice), clear=lambda: store(None),
    )
