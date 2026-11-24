# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""An instrument's preview pattern: a pattern of its own for designing its sound before any music exists, which the
Instrument page's Preview pattern button opens and Listen plays.

Each instrument holds its own preview, written inside it under `preview`, so that it is renamed, copied and deleted with
the instrument, and it is never one of the set's patterns, so that no list of patterns, picker or chain ever shows one. The
pattern editor reaches one by a key, PreviewOf, the instrument's name, which only the set's get_pattern resolves, so that every edit, munge and undo works on it as on any pattern. A tonal
instrument's preview plays under a hidden chromatic scale on C, so that any note can be written without choosing a key; a
drum instrument's under none. A new preview is a sixteenth-note run up and down C major, or a drum's C on each quarter, in the set's
default drum octave, where the built-in drums play at their own pitch.
"""

from typing import NamedTuple

from llamatron.model.schema.file_format import PatternSetting, Row
from llamatron.model.values.note import NoteName
from llamatron.model.values.scale import ScaleType

PREVIEW_STEPS = 16
PREVIEW_STEP_SIZE = '1/16'
PREVIEW_OCTAVE = 4
# C major up and down, as steps of the chromatic scale from C: C D E F G A B C, then C B A G F E D C, the top C an octave up.
MAJOR_STEPS = (1, 3, 5, 6, 8, 10, 12, 13, 13, 12, 10, 8, 6, 5, 3, 1)
STEPS_IN_AN_OCTAVE = 12
QUARTER_STEPS = 4


class PreviewOf(NamedTuple):
    """The key of an instrument's preview pattern, by the instrument's name: what the pattern editor opens it by."""

    instrument: str


class PreviewScale(NamedTuple):
    """The key of the hidden chromatic scale on C a tonal preview plays under: what a preview's scale is named by."""

    kind: str = ScaleType.CHROMATIC


def is_preview(name):
    """Return whether a pattern's name is a preview's key rather than a pattern of the set's."""
    return type(name) is PreviewOf


def is_preview_scale(name):
    """Return whether a scale's name is the hidden chromatic scale's key rather than a scale of the set's."""
    return type(name) is PreviewScale


def starting_preview(*, drum):
    """Return a new preview pattern's data: a drum's C on each quarter in the default drum octave, or a run up and down C major on the chromatic scale."""
    if drum:
        # No octave written, so each C plays in the set's default drum octave, the very C the built-in drums play at their own
        # pitch on.
        degrees = [NoteName.C if step % QUARTER_STEPS == 0 else None for step in range(PREVIEW_STEPS)]
        return {PatternSetting.STEPS: PREVIEW_STEPS, PatternSetting.STEP_SIZE: PREVIEW_STEP_SIZE, PatternSetting.DRUM: True, Row.DEGREE: degrees}
    degrees = []
    octaves = []
    for step in MAJOR_STEPS:
        degrees.append((step - 1) % STEPS_IN_AN_OCTAVE + 1)
        octaves.append(PREVIEW_OCTAVE + (step - 1) // STEPS_IN_AN_OCTAVE)
    return {PatternSetting.STEPS: PREVIEW_STEPS, PatternSetting.STEP_SIZE: PREVIEW_STEP_SIZE, PatternSetting.SCALE_LENGTH: STEPS_IN_AN_OCTAVE,
            Row.DEGREE: degrees, Row.OCTAVE: octaves}
