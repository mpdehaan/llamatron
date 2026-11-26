# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Small songs for the engine's tests, written as a file's data, and what a track plays in them.

Every pattern plays middle C, MIDI note 60, in C major, unless its rows say otherwise, a quarter note a step, so that every
step is easy to tell apart; scale_notes turns how far each note moved along C major into the notes it moves C3 to.
"""

from llamatron.engine.timing.timing import timed_events
from llamatron.model.objects.named_scale import scale_type_name
from llamatron.model.schema.file_format import ClipSlotSetting, PatternSetting, Row, ScaleSetting, SceneSetting, Section, SongSetting
from llamatron.model.values.note import NoteName
from llamatron.model.values.scale import ScaleType
from llamatron.music_theory.fundamentals import intervals
from tests.support.rendering import render_data

OCTAVE = 5
ROOT = 60
C_MAJOR_STEPS = [0, 2, 4, 5, 7, 9, 11]
STEP_SIZE = '1/4'

# Names the tests give to their own things.
LEAD = 'lead'
MAIN = 'main'
X = 'x'
Y = 'y'


def scale_notes(values):
    """Return the MIDI notes that moves of so many notes along C major take C3 to, one for each move."""
    return [scale_note(value) for value in values]


def scale_note(value):
    octaves, place = divmod(value, len(C_MAJOR_STEPS))
    return ROOT + octaves * intervals.HALF_STEPS_PER_OCTAVE + C_MAJOR_STEPS[place]


def pattern(steps, **rows):
    """Return a pattern of steps that all play C3 unless rows say otherwise."""
    return {PatternSetting.STEPS: steps, PatternSetting.STEP_SIZE: STEP_SIZE, Row.DEGREE: [1] * steps, Row.OCTAVE: [OCTAVE] * steps, **rows}


def song(*, patterns, scenes, draws=None, tracks=(LEAD,)):
    """Return a song in C major of the patterns and scenes given, with a track for each name in tracks, and the draws given."""
    data = {
        Section.SCALES: {MAIN: {ScaleSetting.ROOT: NoteName.C, ScaleSetting.TYPE: scale_type_name(ScaleType.MAJOR)}}, SongSetting.SCALE: MAIN,
        Section.PATTERNS: patterns, Section.TRACKS: {name: {} for name in tracks}, Section.SCENES: scenes,
    }
    if draws:
        data[Section.DRAWS] = draws
    return data


def one_clip(*, rows, steps=1, repeat=1, drum=False):
    """Return a song whose lead plays one pattern, with rows, repeated."""
    made = pattern(steps, **rows)
    if drum:
        made.update({PatternSetting.DRUM: True, Row.DEGREE: [NoteName.C] * steps})
    return song(patterns={X: made}, scenes=[{SceneSetting.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: X, ClipSlotSetting.REPEAT: repeat}}}])


def played(*, data, scene=1, track=LEAD):
    """Return (pitch, velocity) for each note a track plays in a scene, in time order."""
    grid = render_data(data)
    found = grid.get_clip(row=grid.get_rows()[scene - 1], column=[each for each in grid.get_columns() if each.get_name() == track][0])
    return [(pitch, velocity) for _, _, pitch, velocity in sorted(timed_events(clip=found, scale=found.get_scale())[0])]


def pitches(data, **where):
    return [pitch for pitch, _ in played(data=data, **where)]


def velocities(data, **where):
    return [velocity for _, velocity in played(data=data, **where)]
