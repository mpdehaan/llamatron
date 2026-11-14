# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""A grab takes the root of the chord it hears, the note the chord was built on, however the chord is inverted or voiced, the user's rule of 2026-11-11."""

import unittest

from llamatron.composition.file_format import ClipSlotSetting, GeneratorKind, PatternSetting, Row, SceneSetting, Section, TrackSetting
from test_registers import song
from rendering import render_data
from llamatron.exporters.timing import timed_events

CHORDS = 'chords'
BASS = 'bass'
HARMONY = 'harmony'
GRABBING = 'grabbing'
VOICED = 'voiced'
PROGRESSION = 'changes'
TRIAD = '3'
STEPS = 4
C = 60
G = 67
A = 69
F = 65
OCTAVE = 12


def grabbed(*, inversion=None, voiced=False, chords=(1, 5, 6, 4)):
    """Return the notes the bass grabs from a chord track playing a C triad a bar through a progression, inverted or voice-led as asked."""
    chord_pattern = {PatternSetting.STEPS: 1, PatternSetting.STEP_SIZE: '1', Row.DEGREE: [1], Row.OCTAVE: [5], Row.CHORD: [TRIAD]}
    if inversion is not None:
        chord_pattern[Row.INVERSION] = [inversion]
    bass_pattern = {PatternSetting.STEPS: 1, PatternSetting.STEP_SIZE: '1', Row.GRAB: [True]}
    data = song(
        patterns={HARMONY: chord_pattern, GRABBING: bass_pattern},
        scenes=[{SceneSetting.TRACKS: {
            CHORDS: {ClipSlotSetting.PATTERN: HARMONY, ClipSlotSetting.REPEAT: STEPS, ClipSlotSetting.CHAINS: [PROGRESSION]},
            BASS: {ClipSlotSetting.PATTERN: GRABBING, ClipSlotSetting.REPEAT: STEPS, ClipSlotSetting.GRAB_TRACK: CHORDS},
        }}],
        tracks=(CHORDS, BASS),
    )
    data[Section.TRACKS][CHORDS] = {TrackSetting.MUTE: True}
    data[Section.PROGRESSIONS] = {PROGRESSION: {'chords': list(chords)}}
    data[Section.CHAINS] = {PROGRESSION: [{GeneratorKind.PROGRESSION: PROGRESSION}]}
    if voiced:
        data[Section.VOICE_LEADINGS] = {VOICED: {}}
        data[Section.CHAINS][PROGRESSION].append({GeneratorKind.VOICE_LEADING: VOICED})
    return [pitch for _, _, pitch, _ in notes_on(data, track=1)]


def notes_on(data, *, track):
    grid = render_data(data)
    clip = grid.get_clip(row=grid.get_rows()[0], column=grid.get_columns()[track])
    return sorted(timed_events(clip=clip, scale=clip.get_scale())[0])


class TestGrabbingTheRoot(unittest.TestCase):

    def test_a_chord_in_root_position_gives_its_root(self):
        self.assertEqual(grabbed(), [C, G, A, F])

    def test_an_inverted_chord_still_gives_its_root(self):
        self.assertEqual(grabbed(inversion=1), [C + OCTAVE, G + OCTAVE, A + OCTAVE, F + OCTAVE])
        self.assertEqual([pitch % OCTAVE for pitch in grabbed(inversion=2)], [C % OCTAVE, G % OCTAVE, A % OCTAVE, F % OCTAVE])

    def test_a_voice_led_chord_still_gives_its_root(self):
        self.assertEqual([pitch % OCTAVE for pitch in grabbed(voiced=True)], [C % OCTAVE, G % OCTAVE, A % OCTAVE, F % OCTAVE])

