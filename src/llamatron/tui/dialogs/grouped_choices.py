# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Choices offered in groups, each under a heading: a picker's list with its headings, and what each place in it stands for."""

from llamatron.model.schema import file_format
from llamatron.tui import drawing
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.user_strings import labels

# The names a statement of Conditional Execution can read, in the order its pickers list them and its keys step through them: the
# draws, then the registers.
VALUE_NAMES_IN_ORDER = [*file_format.DRAW_NAMES, *file_format.REGISTER_NAMES]
# What choosing a number to type stands for in a value's picker.
NUMBER_CHOSEN = 'number'
# Those names in their groups, each under its heading.
VALUE_GROUPS = [(labels.MSG_PICKER_DRAWS_HEADING, file_format.DRAW_NAMES), (labels.MSG_PICKER_REGISTERS_HEADING, file_format.REGISTER_NAMES)]


class GroupedChoices:
    """A picker's choices in groups: each group a heading, or None for none, and its choices, each what the picker shows and
    what choosing it stands for, with a blank line between groups. The headings and the blank lines are never chosen."""

    __slots__ = ('_shown', '_values', '_headings')

    def __init__(self, groups):
        """groups is a list of (heading or None, [(shown, value), ...])."""
        self._shown = []
        self._values = []
        self._headings = []
        for place, (heading, choices) in enumerate(groups):
            if place:
                self._heading(drawing.NOTHING)
            if heading is not None:
                self._heading(heading)
            for shown, value in choices:
                self._shown.append(shown)
                self._values.append(value)

    def _heading(self, text):
        self._headings.append(len(self._shown))
        self._shown.append(text)
        self._values.append(None)

    def dialog(self, *, title, current):
        """Return the picker, opening on the choice that stands for current, or on the first choice."""
        places = [place for place, value in enumerate(self._values) if place not in self._headings and value == current]
        return ChoiceDialog(title=title, options=self._shown, current=places[0] if places else 0, headings=self._headings)

    def value_at(self, place):
        """Return what the choice at a place in the picker stands for."""
        return self._values[place]


def named_choices(names):
    """Return names as choices that stand for themselves."""
    return [(name, name) for name in names]


def number_or_names():
    """Return the groups of a value's picker: a number to type under the constant's heading, then the draws and the registers."""
    return value_groups(first=(labels.MSG_PICKER_CONSTANT_HEADING, [(labels.MSG_STATEMENT_NUMBER_CHOICE, NUMBER_CHOSEN)]))


def value_groups(*, first):
    """Return the groups a picker of a statement's part offers: first, a group of its own, then the draws and the registers under their headings."""
    return GroupedChoices([first, *[(heading, named_choices(names)) for heading, names in VALUE_GROUPS]])
