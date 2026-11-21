# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Helpers that build small songs from pieces, for the tests of song files and what they play."""

import yaml

from llamatron.engine.timing.timing import timed_events
from llamatron.model.schema.file_format import ClipSlotSetting, PatternSetting, Row, Section
from tests.support.gate_conversion import to_gates
from tests.support.rendering import render_data

# Names the tests give to their own things, and other values they use.
DURATION = 'duration'
ROWS = 'rows'
X = 'x'
LEAD = 'lead'
BASIC = """
tempo: 120
scale: C major
scales:
  C major: { root: C, type: major }
  C minor: { root: C, type: minor }
  C dorian: { root: C, type: dorian }
default_octave: 4
patterns:
  a: { steps: 4, step_size: 1/4, degree: [1, 3, ~, ~] }
  b: { steps: 4, step_size: 1/4, degree: [5, 6, 7, 1], octave: [4, 4, 4, 5] }
  hit: { steps: 4, drum: true, degree: [C, ~, ~, ~] }
tracks:
  lead: {}
  kick: {}
scenes:
  - name: one
    tracks:
      lead: { pattern: a }
      kick: { pattern: hit, loop: true }
"""


def pat(*steps, drum=False, **rows):
    """Return a pattern from [what, duration] steps, with None as what for a rest.

    Each duration becomes a gate, followed by empty steps for the rest of its time, as
    gate_conversion explains, so tests can still write a melody as notes and their lengths.
    """
    pattern = {PatternSetting.STEPS: len(steps), Row.DEGREE: [s[0] for s in steps], DURATION: [s[1] for s in steps]}
    if drum:
        pattern[PatternSetting.DRUM] = True
    pattern.update(rows)
    return to_gates(old=pattern)


def build(text):
    return render_data(yaml.safe_load(text))


def with_parts(**parts):
    data = yaml.safe_load(BASIC)
    patterns = {**data[Section.PATTERNS], **parts.pop(Section.PATTERNS, {})}
    data.update(parts, patterns=patterns)
    return data


def clip(*, song, scene, track):
    return song.get_clip(row=song.get_rows()[scene - 1], column=[t for t in song.get_columns() if t.get_name() == track][0])


def pitches(a_clip):
    return [pitch for _, _, pitch, _ in sorted(timed_events(clip=a_clip, scale=a_clip.get_scale())[0])]


def lead_data(*steps, clip_slot=None, **parts):
    """Return the data of a song with one clip on the lead track, playing the given steps."""
    rows = parts.pop(ROWS, {})
    return with_parts(
        patterns={X: pat(*steps, **rows), **parts.pop(Section.PATTERNS, {})},
        scenes=[{Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: X, **(clip_slot or {})}}}], **parts,
    )


def lead_song(*steps, **parts):
    """Return a song with one clip on the lead track, playing the given steps."""
    return render_data(lead_data(*steps, **parts))


def lead(*steps, **parts):
    return clip(song=lead_song(*steps, **parts), scene=1, track=LEAD)
