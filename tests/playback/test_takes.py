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



"""A clip's take (SongRenderer's takes): a take after the first gives that clip new random choices and leaves every other clip's
as they were, and a render after an earlier one with another take keeps every scene before and every clip the take cannot
reach, playing as a whole render with the same takes plays."""

import unittest

from llamatron.composition.file_format import ClipSlotSetting, Row, SceneSetting, Section
from llamatron.playback.song_renderer import SongRenderer
from llamatron.support.memory import Memory
from tests.support import song_testing
from tests.support.rendering import setlist_from_data

LEAD = 'lead'
BASS = 'bass'
CHANCE = 'chance'
PLAIN = 'plain'
FIRST = 'one'
SECOND = 'two'
STEPS = 32
HALF_THE_TIME = 50
SEED = 1
SECOND_SCENE = 1
ANOTHER_TAKE = 1


def a_set():
    """Return a set of one song of two scenes: the lead plays a long pattern whose every step plays half the time, the bass a plain one."""
    steps = [[1 + place % 7, 1] for place in range(STEPS)]
    def scene(name):
        return {SceneSetting.NAME: name, Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERNS: [CHANCE]}, BASS: {ClipSlotSetting.PATTERNS: [PLAIN]}}}
    return setlist_from_data(song_testing.with_parts(
        patterns={CHANCE: song_testing.pat(*steps, **{Row.PROBABILITY: [HALF_THE_TIME] * STEPS}), PLAIN: song_testing.pat(*steps)},
        tracks={LEAD: {}, BASS: {}},
        scenes=[scene(FIRST), scene(SECOND)],
    ))


def sounds_by_clip(grid):
    """Return every clip's sounds, by (the scene's place, the track)."""
    return {(place, track.get_name()): tuple(grid.get_clip(row=row, column=track).get_sounds()) for place, row in enumerate(grid.get_rows()) for track in grid.get_columns()}


class TestTakes(unittest.TestCase):

    def setUp(self):
        checking = Memory.checks_by_default()
        Memory.check_every_answer(checks=True)
        self.addCleanup(Memory.check_every_answer, checks=checking)
        self.setlist = a_set()
        self.song = self.setlist.get_song(self.setlist.first_song_name())

    def render(self, *, takes=None, after=None):
        renderer = SongRenderer(self.song, seed=SEED, data=self.setlist.kept_data(), takes=takes)
        return renderer, renderer.render(after=after)

    def test_another_take_gives_that_clip_new_random_choices_and_leaves_every_other_clip_alone(self):
        _first, before = self.render()
        _again, after = self.render(takes={(SECOND_SCENE, LEAD): ANOTHER_TAKE})
        old = sounds_by_clip(before)
        new = sounds_by_clip(after)
        self.assertNotEqual(new.pop((SECOND_SCENE, LEAD)), old.pop((SECOND_SCENE, LEAD)))
        self.assertEqual(new, old)

    def test_take_zero_is_every_clips_take_unless_given(self):
        _first, plain = self.render()
        _again, zero = self.render(takes={(SECOND_SCENE, LEAD): 0})
        self.assertEqual(sounds_by_clip(zero), sounds_by_clip(plain))

    def test_a_render_after_another_take_keeps_what_the_take_cannot_reach_and_plays_as_a_whole_render(self):
        earlier, _grid = self.render()
        takes = {(SECOND_SCENE, LEAD): ANOTHER_TAKE}
        later, kept = self.render(takes=takes, after=earlier)
        self.assertEqual(later.get_reused_scene_count(), SECOND_SCENE)
        self.assertGreater(later.get_kept_clip_count(), 0)
        _whole, whole = self.render(takes=takes)
        self.assertEqual(sounds_by_clip(kept), sounds_by_clip(whole))


if __name__ == '__main__':
    unittest.main()
