# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The settings of the euclid generator: their names, their checks and their defaults, as a set file holds them."""

from llamatron.engine.generators import settings_base
from llamatron.engine.generators.euclid.generator import EuclidMask
from llamatron.engine.generators.settings_base import GeneratorSettings
from llamatron.model.file.checks import Bars, time_length
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects import euclid
from llamatron.model.objects.euclid import euclid_part_settings, euclid_values
from llamatron.model.schema import limits
from llamatron.model.schema.file_format import EuclidPart, NamedRhythm
from llamatron.model.schema.setting import described
from llamatron.user_strings import errors

class EuclidSettings(GeneratorSettings):
    """A Euclid generator's settings, a mask painted on clips on top of their track's: its hits, steps, rotation and step, a bar of sixteenths at the pattern's step size unless set."""

    __slots__ = ()

    GENERATOR = EuclidMask
    SETTINGS = described(*euclid_part_settings(lambda part: part), settings_base.RESTART_SETTING)
    TAKEN_AS = {EuclidPart.STEP: time_length}

    @classmethod
    def new(cls):
        """Return the settings a new Euclid starts with: the tresillo, three hits over eight steps."""
        hits, steps = euclid.NAMED_RHYTHMS[NamedRhythm.TRESILLO]
        return cls({EuclidPart.HITS: hits, EuclidPart.STEPS: steps})

    @classmethod
    def check_data(cls, data):
        super().check_data(data)
        _check_hits_fit(hits=data.get(EuclidPart.HITS), steps=data.get(EuclidPart.STEPS))

    def _with_defaults(self, *, values, default_seed, default_step, bar):
        mask = euclid_values(lambda part: values.get(part))
        step = values.get(EuclidPart.STEP)
        if isinstance(step, Bars):
            step = bar * step.count
        return {EuclidPart.HITS: mask.hits, EuclidPart.STEPS: mask.steps, EuclidPart.ROTATE: mask.rotate, EuclidPart.STEP: step or default_step}

    def get_euclid_setting(self, part):
        return self.get_written(part)

    def get_euclid(self):
        return euclid_values(self.get_written)


def _check_hits_fit(*, hits, steps):
    """Refuse more hits than steps, a bar of sixteenths when the steps are left out."""
    if hits is not None and hits > (limits.DEFAULT_EUCLID_STEPS if steps is None else steps):
        raise InvalidValue(errors.ERR_EUCLID_TOO_MANY_HITS.format(hits=hits, steps=limits.DEFAULT_EUCLID_STEPS if steps is None else steps))
