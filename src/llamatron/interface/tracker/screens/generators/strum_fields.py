# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The fields of a strum, which the track editor's and the clip page's + Strum sections and the Strum editor share: direction, spread, fade, loose timing and upstroke strings."""

from llamatron.engine.generators.strum import strings as strum_strings
from llamatron.interface.tracker.screens.shared.field import ChoiceField, NumberField
from llamatron.model.objects import strum
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import StrumPart
from llamatron.user_strings import labels, marks

NO_PERCENT = 0


def spread_name(spread):
    return marks.MSG_SPREAD_SHOWN.format(name=spread, milliseconds=strum.SPREAD_MILLISECONDS[spread])


def strum_fields(*, page, value, store, first=None, prefixed=True, inherited=None):
    """Return a strum's five fields, each part read by value(part) and kept by store(part, value), None leaving it blank.

    first is the direction's choice that stands for blank, like (none) on a track or (track) on a
    clip, or None where a direction is always set, as on a Strum generator. prefixed puts Strum
    in front of each label, as on a page where the strum is one section among others. inherited is
    what a blank direction shows, the value it takes and where from, such as down (from track).
    """
    def label(part):
        return labels.MSG_STRUM_FIELD_LABELS[part] if prefixed else labels.MSG_STRUM_PART_LABELS[part]

    directions = file_format.STRUM_DIRECTIONS if first is None else [first, *file_format.STRUM_DIRECTIONS]
    direction = value(StrumPart.DIRECTION)
    current = direction if direction is not None else (first if first is not None else file_format.STRUM_DIRECTIONS[0])
    spread = value(StrumPart.SPREAD) or strum.DEFAULT_SPREAD
    upstroke = value(StrumPart.UPSTROKE_STRINGS) or strum.DEFAULT_UPSTROKE_STRINGS

    def percent(part, highest):
        number = value(part)
        return NumberField(
            page=page, label=label(part), number=number, start=NO_PERCENT, shown=marks.MSG_NONE_SHOWN if number is None else None, lowest=limits.MIN_STRUM_PERCENT, highest=highest,
            set=lambda chosen: store(part, chosen or None), clear=lambda: store(part, None),
        )
    return [
        ChoiceField(
            page=page, label=label(StrumPart.DIRECTION), choices=directions, current=current, names=[labels.MSG_STRUM_WORDS.get(choice, choice) for choice in directions],
            shown=inherited if direction is None and inherited is not None else labels.MSG_STRUM_WORDS.get(current, current),
            set=lambda chosen: store(StrumPart.DIRECTION, None if chosen == first else chosen),
        ),
        ChoiceField(
            page=page, label=label(StrumPart.SPREAD), choices=file_format.STRUM_SPREADS, current=spread, names=[spread_name(choice) for choice in file_format.STRUM_SPREADS],
            shown=spread_name(spread), set=lambda chosen: store(StrumPart.SPREAD, None if chosen == strum.DEFAULT_SPREAD else chosen),
        ),
        percent(StrumPart.FADE, limits.MAX_STRUM_FADE),
        percent(StrumPart.LOOSE_TIMING, limits.MAX_LOOSE_TIMING),
        ChoiceField(
            page=page, label=label(StrumPart.UPSTROKE_STRINGS), choices=file_format.UPSTROKE_STRINGS, current=upstroke, names=[labels.MSG_STRUM_WORDS.get(choice, choice) for choice in file_format.UPSTROKE_STRINGS],
            shown=labels.MSG_STRUM_WORDS.get(upstroke, upstroke), set=lambda chosen: store(StrumPart.UPSTROKE_STRINGS, None if chosen == strum.DEFAULT_UPSTROKE_STRINGS else chosen),
        ),
    ]


def strum_section(*, page, value, store, first, inherited=None):
    """Return a + Strum section, closed until opened and saying when anything inside is set, and its five fields."""
    heading = page.heading(label=strum_strings.MSG_LABEL, is_set=lambda: value(StrumPart.DIRECTION) is not None)
    return [heading, *strum_fields(page=page, value=value, store=store, first=first, inherited=inherited)]
