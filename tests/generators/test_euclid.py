# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Euclidean mask: only the notes starting on a hit of a Euclidean rhythm play, a track's mask and Euclid generators stacking.

Each test plays a bar of sixteen sixteenth notes, so that every step of a 16-step rhythm has a note.
"""

import unittest

from llamatron.math.rational import Rational
from llamatron.model.file.song_file_error import SongFileError
from llamatron.model.objects import euclid
from llamatron.model.objects.euclid import rhythm
from llamatron.model.schema.file_format import ClipSlotSetting, euclid_setting, EuclidPart, GeneratorKind, NamedRhythm, PatternSetting, SceneSetting, Section
from tests.playback import test_registers
from tests.playback.test_registers import pattern, song
from tests.playback.test_shapes import notes
from tests.support.rendering import setlist_from_data

STEPS = 16
MASKED = 'masked'
MASKED_CHAIN = 'masked chain'
SIXTEENTH = Rational(1, 16)


def sixteenths(*, track=None, generator=None, step_size='1/16', repeat=1):
    """Return a song whose lead plays a bar of sixteenths, the track given a mask and the clip's chain naming a Euclid generator."""
    clip = {ClipSlotSetting.PATTERN: test_registers.X, ClipSlotSetting.REPEAT: repeat}
    if generator is not None:
        clip[ClipSlotSetting.CHAINS] = [MASKED_CHAIN]
    data = song(patterns={test_registers.X: dict(pattern(STEPS), **{PatternSetting.STEP_SIZE: step_size})}, scenes=[{SceneSetting.TRACKS: {test_registers.LEAD: clip}}])
    data[Section.TRACKS][test_registers.LEAD] = {euclid_setting(part): value for part, value in (track or {}).items()}
    if generator is not None:
        data[Section.EUCLIDS] = {MASKED: generator}
        data[Section.CHAINS] = {MASKED_CHAIN: [{GeneratorKind.EUCLID: MASKED}]}
    return data


def steps_played(data):
    return [int(start / SIXTEENTH) for start, _, _, _ in notes(data)]


def hits_of(*, hits, steps, rotate=0):
    return [place for place, hit in enumerate(rhythm(hits=hits, steps=steps, rotate=rotate)) if hit]


class TestRhythm(unittest.TestCase):

    def test_the_named_rhythms(self):
        hits = {name: hits_of(hits=count, steps=steps) for name, (count, steps) in euclid.NAMED_RHYTHMS.items()}
        self.assertEqual(hits[NamedRhythm.TRESILLO], [0, 3, 6])
        self.assertEqual(hits[NamedRhythm.CINQUILLO], [0, 2, 3, 5, 6])
        self.assertEqual(hits[NamedRhythm.BOSSA_NOVA], [0, 3, 6, 9, 12])

    def test_a_rotation_moves_it_later(self):
        self.assertEqual(hits_of(hits=3, steps=8, rotate=1), [1, 4, 7])

    def test_hits_spread_evenly_and_every_hit_counts(self):
        for hits in range(1, STEPS + 1):
            self.assertEqual(sum(rhythm(hits=hits, steps=STEPS)), hits)


class TestMask(unittest.TestCase):

    def test_no_mask_plays_every_step(self):
        self.assertEqual(steps_played(sixteenths()), list(range(STEPS)))

    def test_a_tracks_mask_keeps_the_notes_on_its_hits(self):
        self.assertEqual(steps_played(sixteenths(track={EuclidPart.HITS: 5, EuclidPart.STEPS: 16})), hits_of(hits=5, steps=16))

    def test_steps_default_to_a_bar_of_sixteenths(self):
        self.assertEqual(steps_played(sixteenths(track={EuclidPart.HITS: 5})), hits_of(hits=5, steps=16))

    def test_a_shorter_rhythm_repeats_and_runs_across_the_bar(self):
        self.assertEqual(steps_played(sixteenths(track={EuclidPart.HITS: 3, EuclidPart.STEPS: 8})), [0, 3, 6, 8, 11, 14])

    def test_a_step_of_its_own_spreads_the_rhythm_wider(self):
        self.assertEqual(steps_played(sixteenths(track={EuclidPart.HITS: 2, EuclidPart.STEPS: 4, EuclidPart.STEP: '1/8'})), [0, 1, 4, 5, 8, 9, 12, 13])

    def test_a_generator_masks_on_top_of_the_track(self):
        played = steps_played(sixteenths(track={EuclidPart.HITS: 5, EuclidPart.STEPS: 8}, generator={EuclidPart.HITS: 3, EuclidPart.STEPS: 8, EuclidPart.ROTATE: 1}))
        both = sorted(set(place for place in range(STEPS) if rhythm(hits=5, steps=8)[place % 8] and rhythm(hits=3, steps=8, rotate=1)[place % 8]))
        self.assertEqual(played, both)

    def test_a_masked_note_keeps_its_place(self):
        played = notes(sixteenths(track={EuclidPart.HITS: 1, EuclidPart.STEPS: 16}))
        self.assertEqual(len(played), 1)


class TestWhatAFileHolds(unittest.TestCase):

    def test_more_hits_than_steps_is_refused_on_a_generator(self):
        with self.assertRaises(SongFileError):
            setlist_from_data(sixteenths(generator={EuclidPart.HITS: 9, EuclidPart.STEPS: 8}))

    def test_hits_past_the_most_are_refused_on_a_track(self):
        with self.assertRaises(SongFileError):
            setlist_from_data(sixteenths(track={EuclidPart.HITS: 33}))
