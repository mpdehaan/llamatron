# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A section's scene settings as a set file writes them: the velocity and the tempo as percentages of what they scale.

The wizard works out how loud a section plays as a share of each note's written velocity, 100 for
as written, and its tempo in quarter notes a minute. A scene holds each as a percentage: the
velocity of what is written, each end of a velocity ramp of that velocity, the tempo of the song's,
and each end of a tempo ramp of the scene's tempo. Each is rounded to a whole percent, as a scene
holds it.
"""

from llamatron.model.objects import velocity_ramps
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import RampPart, SceneSetting, VelocitySetting

PERCENT = 100


def as_percentages(*, settings, song_tempo):
    """Return a scene's settings with the ends of its velocity ramps, its tempo and the ends of its tempo ramps written as
    percentages of what each scales; its velocity is a percentage of what is written already."""
    changed = dict(settings)
    level = settings.get(VelocitySetting.LEVEL)
    if level is None:
        level = velocity_ramps.AS_WRITTEN
    _ramps_as_percentages(changed=changed, ramp_settings=file_format.VELOCITY_RAMP_SETTINGS, base=level)
    tempo = settings.get(SceneSetting.TEMPO)
    if tempo is None:
        tempo = song_tempo
    else:
        changed[SceneSetting.TEMPO] = percent_of(value=tempo, base=song_tempo)
    _ramps_as_percentages(changed=changed, ramp_settings=file_format.TEMPO_RAMP_SETTINGS, base=tempo)
    return changed


def percent_of(*, value, base):
    """Return a value as a whole percent of a base."""
    return round(value * PERCENT / base)


def _ramps_as_percentages(*, changed, ramp_settings, base):
    """Write the start and the end of each ramp, by ramp_settings' names, as percentages of a base, where they are given."""
    for way in file_format.RAMP_WAYS:
        for part in (RampPart.START, RampPart.END):
            name = ramp_settings[(way, part)]
            if changed.get(name) is not None:
                changed[name] = percent_of(value=changed[name], base=base)
