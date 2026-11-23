# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Velocity field and the two velocity ramp sections, as the Scene page and the clip page show them.

Each value is a percentage of what it scales, 100% for a blank one: the Velocity of the velocity
written, stacking with the instrument's, the track's and, on the clip page, the scene's; each end
of a ramp of that level. A ramp field left blank on the clip page shows the scene's value.
"""

from typing import NamedTuple

from llamatron.interface.tracker.screens.shared.field import NumberField
from llamatron.interface.tracker.screens.shared.percentages import percent_shown
from llamatron.model.objects import velocity_ramps
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import RampPart, VelocitySetting
from llamatron.user_strings import labels, legends, marks


class VelocityValues(NamedTuple):
    """How the velocity fields of a scene or a clip reach its settings: own(name) reads its own, None where blank, above(name)
    the one a blank field takes, from the scene on the clip page and from nothing on the Scene page, and store(name, value)
    keeps one, None leaving it blank."""

    own: object
    above: object
    store: object


def bars_shown(bars):
    """Return a count of bars as a ramp's Over shows it."""
    return marks.MSG_RAMP_ONE_BAR_SHOWN if bars == limits.MIN_RAMP_BARS else marks.MSG_RAMP_BARS_SHOWN.format(bars=bars)


def velocity_field(*, page, values):
    """Return the Velocity field: the percentage of their velocity the notes play at, read from own(name) and kept by
    store(name, value), None leaving it blank, which is 100%: a clip's stacks on its scene's, so it takes nothing from above."""
    own, _, store = values
    name = VelocitySetting.LEVEL
    level = own(name)
    shown = percent_shown(velocity_ramps.AS_WRITTEN if level is None else level)
    return NumberField(
        page=page, label=labels.MSG_VELOCITY_PERCENT_LABEL, number=level, start=velocity_ramps.AS_WRITTEN, shown=shown,
        lowest=limits.MIN_VELOCITY_PERCENT, highest=limits.MAX_VELOCITY_PERCENT, set=lambda number: store(name, number), clear=lambda: store(name, None), clear_what=legends.MSG_RAMP_BLANK_WHAT,
    )


def velocity_ramp_sections(*, page, values):
    """Return the two velocity ramp sections, each closed until opened: the percentage it starts from, the percentage it reaches, and the bars it takes."""
    return [field for way in file_format.RAMP_WAYS for field in velocity_ramp_section(page=page, way=way, values=values)]


def velocity_ramp_section(*, page, way, values):
    """Return one velocity ramp's section: its heading, the percentage of the Velocity it starts from and the one it reaches,
    a blank one 100%, and the bars it takes."""
    own, above, store = values
    names = {part: file_format.VELOCITY_RAMP_SETTINGS[(way, part)] for part in (RampPart.START, RampPart.END, RampPart.OVER)}

    def end_shown(name):
        if own(name) is not None:
            return percent_shown(own(name))
        if above(name) is not None:
            return marks.MSG_FROM_SCENE_SHOWN.format(value=percent_shown(above(name)))
        return percent_shown(velocity_ramps.AS_WRITTEN)

    def end_field(part):
        name = names[part]
        taken = above(name)
        return NumberField(
            page=page, label=labels.MSG_VELOCITY_RAMP_LABELS[(way, part)], number=own(name), start=velocity_ramps.AS_WRITTEN if taken is None else taken,
            shown=end_shown(name), lowest=limits.MIN_VELOCITY_PERCENT, highest=limits.MAX_VELOCITY_PERCENT, set=lambda number: store(name, number),
            clear=lambda: store(name, None), clear_what=legends.MSG_RAMP_BLANK_WHAT,
        )
    return [
        page.heading(label=labels.MSG_VELOCITY_RAMP_SECTIONS[way], is_set=lambda: any(own(name) is not None for name in names.values())),
        *[end_field(part) for part in (RampPart.START, RampPart.END)],
        _over_field(page=page, way=way, values=values),
    ]


def _over_field(*, page, way, values):
    """Return the field of the bars a ramp takes, none until given."""
    own, above, store = values
    over = file_format.VELOCITY_RAMP_SETTINGS[(way, RampPart.OVER)]
    if own(over) is not None:
        over_shown = bars_shown(own(over))
    elif above(over) is not None:
        over_shown = marks.MSG_FROM_SCENE_SHOWN.format(value=bars_shown(above(over)))
    else:
        over_shown = marks.MSG_NONE_SHOWN
    return NumberField(
        page=page, label=labels.MSG_VELOCITY_RAMP_LABELS[(way, RampPart.OVER)], number=own(over), start=limits.MIN_RAMP_BARS if above(over) is None else above(over), shown=over_shown,
        lowest=limits.MIN_RAMP_BARS, highest=limits.MAX_RAMP_BARS, set=lambda number: store(over, number), clear=lambda: store(over, None), clear_what=legends.MSG_RAMP_BLANK_WHAT,
    )
