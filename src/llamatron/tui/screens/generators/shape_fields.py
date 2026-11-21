# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The fields of a shape, Density, Swell or Articulate, which the Scene page, the clip page and the shape generators' editors share: a section heading and its start, end, over and then."""

import functools

from llamatron.model.objects import shapes
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import ShapePart
from llamatron.tui.screens.generators.time_field import time_field
from llamatron.tui.screens.shared.field import ChoiceField, NumberField
from llamatron.user_strings import labels, marks

# Where a nudge starts on a percentage left blank: 100%, which is what blank plays as.
UNCHANGED = 100


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
    return [
        *[NumberField(page=page, label=label(part), number=value(part), start=UNCHANGED, shown=marks.MSG_NONE_SHOWN if value(part) is None else None,
                      lowest=lowest, highest=highest, set=lambda number, part=part: store(part, number), clear=functools.partial(store, part, None))
          for part in (ShapePart.START, ShapePart.END)],
        time_field(page=page, label=label(ShapePart.OVER), written=over, first=labels.MSG_WHOLE_SPAN, store=lambda choice: store(ShapePart.OVER, choice)),
        ChoiceField(page=page, label=label(ShapePart.THEN), choices=file_format.SHAPE_THENS, current=then or file_format.SHAPE_THENS[0],
                    set=lambda choice: store(ShapePart.THEN, None if choice == file_format.SHAPE_THENS[0] else choice)),
    ]


def shape_section(*, page, shape, value, store):
    """Return a shape's section on the Scene page or the clip page: its heading, closed until opened, saying when any part is set, and its four fields."""
    heading = page.heading(label=labels.MSG_SHAPE_NAMES[shape], is_set=lambda: any(value(part) is not None for part in file_format.SHAPE_PARTS))
    return [heading, *shape_fields(page=page, shape=shape, value=value, store=store)]
