# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The settings of the voice leading generator: their names, their checks and their defaults, as a set file holds them."""

from llamatron.engine.generators import settings_base
from llamatron.engine.generators.settings_base import GeneratorSettings
from llamatron.engine.generators.voice_leading.generator import VoiceLeading
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects.llama_data import or_default
from llamatron.model.schema import file_format
from llamatron.model.schema.setting import described, Flag, WholeNumber
from llamatron.model.values import note
from llamatron.user_strings import errors

class VoiceLeadingSetting:
    """A Voice leading's settings, as a file names them: the octaves its chords stay within, and whether the root stays in the bass."""

    RESTART = file_format.GENERATOR_RESTART

    LOWEST_OCTAVE = 'lowest_octave'
    HIGHEST_OCTAVE = 'highest_octave'
    ROOT_IN_BASS = 'root_in_bass'


# A voice leading's chords stay from the bottom of octave 4 to the top of octave 6, around middle C, unless set; the root moves with the chord.
DEFAULT_VOICING_LOWEST_OCTAVE = 4


DEFAULT_VOICING_HIGHEST_OCTAVE = 6


DEFAULT_ROOT_IN_BASS = False


class VoiceLeadingSettings(GeneratorSettings):
    """A Voice leading's settings: its range of octaves and whether the root stays in the bass, each left out for its default."""

    __slots__ = ()

    GENERATOR = VoiceLeading
    SETTINGS = described(
        WholeNumber(name=VoiceLeadingSetting.LOWEST_OCTAVE, lowest=note.MIN_OCTAVE, highest=note.MAX_OCTAVE, error=errors.ERR_BAD_SHAPE_PERCENT),
        WholeNumber(name=VoiceLeadingSetting.HIGHEST_OCTAVE, lowest=note.MIN_OCTAVE, highest=note.MAX_OCTAVE, error=errors.ERR_BAD_SHAPE_PERCENT),
        Flag(name=VoiceLeadingSetting.ROOT_IN_BASS, error=errors.ERR_ROOT_IN_BASS_NOT_TRUE_OR_FALSE),
        settings_base.RESTART_SETTING,
    )

    @classmethod
    def new(cls):
        return cls({})

    @classmethod
    def check_data(cls, data):
        super().check_data(data)
        lowest = data.get(VoiceLeadingSetting.LOWEST_OCTAVE, DEFAULT_VOICING_LOWEST_OCTAVE)
        highest = data.get(VoiceLeadingSetting.HIGHEST_OCTAVE, DEFAULT_VOICING_HIGHEST_OCTAVE)
        if lowest > highest:
            raise InvalidValue(errors.ERR_VOICE_LEADING_RANGE.format(lowest=lowest, highest=highest))

    def _with_defaults(self, *, values, default_seed, default_step, bar):
        values.setdefault(VoiceLeadingSetting.LOWEST_OCTAVE, DEFAULT_VOICING_LOWEST_OCTAVE)
        values.setdefault(VoiceLeadingSetting.HIGHEST_OCTAVE, DEFAULT_VOICING_HIGHEST_OCTAVE)
        values.setdefault(VoiceLeadingSetting.ROOT_IN_BASS, DEFAULT_ROOT_IN_BASS)
        return values

    def get_lowest_octave(self):
        return or_default(value=self.get_written(VoiceLeadingSetting.LOWEST_OCTAVE), default=DEFAULT_VOICING_LOWEST_OCTAVE)

    def get_highest_octave(self):
        return or_default(value=self.get_written(VoiceLeadingSetting.HIGHEST_OCTAVE), default=DEFAULT_VOICING_HIGHEST_OCTAVE)

    def keeps_root_in_bass(self):
        return bool(self.get_written(VoiceLeadingSetting.ROOT_IN_BASS))
