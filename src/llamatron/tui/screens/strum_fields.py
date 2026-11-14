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
"""The fields of a strum, which the track editor's and the clip page's + Strum sections and the Strum editor share: direction, spread, fade, loose timing and upstroke strings."""

from llamatron.composition.file_format import STRUM_DIRECTIONS, STRUM_SPREADS, UPSTROKE_STRINGS, StrumPart
from llamatron.composition.limits import MAX_LOOSE_TIMING, MAX_STRUM_FADE, MIN_STRUM_PERCENT
from llamatron.composition.strum import DEFAULT_SPREAD, DEFAULT_UPSTROKE_STRINGS, SPREAD_MILLISECONDS
from llamatron.strings.labels import MSG_STRUM_LABEL, MSG_STRUM_FIELD_LABELS, MSG_STRUM_PART_LABELS, MSG_STRUM_WORDS
from llamatron.strings.marks import MSG_NONE_SHOWN, MSG_SPREAD_SHOWN
from llamatron.tui.screens.field import ChoiceField, NumberField

NO_PERCENT = 0


def spread_name(spread):
    return MSG_SPREAD_SHOWN.format(name=spread, milliseconds=SPREAD_MILLISECONDS[spread])


def strum_fields(*, page, value, store, first=None, prefixed=True, inherited=None):
    """Return a strum's five fields, each part read by value(part) and kept by store(part, value), None leaving it blank.

    first is the direction's choice that stands for blank, like (none) on a track or (track) on a
    clip, or None where a direction is always set, as on a Strum generator. prefixed puts Strum
    in front of each label, as on a page where the strum is one section among others. inherited is
    what a blank direction shows, the value it takes and where from, such as down (from track).
    """
    def label(part):
        return MSG_STRUM_FIELD_LABELS[part] if prefixed else MSG_STRUM_PART_LABELS[part]

    directions = STRUM_DIRECTIONS if first is None else [first, *STRUM_DIRECTIONS]
    direction = value(StrumPart.DIRECTION)
    current = direction if direction is not None else (first if first is not None else STRUM_DIRECTIONS[0])
    spread = value(StrumPart.SPREAD) or DEFAULT_SPREAD
    upstroke = value(StrumPart.UPSTROKE_STRINGS) or DEFAULT_UPSTROKE_STRINGS

    def percent(part, highest):
        number = value(part)
        return NumberField(
            page=page, label=label(part), number=number, start=NO_PERCENT, shown=MSG_NONE_SHOWN if number is None else None, lowest=MIN_STRUM_PERCENT, highest=highest,
            set=lambda chosen: store(part, chosen or None), clear=lambda: store(part, None),
        )
    return [
        ChoiceField(
            page=page, label=label(StrumPart.DIRECTION), choices=directions, current=current, names=[MSG_STRUM_WORDS.get(choice, choice) for choice in directions],
            shown=inherited if direction is None and inherited is not None else MSG_STRUM_WORDS.get(current, current),
            set=lambda chosen: store(StrumPart.DIRECTION, None if chosen == first else chosen),
        ),
        ChoiceField(
            page=page, label=label(StrumPart.SPREAD), choices=STRUM_SPREADS, current=spread, names=[spread_name(choice) for choice in STRUM_SPREADS],
            shown=spread_name(spread), set=lambda chosen: store(StrumPart.SPREAD, None if chosen == DEFAULT_SPREAD else chosen),
        ),
        percent(StrumPart.FADE, MAX_STRUM_FADE),
        percent(StrumPart.LOOSE_TIMING, MAX_LOOSE_TIMING),
        ChoiceField(
            page=page, label=label(StrumPart.UPSTROKE_STRINGS), choices=UPSTROKE_STRINGS, current=upstroke, names=[MSG_STRUM_WORDS.get(choice, choice) for choice in UPSTROKE_STRINGS],
            shown=MSG_STRUM_WORDS.get(upstroke, upstroke), set=lambda chosen: store(StrumPart.UPSTROKE_STRINGS, None if chosen == DEFAULT_UPSTROKE_STRINGS else chosen),
        ),
    ]


def strum_section(*, page, value, store, first, inherited=None):
    """Return a + Strum section, closed until opened and saying when anything inside is set, and its five fields."""
    heading = page.heading(label=MSG_STRUM_LABEL, is_set=lambda: value(StrumPart.DIRECTION) is not None)
    return [heading, *strum_fields(page=page, value=value, store=store, first=first, inherited=inherited)]
