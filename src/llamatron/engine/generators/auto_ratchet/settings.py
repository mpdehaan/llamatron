# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The settings of the auto ratchet generator: their names, their checks and their defaults, as a set file holds them."""

from llamatron.engine.generators import settings_base
from llamatron.engine.generators.auto_ratchet.generator import AutoRatchet
from llamatron.engine.generators.settings_base import GeneratorSettings
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.schema import file_format
from llamatron.model.schema.setting import Checked, described
from llamatron.user_strings import errors

# What a new AutoRatchet does: splits each note in two.
NEW_AUTO_RATCHET_COUNTS = [2]


class AutoRatchetSetting:
    """An AutoRatchet's settings, as a file names them."""

    RESTART = file_format.GENERATOR_RESTART

    COUNTS = 'counts'


def _check_counts(value):
    if not isinstance(value, list):
        raise InvalidValue(errors.ERR_GENERATOR_NOT_A_LIST.format(name=AutoRatchetSetting.COUNTS, value=value))


class AutoRatchetSettings(GeneratorSettings):
    """An AutoRatchet's settings: the counts it cycles through."""

    __slots__ = ()

    GENERATOR = AutoRatchet
    SETTINGS = described(Checked(name=AutoRatchetSetting.COUNTS, check=_check_counts), settings_base.RESTART_SETTING)
    REQUIRED = [AutoRatchetSetting.COUNTS]

    def get_counts(self):
        """Return its counts as the file writes them, or None when the file leaves them out."""
        counts = self.get_written(AutoRatchetSetting.COUNTS)
        return None if counts is None else list(counts)

    @classmethod
    def new(cls):
        """Return the settings a new AutoRatchet starts with."""
        return cls({AutoRatchetSetting.COUNTS: list(NEW_AUTO_RATCHET_COUNTS)})
