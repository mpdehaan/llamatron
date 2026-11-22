# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Restart, on every generator: every clip, on new scene or whole song.

Each test plays a one-bar figure of four quarter notes, C, E, G and A in C major, in scenes of
two bars, so that where a generator's run carries on shows in the second scene.
"""

from typing import NamedTuple
import unittest

from llamatron.engine.clips.clip import Clip
from llamatron.engine.generators import auto_ratchet as auto_ratchet_plugin, chords as chords_plugin, shapes as shapes_plugin
from llamatron.engine.generators.base import Continuation
from llamatron.engine.generators.chords import model as chords_model
from llamatron.engine.generators.chords.model import ChordsSetting, ProgressionSetting
from llamatron.engine.generators.chords.voicing import VoiceLeading
from llamatron.engine.timing.timing import timed_events
from llamatron.math.rational import Rational
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import ClipSlotSetting, PatternSetting, Restart, Row, SceneSetting, Section, Shape, shape_setting, ShapePart
from llamatron.model.values.chord import Chord
from llamatron.model.values.note import Note, NoteName
from tests.engine.realizer import test_registers
from tests.engine.realizer.test_registers import pattern, song
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
    settings = {ChordsSetting.MODE: chords_model.PROGRESSION, ProgressionSetting.CHORDS: [1, 5, 6, 4]}
    return two_scenes(section=chords_plugin.SECTION, kind=chords_plugin.NAME, settings=settings, restart=restart, first_repeat=first_repeat)


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

    def test_a_swells_ramp_runs_over_the_whole_song(self):
        swell = {shape_setting(shape=Shape.SWELL, part=ShapePart.START): 0, shape_setting(shape=Shape.SWELL, part=ShapePart.END): 100}
        data = two_scenes(section=shapes_plugin.SECTION, kind=shapes_plugin.NAME, settings=swell, restart=Restart.WHOLE_SONG,
                          rows={Row.VELOCITY: [100] * STEPS})
        scenes = played(data)
        self.assertLess(scenes[0][-1].velocity, scenes[1][0].velocity)
        self.assertLess(scenes[1][-1].velocity, 100)


class TestStateKeepingGenerators(unittest.TestCase):

    def test_an_auto_ratchet_carries_its_count_on(self):
        settings = {'counts': [1, 2, 3]}
        fresh = played(two_scenes(section=auto_ratchet_plugin.SECTION, kind=auto_ratchet_plugin.NAME, settings=settings))
        carried = played(two_scenes(section=auto_ratchet_plugin.SECTION, kind=auto_ratchet_plugin.NAME, settings=settings, restart=Restart.WHOLE_SONG))
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
