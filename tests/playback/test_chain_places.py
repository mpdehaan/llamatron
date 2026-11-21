# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Chains on clips, scenes and tracks: a clip runs its own chains, then its scene's, then its track's, each list in its order, a chain named twice running twice."""

import unittest

from llamatron.engine.generators import auto_ratchet as auto_ratchet_plugin
from llamatron.engine.generators.auto_ratchet.model import AutoRatchetSetting
from llamatron.model.schema.file_format import ClipSlotSetting, SceneSetting, Section, TrackSetting
from llamatron.playback.song_renderer import SongRenderer
from tests.playback import test_registers
from tests.playback.test_registers import pattern, pitches, song
from tests.support.rendering import song_from_data

TWICE = 'twice'
OTHER_CHAIN = 'other'
CHOP = 'chop'
# A clip of one quarter note, which an AutoRatchet of 2 chops into two, and two of them into four.
ONE_NOTE = 1
# A new name for the AutoRatchet that chops.
RENAMED_CHOP = 'chop renamed'
CHOPPED_ONCE = 2
CHOPPED_TWICE = 4


def chained(*, clip_chains=None, scene_chains=None, track_chains=None):
    """Return a song whose lead plays one note, with a chain that chops each note in two, named wherever the test says."""
    clip = {ClipSlotSetting.PATTERN: test_registers.X}
    if clip_chains:
        clip[ClipSlotSetting.CHAINS] = clip_chains
    scene = {SceneSetting.TRACKS: {test_registers.LEAD: clip}}
    if scene_chains:
        scene[SceneSetting.CHAINS] = scene_chains
    data = song(patterns={test_registers.X: pattern(1)}, scenes=[scene])
    data[auto_ratchet_plugin.SECTION] = {CHOP: {AutoRatchetSetting.COUNTS: [2]}}
    data[Section.CHAINS] = {TWICE: [{auto_ratchet_plugin.NAME: CHOP}], OTHER_CHAIN: []}
    if track_chains:
        data[Section.TRACKS][test_registers.LEAD] = {TrackSetting.CHAINS: track_chains}
    return data


class TestChainPlaces(unittest.TestCase):

    def test_a_generator_listed_on_its_own_runs_as_a_chain_of_it_alone(self):
        self.assertEqual(len(pitches(chained(clip_chains=[CHOP]))), CHOPPED_ONCE)
        self.assertEqual(len(pitches(chained(scene_chains=[CHOP], track_chains=[TWICE]))), CHOPPED_TWICE)
        self.assertEqual(pitches(chained(clip_chains=[CHOP])), pitches(chained(clip_chains=[TWICE])))

    def test_a_generator_listed_on_its_own_follows_its_rename_and_counts_as_used(self):
        built = song_from_data(chained(clip_chains=[CHOP], scene_chains=[CHOP]))
        setlist = built.get_setlist()
        self.assertIn(auto_ratchet_plugin.SECTION, [section for section, name in setlist.everything_named() if name == CHOP])
        setlist.rename_item(section=auto_ratchet_plugin.SECTION, old=CHOP, new=RENAMED_CHOP)
        scene = built.get_scenes()[0]
        self.assertEqual((scene.get_clip_slot(test_registers.LEAD).get_chain_names(), scene.get_chain_names()), ([RENAMED_CHOP], [RENAMED_CHOP]))
        self.assertEqual([(step.kind, step.name) for step in setlist.get_chain(TWICE).get_steps()], [(auto_ratchet_plugin.NAME, RENAMED_CHOP)])

    def test_a_scenes_chain_and_a_tracks_chain_each_run_on_a_clip_with_none_of_its_own(self):
        self.assertEqual(len(pitches(chained())), ONE_NOTE)
        self.assertEqual(len(pitches(chained(scene_chains=[TWICE]))), CHOPPED_ONCE)
        self.assertEqual(len(pitches(chained(track_chains=[TWICE]))), CHOPPED_ONCE)

    def test_a_chain_named_in_two_places_runs_twice(self):
        self.assertEqual(len(pitches(chained(clip_chains=[TWICE], track_chains=[TWICE]))), CHOPPED_TWICE)
        self.assertEqual(len(pitches(chained(clip_chains=[TWICE, TWICE]))), CHOPPED_TWICE)

    def test_the_clips_chains_run_first_then_the_scenes_then_the_tracks(self):
        data = chained(clip_chains=[OTHER_CHAIN], scene_chains=[TWICE], track_chains=[OTHER_CHAIN, TWICE])
        renderer = SongRenderer(song_from_data(data))
        scene = renderer.get_scenes()[0]
        self.assertEqual(renderer.chains_of(scene=scene, track=test_registers.LEAD), [OTHER_CHAIN, TWICE, OTHER_CHAIN, TWICE])

    def test_deleting_a_generator_takes_it_out_of_every_chain_and_every_list(self):
        built = song_from_data(chained(clip_chains=[CHOP, TWICE], scene_chains=[CHOP], track_chains=[CHOP]))
        built.get_setlist().delete_generator(section=auto_ratchet_plugin.SECTION, name=CHOP)
        scene = built.get_scenes()[0]
        self.assertEqual(built.get_setlist().get_chain(TWICE).get_steps(), [])
        self.assertEqual((scene.get_clip_slot(test_registers.LEAD).get_chain_names(), scene.get_chain_names(), built.get_track(test_registers.LEAD).get_chain_names()), ([TWICE], [], []))

    def test_renaming_a_chain_renames_it_in_every_list(self):
        renamed = 'renamed'
        data = chained(clip_chains=[TWICE], scene_chains=[TWICE], track_chains=[OTHER_CHAIN, TWICE])
        built = song_from_data(data)
        built.get_setlist().rename_item(section=Section.CHAINS, old=TWICE, new=renamed)
        scene = built.get_scenes()[0]
        self.assertEqual(scene.get_clip_slot(test_registers.LEAD).get_chain_names(), [renamed])
        self.assertEqual(scene.get_chain_names(), [renamed])
        self.assertEqual(built.get_track(test_registers.LEAD).get_chain_names(), [OTHER_CHAIN, renamed])


if __name__ == '__main__':
    unittest.main()
