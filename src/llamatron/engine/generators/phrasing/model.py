# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The settings of the phrasing generator: their names, their checks and their defaults, as a set file holds them."""

from llamatron.engine.generators.phrasing import schema
from llamatron.engine.generators.phrasing.generator import Phrasing
from llamatron.engine.generators.settings_base import GeneratorSettings
from llamatron.model.file import corrections
from llamatron.model.file.checks import reading
from llamatron.model.objects.llama_data import or_default
from llamatron.model.schema.setting import Choice, described
from llamatron.user_strings import errors

class PhrasingSetting:
    """A Phrasing's settings, as a file names them."""

    LINE_BARS = 'line_bars'
    BREATH = 'breath'
    RISE_AND_FALL = 'rise_and_fall'
    NOTES = 'notes'


# How many bars a line of a tune can be, and what a Phrasing does with each setting left out.
LINES_IN_BARS = (1, 2, 4)


DEFAULT_LINE_BARS = 2


PHRASING_DEFAULTS = {
    PhrasingSetting.LINE_BARS: DEFAULT_LINE_BARS, PhrasingSetting.BREATH: schema.QUICK_BREATH, PhrasingSetting.RISE_AND_FALL: schema.LITTLE_RISE,
    PhrasingSetting.NOTES: schema.NOTES_AS_WRITTEN,
}


class PhrasingSettings(GeneratorSettings):
    """A Phrasing's settings: how long a line of the tune is, the breath after it, how far it rises and falls, and how its notes are joined.

    The generator needs the length of a bar, which the song says, so the settings are asked for the generator of one clip (generator_for).
    """

    __slots__ = ()

    GENERATOR = Phrasing
    SETTINGS = described(
        Choice(name=PhrasingSetting.LINE_BARS, choices=LINES_IN_BARS, default=corrections.LEFT_OUT, error=errors.ERR_NOT_A_CHOICE),
        Choice(name=PhrasingSetting.BREATH, choices=schema.BREATHS, default=corrections.LEFT_OUT, error=errors.ERR_NOT_A_CHOICE),
        Choice(name=PhrasingSetting.RISE_AND_FALL, choices=schema.RISES, default=corrections.LEFT_OUT, error=errors.ERR_NOT_A_CHOICE),
        Choice(name=PhrasingSetting.NOTES, choices=schema.JOINS, default=corrections.LEFT_OUT, error=errors.ERR_NOT_A_CHOICE),
    )

    @classmethod
    def new(cls):
        return cls({})

    def get_own(self, name):
        """Return one of the Phrasing's settings, or what the Phrasing does with the setting left out."""
        return or_default(value=self.get_written(name), default=PHRASING_DEFAULTS[name])

    def generator_for(self, *, where, bar):
        """Return the Phrasing of one clip, whose bars are of a length."""
        with reading(where):
            self.check_data(self._settings)
        return Phrasing(
            line=self.get_own(PhrasingSetting.LINE_BARS) * bar, bar=bar, breath=self.get_own(PhrasingSetting.BREATH),
            rise=self.get_own(PhrasingSetting.RISE_AND_FALL), join=self.get_own(PhrasingSetting.NOTES),
        )
