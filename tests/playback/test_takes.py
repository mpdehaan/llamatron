# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later



"""A clip's take (SongRenderer's takes): a take after the first gives that clip new random choices and leaves every other clip's
as they were, a render after an earlier one with another take keeps every scene before and every clip the take cannot reach,
playing as a whole render with the same takes plays, and a draw of any value or of each value once draws anew on every repeat
and every take of a scene."""

import unittest

from llamatron.caching.memory import Memory
from llamatron.model.vocabulary.file_format import ClipSlotSetting, DrawDirection, DrawName, Row, SceneSetting, Section
from llamatron.playback.song_renderer import SongRenderer
from tests.playback import test_draws
from tests.support import song_testing
from tests.support.rendering import setlist_from_data, song_from_data

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
FIRST_SCENE = 0
REPEATS = 4
# The draws that choose by chance, which must draw anew on every repeat and take of a scene.
DRAWING_AFRESH = (DrawDirection.ANY, DrawDirection.SERIAL)


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


class TestDrawsOnEveryTake(unittest.TestCase):
    """A draw that takes any value, or each value once a round, draws anew on every repeat of a scene and on every take of it, so
    that a scene repeated, launched again or looping never plays one draw's values over and over."""

    def draws_heard(self, *, direction, takes=None, repeat=1):
        """Return the values a draw of twelve tones gave the lead's steps, a list a repeat of the scene."""
        song = song_from_data(test_draws.song_data(draws={DrawName.AD: test_draws.a_draw(slots=test_draws.TWELVE_TONES, direction=direction)}, rows={Row.AD_NOTE: test_draws.every_step()}, repeat=repeat))
        grid = SongRenderer(song, seed=SEED, takes=takes).render()
        return [[pitch - test_draws.MIDDLE_C for pitch in pitches] for pitches in test_draws.pitches_of(song=grid, scenes=len(grid.get_rows()))]

    def test_every_repeat_of_a_scene_draws_anew(self):
        for direction in DRAWING_AFRESH:
            with self.subTest(direction=direction):
                repeats = self.draws_heard(direction=direction, repeat=REPEATS)
                self.assertEqual(len({tuple(values) for values in repeats}), REPEATS)

    def test_every_take_of_a_scene_draws_anew(self):
        for direction in DRAWING_AFRESH:
            with self.subTest(direction=direction):
                takes = [self.draws_heard(direction=direction, takes={(FIRST_SCENE, test_draws.LEAD): take}) for take in range(REPEATS)]
                self.assertEqual(len({tuple(values[0]) for values in takes}), REPEATS)
