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
"""Chains on clips, scenes and tracks: a clip runs its own chains, then its scene's, then its track's, each list in its order, a chain named twice running twice."""

import unittest

from llamatron.composition.file_format import ClipSlotSetting, GeneratorKind, SceneSetting, Section, TrackSetting
from llamatron.composition.generator_settings import AutoRatchetSetting
from llamatron.playback.song_renderer import SongRenderer
from tests.playback import test_registers
from tests.playback.test_registers import pattern, pitches, song
from tests.support.rendering import song_from_data

TWICE = 'twice'
OTHER_CHAIN = 'other'
CHOP = 'chop'
# A clip of one quarter note, which an AutoRatchet of 2 chops into two, and two of them into four.
ONE_NOTE = 1
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
    data[Section.AUTO_RATCHETS] = {CHOP: {AutoRatchetSetting.COUNTS: [2]}}
    data[Section.CHAINS] = {TWICE: [{GeneratorKind.AUTO_RATCHET: CHOP}], OTHER_CHAIN: []}
    if track_chains:
        data[Section.TRACKS][test_registers.LEAD] = {TrackSetting.CHAINS: track_chains}
    return data


class TestChainPlaces(unittest.TestCase):

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
