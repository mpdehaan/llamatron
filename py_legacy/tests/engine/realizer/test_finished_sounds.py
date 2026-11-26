# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The sounds a clip finishes with: a looping clip cut where its scene ends, without cutting again one already that long, and
any other clip whole."""

from fractions import Fraction
import unittest

from llamatron.engine.clips.clip import Clip
from llamatron.engine.realizer.clip_slot_player import finished_sounds
from llamatron.model.values.note import Note, NoteName

QUARTER = Fraction(1, 4)
HALF = Fraction(1, 2)
NOTHING = 0
OCTAVE = 4


def bar_of_quarters():
    """Return a clip of a bar of four quarter notes, C to F."""
    return Clip(notes=[Note(name=name, octave_number=OCTAVE, length=QUARTER) for name in (NoteName.C, NoteName.D, NoteName.E, NoteName.F)])


def length_of(sounds):
    return Clip(sounds=sounds).total_length()


class TestFinishedSounds(unittest.TestCase):

    def test_a_looping_clip_as_long_as_its_scene_is_not_cut_again_and_plays_what_a_cut_would(self):
        clip = bar_of_quarters()
        whole = clip.total_length()
        self.assertEqual(finished_sounds(clip=clip, loop=True, fill=whole), clip.section(start=NOTHING, end=whole).get_sounds())

    def test_a_looping_clip_longer_than_its_scene_is_cut_where_the_scene_ends(self):
        clip = bar_of_quarters()
        cut = finished_sounds(clip=clip, loop=True, fill=HALF)
        self.assertEqual(cut, clip.section(start=NOTHING, end=HALF).get_sounds())
        self.assertEqual(length_of(cut), HALF)

    def test_a_looping_clip_in_a_scene_of_no_length_plays_nothing(self):
        self.assertEqual(finished_sounds(clip=bar_of_quarters(), loop=True, fill=NOTHING), [])

    def test_a_clip_that_does_not_loop_plays_the_whole_of_what_it_played(self):
        clip = bar_of_quarters()
        self.assertEqual(finished_sounds(clip=clip, loop=False, fill=HALF), clip.played_sounds())
