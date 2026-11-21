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


"""A score made after an edit takes the scenes the edit cannot change from the score before it, and plays as a whole render does.

While the tests check every remembered answer, which tests/support/rendering.py turns on, every score that takes scenes is held
to a whole render of its song as it is made, and raises StaleAnswer where they differ; these tests make such scores, after
edits chosen by hand and after a run of edits chosen at random on demos that use the registers, the draws, drifts, hockets,
grabs, morphs and generators that carry on across scenes, each score made from the one before."""

import os
import random
import unittest

from llamatron.composition.file_format import Row, Section
from llamatron.composition.setlist import Setlist
from llamatron.music import midi
from llamatron.realtime.score import Score
from llamatron.realtime.timeline import Route
from llamatron.support.memory import Memory

PORT = 'test port'
CHANNELS = 16
SEED = 5
ANOTHER_SEED = 6
FUZZ_SEED = 2026
EDITS = 8
LOWEST_TEMPO = 70
HIGHEST_TEMPO = 170
HIGHEST_REPEAT = 3
# Every score that takes scenes is held to a whole render as it is made, as in every test that renders (tests/support/rendering.py).
Memory.check_every_answer()

EXAMPLES = os.path.join(os.path.dirname(__file__), '..', '..', 'examples')
# A demo whose last scene alone plays a pattern of its own, so that an edit to it leaves every scene before.
LATE_PATTERN_DEMO = os.path.join(EXAMPLES, 'learning', '30_draws.yml')
# A set whose every scene plays a brownian drift with random degrees, from the song's top, and a pattern of its own.
DRIFTING_SET = os.path.join(os.path.dirname(__file__), '..', 'data', 'sample_sets', 'scene_reuse_drift.yml')
# A demo whose registers can cut a clip short, so that a scene is played to find how long it lasts.
CUT_SHORT_DEMO = os.path.join(EXAMPLES, 'learning', '27_advanced_conditionals.yml')
# Demos that use what carries from scene to scene: registers, draws, drifts, a hocket, grabs, morphs and generators whose run reaches across scenes.
FUZZED_DEMOS = (
    os.path.join(EXAMPLES, 'learning', '18_techno_morph.yml'),
    os.path.join(EXAMPLES, 'learning', '19_hocket_shanty.yml'),
    os.path.join(EXAMPLES, 'learning', '20_arrangement_shanty.yml'),
    os.path.join(EXAMPLES, 'learning', '21_look_ma_no_notes.yml'),
    os.path.join(EXAMPLES, 'learning', '22_registers.yml'),
    os.path.join(EXAMPLES, 'learning', '30_draws.yml'),
    os.path.join(EXAMPLES, 'by_genre', 'electronic', 'edm_density.yml'),
    os.path.join(EXAMPLES, 'by_genre', 'rock', 'volcano.yml'),
)


class Edited:
    """A set read from a demo, which a test edits as the tracker would and makes scores of, each from a copy of its data as kept."""

    __slots__ = ('setlist', 'name', 'routes')

    def __init__(self, path):
        self.setlist = Setlist.read_file(path)
        self.name = self.setlist.first_song_name()
        self.routes = {track: Route(PORT, place % CHANNELS) for place, track in enumerate(self.song().get_track_names())}

    def song(self):
        return self.setlist.get_song(self.name)

    def score(self, *, earlier=None, seed=SEED, kept=True, routes=None):
        """Return a score of the song as it is now, made from a copy of the set as the transport makes one; kept, made with the set's data, so that a later score can take scenes from it."""
        data = self.setlist.kept_data()
        copied = Setlist.from_data(data=data).get_song(self.name)
        return Score(song=copied, routes=self.routes if routes is None else routes, seed=seed, data=data if kept else None, earlier=earlier)

    def last_pattern(self):
        """Return the name of the pattern whose first scene is the latest in the song."""
        scenes = self.song().get_scenes()
        names = [name for scene in scenes for track in scene.get_track_names() for name in scene.get_clip_slot(track).get_pattern_names()]
        return max(names, key=lambda name: _first_scene_naming(scenes=scenes, name=name))


def _first_scene_naming(*, scenes, name):
    return next(place for place, scene in enumerate(scenes) if scene.clip_slots_naming(section=Section.PATTERNS, name=name))


def reused(score):
    """Return how many written scenes a score took from the one before it."""
    return score.get_reused_scene_count()


class TestScoreTakesScenes(unittest.TestCase):

    def setUp(self):
        self.edited = Edited(LATE_PATTERN_DEMO)
        self.first = self.edited.score()

    def edit_last_pattern(self):
        self.edited.setlist.get_pattern(self.edited.last_pattern()).set_value(row=Row.VELOCITY, step=0, value=midi.MIN_VELOCITY)

    def test_an_edit_to_a_late_pattern_takes_the_scenes_before_and_plays_as_a_whole_render(self):
        self.edit_last_pattern()
        after = self.edited.score(earlier=self.first)
        self.assertEqual(reused(after), len(self.edited.song().get_scenes()) - 1)
        whole = self.edited.score(kept=False)
        for scene in range(after.scene_count()):
            for track in after.get_tracks():
                self.assertEqual(after.get_events(scene=scene, track=track), whole.get_events(scene=scene, track=track))

    def test_with_no_edit_every_scene_is_taken(self):
        self.assertEqual(reused(self.edited.score(earlier=self.first)), len(self.edited.song().get_scenes()))

    def test_a_score_made_without_the_sets_data_gives_nothing(self):
        self.edit_last_pattern()
        unkept = self.edited.score(kept=False)
        self.assertEqual(reused(self.edited.score(earlier=unkept)), 0)

    def test_another_seed_takes_nothing(self):
        self.edit_last_pattern()
        self.assertEqual(reused(self.edited.score(earlier=self.first, seed=ANOTHER_SEED)), 0)

    def test_no_seed_takes_nothing(self):
        first = self.edited.score(seed=None)
        self.assertEqual(reused(self.edited.score(earlier=first, seed=None)), 0)

    def test_other_routes_take_nothing(self):
        routes = {track: Route(PORT, (route.channel + 1) % CHANNELS) for track, route in self.edited.routes.items()}
        self.assertEqual(reused(self.edited.score(earlier=self.first, routes=routes)), 0)

    def test_a_scene_that_lasts_longer_takes_nothing_since_a_run_reaches_across_scenes_by_their_lengths(self):
        last = self.edited.song().get_scenes()[-1]
        last.set_repeat(last.get_repeat() + 1)
        self.assertEqual(reused(self.edited.score(earlier=self.first)), 0)

    def test_a_random_drift_goes_on_from_where_the_scenes_taken_left_it(self):
        edited = Edited(DRIFTING_SET)
        first = edited.score()
        edited.setlist.get_pattern(edited.last_pattern()).set_value(row=Row.VELOCITY, step=0, value=midi.MIN_VELOCITY)
        self.assertEqual(reused(edited.score(earlier=first)), len(edited.song().get_scenes()) - 1)

    def test_a_song_whose_registers_cut_a_clip_short_takes_nothing(self):
        edited = Edited(CUT_SHORT_DEMO)
        first = edited.score()
        edited.setlist.get_pattern(edited.last_pattern()).set_value(row=Row.VELOCITY, step=0, value=midi.MIN_VELOCITY)
        self.assertEqual(reused(edited.score(earlier=first)), 0)


class FuzzedDemo:
    """A run of edits chosen at random on a demo, each score made from the one before and held to a whole render as it is made."""

    __slots__ = ()

    PATH = None

    def test_a_run_of_edits_plays_as_whole_renders(self):
        edited = Edited(self.PATH)
        chooser = random.Random(FUZZ_SEED)
        score = edited.score()
        taken = 0
        for _ in range(EDITS):
            edit = chooser.choice((edit_a_step, edit_a_step, edit_a_scene_tempo, edit_a_scene_repeat))
            edit(edited=edited, chooser=chooser)
            score = edited.score(earlier=score)
            taken += reused(score)
        self.assertGreater(taken, 0)


def edit_a_step(*, edited, chooser):
    """Change the velocity of a step of a pattern the song plays."""
    song = edited.song()
    names = sorted({name for scene in song.get_scenes() for track in scene.get_track_names() for name in scene.get_clip_slot(track).get_pattern_names()})
    pattern = edited.setlist.get_pattern(chooser.choice(names))
    pattern.set_value(row=Row.VELOCITY, step=chooser.randrange(pattern.get_steps()), value=chooser.randint(midi.MIN_VELOCITY, midi.MAX_VELOCITY))


def edit_a_scene_tempo(*, edited, chooser):
    """Change the tempo of one of the song's scenes."""
    chooser.choice(edited.song().get_scenes()).set_tempo(chooser.randint(LOWEST_TEMPO, HIGHEST_TEMPO))


def edit_a_scene_repeat(*, edited, chooser):
    """Change how many times one of the song's scenes repeats."""
    chooser.choice(edited.song().get_scenes()).set_repeat(chooser.randint(1, HIGHEST_REPEAT))


def _fuzzed_class(path):
    name = 'TestFuzzed' + ''.join(part.capitalize() for part in os.path.splitext(os.path.basename(path))[0].split('_') if not part.isdigit())
    return type(name, (FuzzedDemo, unittest.TestCase), {'PATH': path, '__slots__': ()})


for _path in FUZZED_DEMOS:
    _fuzzed = _fuzzed_class(_path)
    globals()[_fuzzed.__name__] = _fuzzed


if __name__ == '__main__':
    unittest.main()
