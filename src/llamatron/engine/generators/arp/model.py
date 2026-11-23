# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The settings of the arp generator: their names, their checks and their defaults, as a set file holds them."""

from llamatron.engine.generators import settings_base
from llamatron.engine.generators.arp import generator as arp, schema
from llamatron.engine.generators.arp.generator import _check_offsets, Arp, ChordOrder, OctaveJump
from llamatron.engine.generators.settings_base import GeneratorSettings
from llamatron.model.file import corrections
from llamatron.model.file.checks import Bars, is_whole_number, is_whole_number_from, time_length
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects.traits import HasCells
from llamatron.model.schema import file_format
from llamatron.model.schema.setting import Checked, Choice, described, WholeNumber
from llamatron.user_strings import errors

MIN_OCTAVE_RANGE = 1


# An offset that leaves the note where it is, which a new step of offsets starts with.
NO_OFFSET = 0


# What the arpeggiator is handed to draw its random choices from: the render's seed, never a setting of the file.
ARP_SEED = 'seed'


class ArpSetting:
    """An arpeggiator's settings, as a file names them."""

    RESTART = file_format.GENERATOR_RESTART

    STEP = 'step'
    ORDER = 'order'
    OCTAVE_RANGE = 'octave_range'
    OCTAVE_JUMP = 'octave_jump'
    OFFSETS = 'offsets'




def written_name(member):
    """Return a chord order or octave jump as a file writes it, like 'up' or 'after_each_note'."""
    return member.name.lower()


ORDERS = {written_name(member): member for member in ChordOrder}


OCTAVE_JUMPS = {written_name(member): member for member in OctaveJump}


def _order(name):
    """Return the chord order a file's name for one means."""
    return ORDERS[name]


def _octave_jump(name):
    """Return the octave jump a file's name for one means."""
    return OCTAVE_JUMPS[name]


def _check_arp_offsets(value):
    """Refuse offsets the arp itself would refuse."""
    try:
        _check_offsets(value)
    except ValueError as error:
        raise InvalidValue(errors.ERR_GENERATOR_BAD_OFFSETS.format(problem=error)) from None


def _nearest_offsets(offsets):
    """Return offsets with each one further than the arp allows at the furthest it does, or NO_NEAREST_VALUE unless they're the right number of whole numbers and silent steps."""
    if not isinstance(offsets, list) or not arp.MIN_OFFSETS <= len(offsets) <= schema.MAX_OFFSETS:
        return corrections.NO_NEAREST_VALUE
    if not all(offset is None or is_whole_number(offset) for offset in offsets):
        return corrections.NO_NEAREST_VALUE
    nearest = []
    for offset in offsets:
        if offset is not None:
            offset = min(max(offset, -schema.MAX_OFFSET), schema.MAX_OFFSET)
        nearest.append(offset)
    return nearest


class ArpSettings(HasCells, GeneratorSettings):
    """An arpeggiator's settings: its step length, order, octave range and jump, and offsets."""

    __slots__ = ()

    GENERATOR = Arp
    SETTINGS = described(
        Checked(name=ArpSetting.STEP, check=time_length),
        Choice(name=ArpSetting.ORDER, choices=sorted(ORDERS), default=corrections.LEFT_OUT, error=errors.ERR_NOT_A_CHOICE),
        WholeNumber(name=ArpSetting.OCTAVE_RANGE, lowest=MIN_OCTAVE_RANGE, highest=schema.MAX_OCTAVE_RANGE, error=errors.ERR_GENERATOR_BAD_OCTAVE_RANGE),
        Choice(name=ArpSetting.OCTAVE_JUMP, choices=sorted(OCTAVE_JUMPS), default=corrections.LEFT_OUT, error=errors.ERR_NOT_A_CHOICE),
        Checked(name=ArpSetting.OFFSETS, check=_check_arp_offsets, nearest=_nearest_offsets),
        settings_base.RESTART_SETTING,
    )
    # A step left out is "(pattern)": the step size of the pattern the clip plays.
    TAKEN_AS = {ArpSetting.STEP: time_length, ArpSetting.ORDER: _order, ArpSetting.OCTAVE_JUMP: _octave_jump}

    def _with_defaults(self, *, values, default_seed, default_step, bar):
        values[ARP_SEED] = default_seed
        if ArpSetting.STEP not in values:
            values[ArpSetting.STEP] = default_step
        elif isinstance(values[ArpSetting.STEP], Bars):
            values[ArpSetting.STEP] = bar * values[ArpSetting.STEP].count
        return values

    # Each setting as the file writes it, or None when the file leaves it out, for the tracker to show.

    def get_step(self):
        return self.get_written(ArpSetting.STEP)

    def get_order(self):
        return self.get_written(ArpSetting.ORDER)

    def get_octave_range(self):
        return self.get_written(ArpSetting.OCTAVE_RANGE)

    def get_octave_jump(self):
        return self.get_written(ArpSetting.OCTAVE_JUMP)

    def get_offsets(self):
        offsets = self.get_written(ArpSetting.OFFSETS)
        if offsets is None:
            return None
        return list(offsets)

    @classmethod
    def new(cls):
        """Return the settings a new arp starts with: an upward order, its step the pattern's."""
        return cls({ArpSetting.ORDER: written_name(ChordOrder.UP)})

    # Editing the offsets one step at a time, as the offsets editor does.

    def set_cell(self, *, step, value):
        """Set one step of the offsets, where None is a silent step."""
        offsets = self._offsets_to_change(step)
        offsets[step] = value
        self.set_setting(name=ArpSetting.OFFSETS, value=offsets)

    def insert_cell(self, step):
        """Add a step that leaves the note where it is, before a step of the offsets, or at the end."""
        offsets = self.get_offsets()
        if offsets is None or not is_whole_number_from(value=step, lowest=0, highest=len(offsets)):
            raise InvalidValue(errors.ERR_NO_SUCH_OFFSET.format(step=step, count=len(offsets or [])))
        offsets.insert(step, NO_OFFSET)
        self.set_setting(name=ArpSetting.OFFSETS, value=offsets)

    def remove_cell(self, step):
        offsets = self._offsets_to_change(step)
        offsets.pop(step)
        self.set_setting(name=ArpSetting.OFFSETS, value=offsets or None)

    def _offsets_to_change(self, step):
        """Return a copy of the offsets with a step to change, or raise InvalidValue if there's no such step."""
        offsets = self.get_offsets()
        if offsets is None:
            raise InvalidValue(errors.ERR_NO_OFFSETS)
        if not is_whole_number_from(value=step, lowest=0, highest=len(offsets) - 1):
            raise InvalidValue(errors.ERR_NO_SUCH_OFFSET.format(step=step, count=len(offsets)))
        return offsets
