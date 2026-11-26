# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A drift's values, each a row of its two versions side by side, A and B: Left and Right move between them, [ and ] change the
one under the cursor, ENTER types a number or picks a scale or root, and Bksp clears it."""

import functools

from llamatron.engine.generators.drift import model as drift_model
from llamatron.engine.generators.drift.model import versioned
from llamatron.interface.forms.nodes import Field, SteppedCells
from llamatron.interface.forms.text import sorted_names
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import DriftValue
from llamatron.model.values import note
from llamatron.user_strings import labels, legends, marks, messages

NOTHING = 0
# The values that pick from a list, the song's scales or the roots, rather than step a number.
CHOSEN_VALUES = (DriftValue.SCALE, DriftValue.ROOT)


def drift_value_rows(page):
    """Return a row for each of the drift's values, in the page's order, each holding version A's and version B's."""
    return [_value_row(page=page, value=value) for value in _values_in_order()]


def _values_in_order():
    """Return each value a version has, in the page's order: the numbers, with the scale and the root before their chances."""
    numbers = [name for name, _, _ in drift_model.DRIFT_NUMBERS]
    return [*numbers[:-2], DriftValue.SCALE, numbers[-2], DriftValue.ROOT, numbers[-1]]


def _value_row(*, page, value):
    """Return one value's row: its label, then version A's cell and version B's."""
    cells = []
    for version in file_format.DRIFT_VERSIONS:
        if value in CHOSEN_VALUES:
            cells.append(_chosen_cell(page=page, value=value, version=version))
        else:
            cells.append(_number_cell(page=page, value=value, version=version))
    return SteppedCells(label=labels.MSG_DRIFT_VALUE_LABELS[value], cells=cells)


def _number_cell(*, page, value, version):
    """Return one version's number, stepped within its range, typed with ENTER, cleared to nothing with Bksp."""
    setting = versioned(version=version, value=value)
    lowest, highest = _range_of(value)
    label = labels.MSG_DRIFT_VALUE_LABELS[value]

    def number():
        return page.settings().get_value(version=version, value=value) or NOTHING

    def step(offset):
        page.store(setting=setting, value=max(min(number() + offset, highest), lowest) or None)

    def typed():
        page.ask_number(
            title=messages.MSG_NUMBER_PROMPT.format(row=label, low=lowest, high=highest), value=number(), low=lowest, high=highest,
            then=lambda chosen: page.store(setting=setting, value=chosen or None),
        )
    return Field(label=label, value=lambda: str(number()), adjust=step, enter=typed, clear=functools.partial(page.store, setting=setting, value=None))


def _chosen_cell(*, page, value, version):
    """Return one version's scale or root, stepped through the list or picked from it, (none) first."""
    setting = versioned(version=version, value=value)
    label = labels.MSG_DRIFT_VALUE_LABELS[value]

    def current():
        return page.settings().get_value(version=version, value=value)

    def step(offset):
        choices = [None, *_choices_of(page=page, value=value)]
        place = max(min(choices.index(current()) + offset, len(choices) - 1), 0)
        page.store(setting=setting, value=choices[place])

    def picked():
        choices = _choices_of(page=page, value=value)
        page.pick(
            title=label, values=[None, *choices], shown=[marks.MSG_NONE_SHOWN, *choices], current=current(),
            then=lambda chosen: page.store(setting=setting, value=chosen),
        )
    return Field(
        label=label, value=lambda: current() or marks.MSG_NONE_SHOWN, adjust=step, enter=picked, enter_what=legends.What.CHOOSE,
        clear=functools.partial(page.store, setting=setting, value=None),
    )


def _range_of(value):
    """Return the lowest and highest a numbered value may be."""
    for name, lowest, highest in drift_model.DRIFT_NUMBERS:
        if name == value:
            return lowest, highest
    raise KeyError(value)


def _choices_of(*, page, value):
    """Return what a scale or root may be: the song's scales by name, or the roots."""
    if value == DriftValue.SCALE:
        return sorted_names(page.document().song().get_setlist().get_scale_names())
    return list(note.ROOT_NAMES)
