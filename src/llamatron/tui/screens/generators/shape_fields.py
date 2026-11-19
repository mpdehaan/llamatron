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
"""The fields of a shape, Density, Swell or Articulate, which the Scene page, the clip page and the shape generators' editors share: a section heading and its start, end, over and then."""

from llamatron.composition import file_format
from llamatron.composition.file_format import ShapePart
from llamatron.composition import shapes
from llamatron.strings import labels, marks
from llamatron.tui.screens.shared.field import ChoiceField, NumberField
from llamatron.tui.screens.generators.time_field import time_field

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
                      lowest=lowest, highest=highest, set=lambda number, part=part: store(part, number), clear=lambda part=part: store(part, None))
          for part in (ShapePart.START, ShapePart.END)],
        time_field(page=page, label=label(ShapePart.OVER), written=over, first=labels.MSG_WHOLE_SPAN, store=lambda choice: store(ShapePart.OVER, choice)),
        ChoiceField(page=page, label=label(ShapePart.THEN), choices=file_format.SHAPE_THENS, current=then or file_format.SHAPE_THENS[0],
                    set=lambda choice: store(ShapePart.THEN, None if choice == file_format.SHAPE_THENS[0] else choice)),
    ]


def shape_section(*, page, shape, value, store):
    """Return a shape's section on the Scene page or the clip page: its heading, closed until opened, saying when any part is set, and its four fields."""
    heading = page.heading(label=labels.MSG_SHAPE_NAMES[shape], is_set=lambda: any(value(part) is not None for part in file_format.SHAPE_PARTS))
    return [heading, *shape_fields(page=page, shape=shape, value=value, store=store)]
