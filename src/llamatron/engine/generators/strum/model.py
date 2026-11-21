# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The settings of the strum generator: their names, their checks and their defaults, as a set file holds them."""

from llamatron.engine.generators import settings_base
from llamatron.engine.generators.settings_base import GeneratorSettings
from llamatron.model.objects.strum import strum_part_settings, strum_values
from llamatron.model.schema.file_format import StrumDirection, StrumPart
from llamatron.model.schema.setting import described

class StrumSettings(GeneratorSettings):
    """A Strum generator's settings, which win over a clip's and its track's: its direction, spread, fade, loose timing and upstroke strings.

    Like a drift, it runs on no clip's notes: the renderer reads it for each clip that names it,
    and the exporters' timing strums the notes (engine/timing/timing.py), so GENERATOR is None.
    """

    __slots__ = ()

    GENERATOR = None
    SETTINGS = described(*strum_part_settings(lambda part: part), settings_base.RESTART_SETTING)

    @classmethod
    def new(cls):
        """Return the settings a new Strum starts with: by the beat, so that it strums at once."""
        return cls({StrumPart.DIRECTION: StrumDirection.BY_THE_BEAT})

    def get_strum_setting(self, part):
        return self.get_written(part)

    def get_strum(self):
        """Return how it strums, by the beat when its direction is blank."""
        return strum_values(lambda part: self.get_written(part) if part != StrumPart.DIRECTION else self.get_written(part) or StrumDirection.BY_THE_BEAT)
