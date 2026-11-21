# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Velocity field and the two velocity ramp sections, as the Scene page and the clip page show them.

Each value is a percentage of the velocity written. A value left blank shows what plays and
where that comes from: on the clip page the scene's value, and at an end of a ramp the Velocity
field's, which the ramps start from and return to.
"""

import functools

from llamatron.model.objects import velocity_ramps
from llamatron.model.vocabulary import file_format, limits
from llamatron.model.vocabulary.file_format import RampPart, VelocitySetting
from llamatron.tui.screens.shared.field import NumberField
from llamatron.user_strings import labels, legends, marks


def bars_shown(bars):
    """Return a count of bars as a ramp's Over shows it."""
    return marks.MSG_RAMP_ONE_BAR_SHOWN if bars == limits.MIN_RAMP_BARS else marks.MSG_RAMP_BARS_SHOWN.format(bars=bars)


def percent_shown(percent):
    return marks.MSG_VELOCITY_PERCENT_SHOWN.format(percent=percent)


def velocity_field(*, page, own, above, store):
    """Return the Velocity field: how loud the notes play, read from own(name), shown as above(name) gives it where blank, and kept by store(name, value), None leaving it blank."""
    name = VelocitySetting.LEVEL
    level = own(name)
    taken = above(name)
    if level is not None:
        shown = percent_shown(level)
    elif taken is not None:
        shown = marks.MSG_FROM_SCENE_SHOWN.format(value=percent_shown(taken))
    else:
        shown = percent_shown(velocity_ramps.AS_WRITTEN)
    return NumberField(
        page=page, label=labels.MSG_VELOCITY_PERCENT_LABEL, number=level, start=velocity_ramps.AS_WRITTEN if taken is None else taken, shown=shown,
        lowest=limits.MIN_VELOCITY_PERCENT, highest=limits.MAX_VELOCITY_PERCENT, set=lambda number: store(name, number), clear=lambda: store(name, None), clear_what=legends.MSG_RAMP_BLANK_WHAT,
    )


def velocity_ramp_sections(*, page, own, above, store):
    """Return the two velocity ramp sections, each closed until opened: the percentage it starts from, the percentage it reaches, and the bars it takes."""
    return [field for way in file_format.RAMP_WAYS for field in velocity_ramp_section(page=page, way=way, own=own, above=above, store=store)]


def velocity_ramp_section(*, page, way, own, above, store):
    level = own(VelocitySetting.LEVEL)
    level = above(VelocitySetting.LEVEL) if level is None else level
    level = velocity_ramps.AS_WRITTEN if level is None else level
    names = {part: file_format.VELOCITY_RAMP_SETTINGS[(way, part)] for part in (RampPart.START, RampPart.END, RampPart.OVER)}

    def end_shown(name):
        if own(name) is not None:
            return percent_shown(own(name))
        if above(name) is not None:
            return marks.MSG_FROM_SCENE_SHOWN.format(value=percent_shown(above(name)))
        return marks.MSG_FROM_VELOCITY_SHOWN.format(value=percent_shown(level))
    over = names[RampPart.OVER]
    if own(over) is not None:
        over_shown = bars_shown(own(over))
    elif above(over) is not None:
        over_shown = marks.MSG_FROM_SCENE_SHOWN.format(value=bars_shown(above(over)))
    else:
        over_shown = marks.MSG_NONE_SHOWN
    return [
        page.heading(label=labels.MSG_VELOCITY_RAMP_SECTIONS[way], is_set=lambda: any(own(name) is not None for name in names.values())),
        *[NumberField(
            page=page, label=labels.MSG_VELOCITY_RAMP_LABELS[(way, part)], number=own(names[part]), start=level if above(names[part]) is None else above(names[part]), shown=end_shown(names[part]),
            lowest=limits.MIN_VELOCITY_PERCENT, highest=limits.MAX_VELOCITY_PERCENT, set=lambda number, part=part: store(names[part], number), clear=functools.partial(store, names[part], None),
            clear_what=legends.MSG_RAMP_BLANK_WHAT,
        ) for part in (RampPart.START, RampPart.END)],
        NumberField(
            page=page, label=labels.MSG_VELOCITY_RAMP_LABELS[(way, RampPart.OVER)], number=own(over), start=limits.MIN_RAMP_BARS if above(over) is None else above(over), shown=over_shown,
            lowest=limits.MIN_RAMP_BARS, highest=limits.MAX_RAMP_BARS, set=lambda number: store(over, number), clear=lambda: store(over, None), clear_what=legends.MSG_RAMP_BLANK_WHAT,
        ),
    ]
