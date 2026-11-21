# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The settings of the drift generator: their names, their checks and their defaults, as a set file holds them."""

from llamatron.engine.generators import settings_base
from llamatron.engine.generators.settings_base import GeneratorSettings
from llamatron.model.file import corrections
from llamatron.model.file.checks import listed, time_length
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import DriftValue, RegisterName
from llamatron.model.schema.setting import Checked, Choice, described, WholeNumber
from llamatron.model.values import note
from llamatron.user_strings import errors

class DriftSetting:
    """A drift's own settings, as a file names them. Each version's settings are named in VERSIONED, with the version's letter in front."""

    RESTART = file_format.GENERATOR_RESTART

    EVERY = 'every'
    STEPS_TO_B = 'steps_to_b'
    DIRECTION = 'direction'


# Each register's add at a drift's trigger, by register.
DRIFT_ADDS = {RegisterName.AX: DriftValue.AX_ADD, RegisterName.BX: DriftValue.BX_ADD, RegisterName.CX: DriftValue.CX_ADD, RegisterName.DX: DriftValue.DX_ADD}


# A version's values, in the order the editor lists them: (name, lowest, highest) for each number, and the two choices.
DRIFT_NUMBERS = [
    *[(name, limits.MIN_REGISTER_VALUE, limits.MAX_REGISTER_VALUE) for name in DRIFT_ADDS.values()],
    (DriftValue.VELOCITY, -limits.MAX_REGISTER_VALUE, limits.MAX_REGISTER_VALUE),
    (DriftValue.PROBABILITY, -limits.MAX_PROBABILITY, limits.MAX_PROBABILITY),
    (DriftValue.DEGREE, -limits.MAX_DRIFT_DEGREE, limits.MAX_DRIFT_DEGREE),
    (DriftValue.DEGREE_RANDOM, limits.MIN_PROBABILITY, limits.MAX_DRIFT_DEGREE),
    (DriftValue.SCALE_PROBABILITY, limits.MIN_PROBABILITY, limits.MAX_PROBABILITY),
    (DriftValue.ROOT_PROBABILITY, limits.MIN_PROBABILITY, limits.MAX_PROBABILITY),
]


DRIFT_VALUES = [
    *DRIFT_ADDS.values(), DriftValue.VELOCITY, DriftValue.PROBABILITY, DriftValue.DEGREE, DriftValue.DEGREE_RANDOM,
    DriftValue.SCALE, DriftValue.SCALE_PROBABILITY, DriftValue.ROOT, DriftValue.ROOT_PROBABILITY,
]


VERSIONED = '{version}_{value}'


# How many triggers a drift takes from A to B, unless it says.
DEFAULT_STEPS_TO_B = 16


MIN_STEPS_TO_B = 1


MAX_STEPS_TO_B = 999


def versioned(*, version, value):
    """Return the file's name for one version's value, like a_velocity."""
    return VERSIONED.format(version=version, value=value)


def _check_scale_name(value):
    if not isinstance(value, str) or not value:
        raise InvalidValue(errors.ERR_DRIFT_BAD_SCALE.format(value=value))


def _check_root(value):
    if value not in note.ROOT_NAMES:
        raise InvalidValue(errors.ERR_DRIFT_BAD_ROOT.format(roots=listed(note.ROOT_NAMES), value=value))


def _drift_settings():
    """Return a drift's settings, each described once: its own, then each version's values, A's first."""
    numbers = {name: (lowest, highest) for name, lowest, highest in DRIFT_NUMBERS}
    versions = []
    for version in file_format.DRIFT_VERSIONS:
        for value in DRIFT_VALUES:
            name = versioned(version=version, value=value)
            if value == DriftValue.SCALE:
                versions.append(Checked(name=name, check=_check_scale_name))
            elif value == DriftValue.ROOT:
                versions.append(Checked(name=name, check=_check_root))
            else:
                lowest, highest = numbers[value]
                versions.append(WholeNumber(name=name, lowest=lowest, highest=highest, error=errors.ERR_GENERATOR_BAD_ADD))
    return described(
        Checked(name=DriftSetting.EVERY, check=time_length),
        WholeNumber(name=DriftSetting.STEPS_TO_B, lowest=MIN_STEPS_TO_B, highest=MAX_STEPS_TO_B, error=errors.ERR_GENERATOR_BAD_ADD),
        Choice(name=DriftSetting.DIRECTION, choices=file_format.DRIFT_DIRECTIONS, default=corrections.LEFT_OUT, error=errors.ERR_NOT_A_CHOICE),
        *versions,
        settings_base.RESTART_SETTING,
    )


class DriftSettings(GeneratorSettings):
    """A drift's settings: how often it triggers, how many triggers it takes from A to B, which way it moves, and what each version sets.

    A drift is not a generator a chain runs on a clip's notes: the render reads these settings
    as one process for the whole song (playback/drift.py), and every clip whose chain names the
    drift hears it, so GENERATOR is None and a chain step naming a drift changes nothing itself.
    """

    __slots__ = ()

    GENERATOR = None
    SETTINGS = _drift_settings()

    @classmethod
    def new(cls):
        """Return the settings a new drift starts with: nothing set, so it does nothing until a version is given values."""
        return cls({})

    def get_every(self):
        """Return how often it triggers, as the file writes it, or None for one bar of the song it plays in."""
        return self.get_written(DriftSetting.EVERY)

    def get_steps_to_b(self):
        return self.get_written(DriftSetting.STEPS_TO_B) or DEFAULT_STEPS_TO_B

    def get_direction(self):
        return self.get_written(DriftSetting.DIRECTION) or file_format.DRIFT_DIRECTIONS[0]

    def get_value(self, *, version, value):
        """Return one version's value as the file writes it, or None when the version leaves it out."""
        return self.get_written(versioned(version=version, value=value))

    def adds_to_registers(self):
        """Return whether either version adds to a register at its triggers."""
        return any(self.get_value(version=version, value=value) for version in file_format.DRIFT_VERSIONS for value in DRIFT_ADDS.values())
