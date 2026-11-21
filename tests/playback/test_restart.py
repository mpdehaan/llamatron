# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Restart, on every generator: every clip, on new scene or whole song.

Each test plays a one-bar figure of four quarter notes, C, E, G and A in C major, in scenes of
two bars, so that where a generator's run carries on shows in the second scene.
"""

from typing import NamedTuple
import unittest

from llamatron.composition import file_format
from llamatron.composition.file_format import ClipSlotSetting, GeneratorKind, PatternSetting, Restart, Row, SceneSetting, Section
from llamatron.exporters.timing import timed_events
from llamatron.generators.base import Continuation
from llamatron.generators.voice_leading import VoiceLeading
from llamatron.grid.clip import Clip
from llamatron.music.chord import Chord
from llamatron.music.note import Note, NoteName
from llamatron.support.rational import Rational
from tests.playback import test_registers
from tests.playback.test_registers import pattern, song
from tests.support.rendering import render_data

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
    clip = {ClipSlotSetting.PATTERN: test_registers.X, ClipSlotSetting.REPEAT: BARS, ClipSlotSetting.CHAINS: [CHAIN]}
    data = song(patterns={test_registers.X: figure}, scenes=[
        {SceneSetting.REPEAT: first_repeat, SceneSetting.TRACKS: {test_registers.LEAD: dict(clip)}},
        {SceneSetting.TRACKS: {test_registers.LEAD: dict(clip)}},
    ])
    data[section] = {NAME: dict(settings, **({} if restart is None else {file_format.GENERATOR_RESTART: restart}))}
    data[Section.CHAINS] = {CHAIN: [{kind: NAME}]}
    return data


class PlayedNote(NamedTuple):
    """A note of a scene as the tests ask of it: when it starts, its MIDI number, its velocity and how long it lasts."""

    start: object
    pitch: int
    velocity: int
    length: object


def played(data):
    """Return each written scene's notes, each a PlayedNote, in the order they start."""
    grid = render_data(data)
    result = []
    for row in grid.get_rows():
        clip = grid.get_clip(row=row, column=grid.get_columns()[0])
        events, _ = timed_events(clip=clip, scale=clip.get_scale())
        result.append([PlayedNote(start=event.start, pitch=event.midi_number, velocity=event.velocity, length=event.end - event.start) for event in sorted(events)])
    return result


def first_names(notes):
    return [NAMES[note.pitch % len(NAMES)] for note in notes[:STEPS]]


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
        self.assertEqual(scenes[1][0].start * STEPS, 1)

    def test_a_swells_ramp_runs_over_the_whole_song(self):
        data = two_scenes(section=Section.SWELLS, kind=GeneratorKind.SWELL, settings={'start': 0, 'end': 100}, restart=Restart.WHOLE_SONG,
                          rows={Row.VELOCITY: [100] * STEPS})
        scenes = played(data)
        self.assertLess(scenes[0][-1].velocity, scenes[1][0].velocity)
        self.assertLess(scenes[1][-1].velocity, 100)


class TestStateKeepingGenerators(unittest.TestCase):

    def test_an_auto_ratchet_carries_its_count_on(self):
        settings = {'counts': [1, 2, 3]}
        fresh = played(two_scenes(section=Section.AUTO_RATCHETS, kind=GeneratorKind.AUTO_RATCHET, settings=settings))
        carried = played(two_scenes(section=Section.AUTO_RATCHETS, kind=GeneratorKind.AUTO_RATCHET, settings=settings, restart=Restart.WHOLE_SONG))
        self.assertEqual(fresh[1], fresh[0])
        # Eight notes used up counts 1 2 3 1 2 3 1 2, so the second scene starts on 3.
        self.assertEqual(carried[1][0].length * 3, fresh[0][0].length)

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
