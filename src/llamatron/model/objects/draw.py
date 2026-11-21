# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A draw: one of the song's four lists of values, AD to DD, that a pattern's steps add to their notes and velocities.

Each time a step uses a draw it takes the value of the draw's next slot, the slots taken in the draw's direction: any direction
a pattern's steps move in, serial, which deals every slot once a round in a random order, or any, which picks a slot at random
every time. A blank slot is passed over without using up a draw.
"""

from llamatron.caching.revised import notes_change
from llamatron.model.file import corrections
from llamatron.model.file.checks import is_whole_number, listed, pass_over_unknown, reading
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects.llama_data import HoldsSettings, own_copy
from llamatron.model.vocabulary import defaults, file_format, limits
from llamatron.model.vocabulary.file_format import DrawSetting
from llamatron.model.vocabulary.setting import Checked, Choice, described, Flag, WholeNumber
from llamatron.user_strings import errors


def is_slot_value(value):
    """Return whether a value can stand in a draw's slot: a whole number in the draws' range, or None for a blank."""
    return value is None or (is_whole_number(value) and limits.MIN_DRAW_VALUE <= value <= limits.MAX_DRAW_VALUE)


def check_slots(value):
    """Raise InvalidValue unless a value is a draw's slots: a list of MIN_DRAW_SLOTS to MAX_DRAW_SLOTS values or blanks."""
    if not isinstance(value, list) or not limits.MIN_DRAW_SLOTS <= len(value) <= limits.MAX_DRAW_SLOTS or not all(is_slot_value(slot) for slot in value):
        raise InvalidValue(errors.ERR_BAD_DRAW_SLOTS.format(lowest=limits.MIN_DRAW_SLOTS, highest=limits.MAX_DRAW_SLOTS, value=value))


SETTINGS = described(
    Choice(name=DrawSetting.DIRECTION, choices=file_format.DRAW_DIRECTIONS, default=corrections.LEFT_OUT, error=errors.ERR_BAD_DRAW_DIRECTION),
    Checked(name=DrawSetting.SLOTS, check=check_slots),
    WholeNumber(name=DrawSetting.VALUE_MIN, lowest=limits.MIN_DRAW_VALUE, highest=limits.MAX_DRAW_VALUE, error=errors.ERR_BAD_VALUE),
    WholeNumber(name=DrawSetting.VALUE_MAX, lowest=limits.MIN_DRAW_VALUE, highest=limits.MAX_DRAW_VALUE, error=errors.ERR_BAD_VALUE),
    Flag(name=DrawSetting.CONDITIONS_REDRAW, error=errors.ERR_DRAW_CONDITIONS_REDRAW_NOT_TRUE_OR_FALSE),
)
DEFAULTS = {
    DrawSetting.DIRECTION: file_format.FORWARD, DrawSetting.SLOTS: [None] * defaults.DEFAULT_DRAW_SLOT_COUNT,
    DrawSetting.VALUE_MIN: limits.MIN_DRAW_VALUE, DrawSetting.VALUE_MAX: limits.MAX_DRAW_VALUE,
    DrawSetting.CONDITIONS_REDRAW: defaults.DEFAULT_DRAW_CONDITIONS_REDRAW,
}


class Draw(HoldsSettings):
    """A draw's direction, its slots, the range its values keep to, and whether a condition reading it draws from it.

    Settings the file leaves out are kept as None, meaning their defaults. Every slot's value lies within the draw's Value Min
    and Value Max: a value typed past either end is held at that end, and moving an end moves every slot past it, since the
    range is there to keep what is typed in bounds.
    """

    __slots__ = ()

    SETTINGS = SETTINGS

    def __init__(self, **settings):
        self.note_change()
        # The slots are kept as a list of the draw's own, so that it shares nothing with the data it was read from.
        self._settings = {name: own_copy(settings.get(name)) for name in SETTINGS}

    @classmethod
    def from_data(cls, *, data, where, song=None):
        with reading(where):
            data = {} if data is None else data
            if not isinstance(data, dict):
                raise InvalidValue(errors.ERR_DRAW_EXPECTED_SETTINGS.format(data=data))
            pass_over_unknown(data=data, allowed=SETTINGS)
            return _checked(data)

    def is_default(self):
        """Return whether every setting is at its default, so the file needn't name the draw."""
        return not self.to_data()

    def copy(self):
        return Draw(**self._settings)

    def to_data(self):
        return {name: own_copy(value) for name, value in self._settings.items() if value is not None}

    def get_direction(self):
        return self._setting(DrawSetting.DIRECTION)

    def get_slots(self):
        """Return the draw's slots in order, each a whole number or None for a blank, as a list of the caller's own."""
        return list(self._setting(DrawSetting.SLOTS))

    def slot_count(self):
        """Return how many slots the draw holds, blank ones included."""
        return len(self._setting(DrawSetting.SLOTS))

    def filled_places(self):
        """Return the places of the slots that hold a value, in order: the slots a draw takes from."""
        return [place for place, value in enumerate(self._setting(DrawSetting.SLOTS)) if value is not None]

    def get_value_min(self):
        return self._setting(DrawSetting.VALUE_MIN)

    def get_value_max(self):
        return self._setting(DrawSetting.VALUE_MAX)

    def value_limits(self):
        """Return the lowest and the highest value any draw's slot or range can take, which Value Min and Value Max lie between."""
        return limits.MIN_DRAW_VALUE, limits.MAX_DRAW_VALUE

    def slot_count_limits(self):
        """Return the fewest and the most slots any draw can hold."""
        return limits.MIN_DRAW_SLOTS, limits.MAX_DRAW_SLOTS

    def redraws_in_conditions(self):
        """Return whether a condition that reads the draw draws from it, as a step's Use Draws row does, rather than only looking at it."""
        return bool(self._setting(DrawSetting.CONDITIONS_REDRAW))

    @notes_change
    def set_setting(self, *, name, value):
        """Change one setting, by its file name, or None to go back to its default. A new Value Min or Value Max moves every slot past it to it."""
        if name not in SETTINGS:
            raise InvalidValue(errors.ERR_DRAW_NO_SUCH_SETTING.format(name=name, names=listed(SETTINGS)))
        settings = {**self._settings, name: value}
        if name in (DrawSetting.VALUE_MIN, DrawSetting.VALUE_MAX) and settings[DrawSetting.SLOTS] is not None:
            lowest, highest = _range_of(settings)
            settings[DrawSetting.SLOTS] = [None if slot is None else max(lowest, min(slot, highest)) for slot in settings[DrawSetting.SLOTS]]
        self._settings = _checked(settings)._settings

    def set_slot(self, *, place, value):
        """Give one slot a value, held within Value Min and Value Max, or make it blank with None."""
        slots = self.get_slots()
        slots[place] = None if value is None else max(self.get_value_min(), min(value, self.get_value_max()))
        self.set_setting(name=DrawSetting.SLOTS, value=slots)

    def set_slot_count(self, count):
        """Make the draw hold count slots: new slots at the end are blank, and slots past the new end are taken away."""
        slots = self.get_slots()
        self.set_setting(name=DrawSetting.SLOTS, value=(slots + [None] * count)[:count])

    def _setting(self, name):
        value = self._settings[name]
        return DEFAULTS[name] if value is None else value


def _range_of(settings):
    """Return the lowest and highest value a draw's settings allow, defaults filled in."""
    lowest = settings.get(DrawSetting.VALUE_MIN)
    highest = settings.get(DrawSetting.VALUE_MAX)
    return (limits.MIN_DRAW_VALUE if lowest is None else lowest), (limits.MAX_DRAW_VALUE if highest is None else highest)


def _checked(data):
    """Return a Draw made from settings, each checked, its range in order and every slot within it."""
    for name, value in data.items():
        # None is a setting left at its default.
        if value is not None:
            SETTINGS[name].check_held(data)
    lowest, highest = _range_of(data)
    if lowest > highest:
        raise InvalidValue(errors.ERR_DRAW_VALUES_OUT_OF_ORDER.format(lowest=lowest, highest=highest))
    for slot in data.get(DrawSetting.SLOTS) or []:
        if slot is not None and not lowest <= slot <= highest:
            raise InvalidValue(errors.ERR_DRAW_SLOT_OUT_OF_RANGE.format(lowest=lowest, highest=highest, value=slot))
    return Draw(**data)
