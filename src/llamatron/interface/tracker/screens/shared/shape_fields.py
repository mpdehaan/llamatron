# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The fields of a shape, Density, Swell or Articulate, which the Scene page, the clip page and the shape generators' editors share: a section heading and its start, end, over and then."""

import dataclasses
import functools

from llamatron.interface.tracker.screens.shared.field import ChoiceField, NumberField
from llamatron.interface.tracker.screens.shared.time_field import time_field
from llamatron.model.objects import shapes
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import ShapePart
from llamatron.user_strings import labels, marks

# Where a nudge starts on a percentage left blank: 100%, which is what blank plays as.
UNCHANGED = 100
# A shape's fields, in the order they are made.
SHAPE_PARTS = (ShapePart.START, ShapePart.END, ShapePart.OVER, ShapePart.THEN)


def shape_fields(*, page, shape, value, store, prefixed=True):
    """Return a shape's four fields: start, end, over and then, each read by value(part) and kept by store(part, value), None leaving it blank.

    prefixed puts the shape's name in front of each label, as on the Scene page and the clip
    page, where three shapes share the page; a shape generator's editor has one and leaves it off.
    """
    lowest, highest = shapes.SHAPE_LIMITS[shape]
    name = labels.MSG_SHAPE_NAMES[shape]

    def label(part):
        return labels.MSG_SHAPE_FIELD_LABELS[part].format(shape=name) if prefixed else labels.MSG_SHAPE_PART_LABELS[part]

    over = value(ShapePart.OVER)
    then = value(ShapePart.THEN)
    percentages = []
    for part in (ShapePart.START, ShapePart.END):
        written = value(part)
        percentages.append(NumberField(
            page=page, label=label(part), number=written, start=UNCHANGED, shown=_percent_shown(written), lowest=lowest, highest=highest,
            set=functools.partial(_store_part, store=store, part=part), clear=functools.partial(store, part, None),
        ))
    fields = [
        *percentages,
        time_field(page=page, label=label(ShapePart.OVER), written=over, first=labels.MSG_WHOLE_SPAN, store=lambda choice: store(ShapePart.OVER, choice)),
        ChoiceField(page=page, label=label(ShapePart.THEN), choices=file_format.SHAPE_THENS, current=then or file_format.SHAPE_THENS[0],
                    set=lambda choice: store(ShapePart.THEN, None if choice == file_format.SHAPE_THENS[0] else choice)),
    ]
    # Under the shape's own heading a field shows its part alone, Start for Density start, keeping its full name.
    return [dataclasses.replace(field, shown_label=labels.MSG_SHAPE_PART_LABELS[part]) for field, part in zip(fields, SHAPE_PARTS)]


def shape_section(*, page, shape, value, store):
    """Return a shape's section on the Scene page or the clip page: its heading, closed until opened, saying when any part is set, and its four fields."""
    heading = page.heading(label=labels.MSG_SHAPE_NAMES[shape], is_set=lambda: any(value(part) is not None for part in file_format.SHAPE_PARTS))
    return [heading, *shape_fields(page=page, shape=shape, value=value, store=store)]


def _percent_shown(written):
    """Return how a start or an end shows: as a percentage once set, and as none while blank."""
    if written is None:
        return marks.MSG_NONE_SHOWN
    return marks.MSG_SHAPE_PERCENT_SHOWN.format(percent=written)


def _store_part(number, *, store, part):
    store(part, number)
