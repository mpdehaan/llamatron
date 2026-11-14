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
"""Restart, on every generator, the user's design of 2026-11-11: every clip, on new scene or whole song.

Each test plays a one-bar figure of four quarter notes, C, E, G and A in C major, in scenes of
two bars, so that where a generator's run carries on shows in the second scene.
"""

import unittest

from llamatron.composition.file_format import (
    GENERATOR_RESTART, ClipSlotSetting, GeneratorKind, PatternSetting, Restart, Row, SceneSetting, Section,
)
from llamatron.exporters.timing import timed_events
from rendering import render_data
from llamatron.generators.base import Continuation
from llamatron.generators.voice_leading import VoiceLeading
from llamatron.grid.clip import Clip
from llamatron.music.chord import Chord
from llamatron.music.note import Note, NoteName
from llamatron.support.rational import Rational
from test_registers import LEAD, X, pattern, song

CHAIN = 'chain'
NAME = 'generator'
FIGURE = [1, 3, 5, 6]
STEPS = len(FIGURE)
BARS = 2
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
TRIAD = '3'
# A G major chord high up, G B D from MIDI 79, which a C major chord moves nearest to as C E G from 72.
G_MAJOR_HIGH = [74, 79, 83]
QUARTER = Rational(1, 4)


def two_scenes(*, section, kind, settings, restart=None, first_repeat=1, rows=None):
    """Return a song of two scenes, the lead playing the figure for two bars in each, through one generator with a Restart."""
    figure = dict(pattern(STEPS, **{Row.DEGREE: list(FIGURE), **(rows or {})}), **{PatternSetting.STEP_SIZE: '1/4'})
    clip = {ClipSlotSetting.PATTERN: X, ClipSlotSetting.REPEAT: BARS, ClipSlotSetting.CHAINS: [CHAIN]}
    data = song(patterns={X: figure}, scenes=[
        {SceneSetting.REPEAT: first_repeat, SceneSetting.TRACKS: {LEAD: dict(clip)}},
        {SceneSetting.TRACKS: {LEAD: dict(clip)}},
    ])
    data[section] = {NAME: dict(settings, **({} if restart is None else {GENERATOR_RESTART: restart}))}
    data[Section.CHAINS] = {CHAIN: [{kind: NAME}]}
    return data


def played(data):
    """Return each written scene's notes as (start, pitch, velocity, length)."""
    grid = render_data(data)
    result = []
    for row in grid.get_rows():
        clip = grid.get_clip(row=row, column=grid.get_columns()[0])
        result.append([(start, pitch, velocity, end - start) for start, end, pitch, velocity in sorted(timed_events(clip=clip, scale=clip.get_scale())[0])])
    return result


def first_names(notes):
    return [NAMES[pitch % len(NAMES)] for _, pitch, _, _ in notes[:STEPS]]


def progression(*, restart=None, first_repeat=1):
    return two_scenes(section=Section.PROGRESSIONS, kind=GeneratorKind.PROGRESSION, settings={'chords': [1, 5, 6, 4]}, restart=restart, first_repeat=first_repeat)


class TestTimeFollowingGenerators(unittest.TestCase):

    def test_every_clip_starts_each_clip_on_the_first_chord(self):
        scenes = played(progression())
        self.assertEqual(first_names(scenes[1]), ['C', 'E', 'G', 'A'])

    def test_whole_song_carries_on_into_the_next_scene(self):
        scenes = played(progression(restart=Restart.WHOLE_SONG))
        # Two bars in, the progression has reached its third chord, vi.
        self.assertEqual(first_names(scenes[1]), ['A', 'C', 'E', 'F'])

    def test_on_new_scene_carries_through_repeats_and_starts_a_new_scene_over(self):
        scenes = played(progression(restart=Restart.ON_NEW_SCENE, first_repeat=2))
        self.assertEqual(first_names(scenes[1]), ['A', 'C', 'E', 'F'])
        self.assertEqual(first_names(scenes[2]), ['C', 'E', 'G', 'A'])

    def test_a_euclid_carries_its_rhythm_on(self):
        data = two_scenes(section=Section.EUCLIDS, kind=GeneratorKind.EUCLID, settings={'hits': 1, 'steps': 3}, restart=Restart.WHOLE_SONG)
        scenes = played(data)
        # Eight quarter notes, a hit every third: the second scene's first hit falls on its second step.
        self.assertEqual(len(scenes[0]), 3)
        self.assertEqual(scenes[1][0][0] * STEPS, 1)

    def test_a_swells_ramp_runs_over_the_whole_song(self):
        data = two_scenes(section=Section.SWELLS, kind=GeneratorKind.SWELL, settings={'start': 0, 'end': 100}, restart=Restart.WHOLE_SONG,
                          rows={Row.VELOCITY: [100] * STEPS})
        scenes = played(data)
        self.assertLess(scenes[0][-1][2], scenes[1][0][2])
        self.assertLess(scenes[1][-1][2], 100)


class TestStateKeepingGenerators(unittest.TestCase):

    def test_an_auto_ratchet_carries_its_count_on(self):
        settings = {'counts': [1, 2, 3]}
        fresh = played(two_scenes(section=Section.AUTO_RATCHETS, kind=GeneratorKind.AUTO_RATCHET, settings=settings))
        carried = played(two_scenes(section=Section.AUTO_RATCHETS, kind=GeneratorKind.AUTO_RATCHET, settings=settings, restart=Restart.WHOLE_SONG))
        self.assertEqual(fresh[1], fresh[0])
        # Eight notes used up counts 1 2 3 1 2 3 1 2, so the second scene starts on 3.
        self.assertEqual(carried[1][0][3] * 3, fresh[0][0][3])

    def test_voice_leading_voices_a_clips_first_chord_near_the_chord_it_was_handed(self):
        chord = Clip(notes=[Chord([Note(name=name, octave_number=5, length=QUARTER) for name in (NoteName.C, NoteName.E, NoteName.G)])])
        fresh = VoiceLeading(lowest_octave=4, highest_octave=6).generate(chord)
        handed = VoiceLeading(lowest_octave=4, highest_octave=6, continuation=Continuation(0, None, G_MAJOR_HIGH)).generate(chord)
        self.assertEqual(sorted(note.get_midi_number() for note in fresh.get_notes()[0].get_notes()), [60, 64, 67])
        self.assertEqual(sorted(note.get_midi_number() for note in handed.get_notes()[0].get_notes()), [72, 76, 79])

    def test_a_generator_starts_every_clip_from_what_it_was_handed(self):
        chord = Clip(notes=[Chord([Note(name=name, octave_number=5, length=QUARTER) for name in (NoteName.C, NoteName.E, NoteName.G)])])
        generator = VoiceLeading(lowest_octave=4, highest_octave=6, continuation=Continuation(0, None, G_MAJOR_HIGH))
        self.assertEqual(generator.generate(chord).get_notes(), generator.generate(chord).get_notes())
