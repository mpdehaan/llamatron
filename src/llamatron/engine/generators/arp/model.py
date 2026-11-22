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
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import RegisterName
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
    # How much each note the arp plays adds to each register, and what each step of the offsets adds.
    AX_ADD = 'ax_add'
    BX_ADD = 'bx_add'
    CX_ADD = 'cx_add'
    DX_ADD = 'dx_add'
    AX_STEP_ADDS = 'ax_step_adds'
    BX_STEP_ADDS = 'bx_step_adds'
    CX_STEP_ADDS = 'cx_step_adds'
    DX_STEP_ADDS = 'dx_step_adds'


# Each register's per-note add and its row of adds under the offsets, by register.
ARP_NOTE_ADDS = {RegisterName.AX: ArpSetting.AX_ADD, RegisterName.BX: ArpSetting.BX_ADD, RegisterName.CX: ArpSetting.CX_ADD, RegisterName.DX: ArpSetting.DX_ADD}


ARP_STEP_ADDS = {
    RegisterName.AX: ArpSetting.AX_STEP_ADDS, RegisterName.BX: ArpSetting.BX_STEP_ADDS, RegisterName.CX: ArpSetting.CX_STEP_ADDS, RegisterName.DX: ArpSetting.DX_STEP_ADDS,
}


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


def _is_step_add(value):
    return value is None or is_whole_number_from(value=value, lowest=limits.MIN_REGISTER_VALUE, highest=limits.MAX_REGISTER_VALUE)


def _check_step_adds(value):
    """Refuse a row of adds under the offsets unless it is a list of 1 to 16 adds or blanks."""
    if not isinstance(value, list) or not arp.MIN_OFFSETS <= len(value) <= schema.MAX_OFFSETS or not all(_is_step_add(add) for add in value):
        raise InvalidValue(errors.ERR_GENERATOR_BAD_STEP_ADDS.format(most=schema.MAX_OFFSETS, lowest=limits.MIN_REGISTER_VALUE, highest=limits.MAX_REGISTER_VALUE, value=value))


class ArpSettings(HasCells, GeneratorSettings):
    """An arpeggiator's settings: its step length, order, octave range and jump, and offsets."""

    __slots__ = ()

    MAY_ADD_TO_REGISTERS = True

    GENERATOR = Arp
    SETTINGS = described(
        Checked(name=ArpSetting.STEP, check=time_length),
        Choice(name=ArpSetting.ORDER, choices=sorted(ORDERS), default=corrections.LEFT_OUT, error=errors.ERR_NOT_A_CHOICE),
        WholeNumber(name=ArpSetting.OCTAVE_RANGE, lowest=MIN_OCTAVE_RANGE, highest=schema.MAX_OCTAVE_RANGE, error=errors.ERR_GENERATOR_BAD_OCTAVE_RANGE),
        Choice(name=ArpSetting.OCTAVE_JUMP, choices=sorted(OCTAVE_JUMPS), default=corrections.LEFT_OUT, error=errors.ERR_NOT_A_CHOICE),
        Checked(name=ArpSetting.OFFSETS, check=_check_arp_offsets, nearest=_nearest_offsets),
        *[WholeNumber(name=name, lowest=limits.MIN_REGISTER_VALUE, highest=limits.MAX_REGISTER_VALUE, error=errors.ERR_GENERATOR_BAD_ADD) for name in ARP_NOTE_ADDS.values()],
        *[Checked(name=name, check=_check_step_adds) for name in ARP_STEP_ADDS.values()],
        settings_base.RESTART_SETTING,
    )
    # A step left out is "(pattern)": the step size of the pattern the clip plays.
    REQUIRED = []
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

    def get_note_add(self, register):
        """Return how much each note the arp plays adds to a register, or None for nothing."""
        return self.get_written(ARP_NOTE_ADDS[register])

    def get_step_adds(self, register):
        """Return what each step of the offsets adds to a register, one a step with None for nothing, or None when the arp has no offsets."""
        offsets = self.get_offsets()
        if offsets is None:
            return None
        adds = self.get_written(ARP_STEP_ADDS[register]) or []
        # The adds are as many as the offsets, a blank for each past the last written.
        lined_up = []
        for place in range(len(offsets)):
            if place < len(adds):
                lined_up.append(adds[place])
            else:
                lined_up.append(None)
        return lined_up

    def adds_to_registers(self):
        """Return whether its notes or its offsets' steps add to any register."""
        for register in file_format.REGISTER_NAMES:
            if self.get_note_add(register) or any(self.get_step_adds(register) or []):
                return True
        return False

    def set_step_add(self, *, register, step, add):
        """Set what one step of the offsets adds to a register, where None or 0 adds nothing; a row that adds nothing is left out of the file."""
        self._offsets_to_change(step)
        adds = self.get_step_adds(register)
        adds[step] = add or None
        if not any(adds):
            adds = None
        self.set_setting(name=ARP_STEP_ADDS[register], value=adds)

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
        rows = {register: self.get_step_adds(register) for register in file_format.REGISTER_NAMES}
        offsets.insert(step, NO_OFFSET)
        self.set_setting(name=ArpSetting.OFFSETS, value=offsets)
        for register, adds in rows.items():
            if any(adds):
                self.set_setting(name=ARP_STEP_ADDS[register], value=adds[:step] + [None] + adds[step:])

    def remove_cell(self, step):
        offsets = self._offsets_to_change(step)
        rows = {register: self.get_step_adds(register) for register in file_format.REGISTER_NAMES}
        offsets.pop(step)
        self.set_setting(name=ArpSetting.OFFSETS, value=offsets or None)
        for register, adds in rows.items():
            kept = adds[:step] + adds[step + 1:]
            if not any(kept):
                kept = None
            self.set_setting(name=ARP_STEP_ADDS[register], value=kept)

    def _offsets_to_change(self, step):
        """Return a copy of the offsets with a step to change, or raise InvalidValue if there's no such step."""
        offsets = self.get_offsets()
        if offsets is None:
            raise InvalidValue(errors.ERR_NO_OFFSETS)
        if not is_whole_number_from(value=step, lowest=0, highest=len(offsets) - 1):
            raise InvalidValue(errors.ERR_NO_SUCH_OFFSET.format(step=step, count=len(offsets)))
        return offsets
