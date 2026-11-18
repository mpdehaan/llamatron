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

"""The step in loudness from one section to the next, and each player's trade of loudness for a much denser part."""

import unittest

from llamatron.composition.file_format import Shape
from llamatron.macro_composer import loudness_steps
from llamatron.macro_composer.breaks import HAT, OPEN, RIDE
from llamatron.macro_composer.loudness_steps import AS_DENSE, FEWEST_NOTES_A_BAR, LARGEST_STEP, LEAST_KEPT, MUCH_DENSER, TIMEKEEPER
from llamatron.macro_composer.song_plan import CHORUS
from llamatron.macro_composer.wizard_choices import WizardChoices
from llamatron.support.version import VERSION

A_NAME = 'a_song'
A_SEED = 11
ROCK = 'rock'
ARENA_ROCK = 'arena rock'
A_GUITAR = 'guitar'
A_BASS = 'bass'
A_SINGER = 'singer'
SOME_NOTES = 8
SOME_LOUDNESS = 600
WHOLE = 1
TWICE = 2
FAR_DENSER = 10
NOT_TRADED = 1
A_LITTLE = 0.01


def part(*, notes=SOME_NOTES, loudness=SOME_LOUDNESS):
    return (notes, loudness)


def played(*, notes=SOME_NOTES, loudness=SOME_LOUDNESS, kept=NOT_TRADED):
    return (notes, loudness, kept)


def arena_rock():
    choices = WizardChoices()
    choices.set_genre(ROCK)
    choices.set_subgenre(ARENA_ROCK)
    choices.set_seed(A_SEED)
    return choices


def first_chorus(song):
    return [scene.get_section() for scene in song.get_scenes()].index(CHORUS)


def chorus_step(setlist):
    song = setlist.get_song(A_NAME)
    scenes = loudness_steps.measured(song=song)
    place = first_chorus(song)
    return loudness_steps.step(before=scenes[place - 1], now=scenes[place])


class TestATrade(unittest.TestCase):

    def test_a_part_twice_as_dense_and_twice_as_loud_keeps_what_makes_the_largest_step(self):
        kept = loudness_steps.trade_of(before=played(), now=part(notes=SOME_NOTES * TWICE, loudness=SOME_LOUDNESS * TWICE))
        self.assertAlmostEqual(kept, max(LEAST_KEPT, LARGEST_STEP / TWICE))
        self.assertLess(kept, WHOLE)

    def test_a_note_never_keeps_less_than_the_least(self):
        kept = loudness_steps.trade_of(before=played(), now=part(notes=SOME_NOTES * FAR_DENSER, loudness=SOME_LOUDNESS * FAR_DENSER))
        self.assertEqual(kept, LEAST_KEPT)

    def test_a_denser_part_that_adds_up_to_no_more_is_played_whole(self):
        self.assertEqual(loudness_steps.trade_of(before=played(), now=part(notes=SOME_NOTES * TWICE, loudness=SOME_LOUDNESS)), WHOLE)

    def test_a_part_a_little_denser_is_played_as_the_part_before(self):
        a_little_denser = SOME_NOTES * MUCH_DENSER
        self.assertEqual(loudness_steps.trade_of(before=played(), now=part(notes=a_little_denser, loudness=SOME_LOUDNESS * TWICE)), WHOLE)
        self.assertEqual(loudness_steps.trade_of(before=played(kept=LEAST_KEPT), now=part(notes=a_little_denser)), LEAST_KEPT)

    def test_a_part_as_dense_keeps_the_trade_before_and_a_thinner_part_is_played_whole(self):
        as_dense = SOME_NOTES * AS_DENSE
        self.assertEqual(loudness_steps.trade_of(before=played(kept=LEAST_KEPT), now=part(notes=as_dense)), LEAST_KEPT)
        self.assertEqual(loudness_steps.trade_of(before=played(kept=LEAST_KEPT), now=part(notes=as_dense - A_LITTLE)), WHOLE)


class TestTheTradesOfASong(unittest.TestCase):

    def thin_then_dense(self, player):
        return [{player: part()}, {player: part(notes=SOME_NOTES * TWICE, loudness=SOME_LOUDNESS * TWICE)}]

    def test_a_player_whose_part_grows_much_denser_trades_and_goes_on_trading_while_as_dense(self):
        scenes = self.thin_then_dense(A_GUITAR)
        traded = loudness_steps.trades(scenes=[*scenes, scenes[-1]])
        self.assertEqual(traded[0], {})
        self.assertLess(traded[1][A_GUITAR], WHOLE)
        self.assertEqual(traded[2], traded[1])

    def test_a_player_who_comes_in_is_left_alone(self):
        scenes = [{A_BASS: part()}, {A_BASS: part(), A_GUITAR: part(notes=SOME_NOTES * FAR_DENSER, loudness=SOME_LOUDNESS * FAR_DENSER)}]
        self.assertEqual(loudness_steps.trades(scenes=scenes), [{}, {}])

    def test_a_player_who_carries_a_melody_never_trades(self):
        self.assertEqual(loudness_steps.trades(scenes=self.thin_then_dense(A_SINGER), kept={A_SINGER}), [{}, {}])

    def test_a_part_of_a_note_now_and_then_is_no_part_to_trade_or_to_trade_against(self):
        a_fill = part(notes=FEWEST_NOTES_A_BAR - A_LITTLE, loudness=SOME_LOUDNESS)
        scenes = [{A_GUITAR: a_fill}, {A_GUITAR: part(notes=SOME_NOTES * FAR_DENSER, loudness=SOME_LOUDNESS * FAR_DENSER)}]
        self.assertEqual(loudness_steps.trades(scenes=scenes), [{}, {}])

    def test_a_part_is_held_against_the_part_before_as_traded(self):
        scenes = [{A_GUITAR: part()}, {A_GUITAR: part(notes=SOME_NOTES * TWICE, loudness=SOME_LOUDNESS * TWICE)},
                  {A_GUITAR: part(notes=SOME_NOTES * TWICE * TWICE, loudness=SOME_LOUDNESS * TWICE * TWICE)}]
        first, second = loudness_steps.trades(scenes=scenes)[1:]
        self.assertAlmostEqual(second[A_GUITAR], max(LEAST_KEPT, LARGEST_STEP * first[A_GUITAR] / TWICE))

    def test_the_timekeeping_cymbals_are_one_player(self):
        for cymbal in (HAT, OPEN, RIDE):
            self.assertEqual(loudness_steps.player_of(cymbal), TIMEKEEPER)
        self.assertEqual(loudness_steps.player_of(A_BASS), A_BASS)


class TestTheWizardsSong(unittest.TestCase):
    """The song the wizard makes holds the trades, and the song as written holds none."""

    def clips_with_a_swell(self, setlist):
        song = setlist.get_song(A_NAME)
        return [(scene.get_name(), track) for scene in song.get_scenes() for track in scene.get_track_names() if scene.get_clip_slot(track).get_shape(Shape.SWELL) is not None]

    def test_the_song_as_written_holds_no_trade_and_the_song_made_does(self):
        choices = arena_rock()
        self.assertEqual(self.clips_with_a_swell(choices.written_setlist(name=A_NAME, version=VERSION)), [])
        self.assertTrue(self.clips_with_a_swell(choices.made_setlist(name=A_NAME, version=VERSION)))

    def test_the_step_into_the_chorus_is_smaller_in_the_song_made(self):
        choices = arena_rock()
        written = chorus_step(choices.written_setlist(name=A_NAME, version=VERSION))
        made = chorus_step(choices.made_setlist(name=A_NAME, version=VERSION))
        self.assertGreater(written, LARGEST_STEP)
        self.assertLess(made, written)

    def test_a_traded_clip_plays_at_its_scenes_loudness_lowered_and_no_melody_trades(self):
        choices = arena_rock()
        setlist = choices.made_setlist(name=A_NAME, version=VERSION)
        song = setlist.get_song(A_NAME)
        melodies = choices.melody_players()
        for scene_name, track in self.clips_with_a_swell(setlist):
            scene = [scene for scene in song.get_scenes() if scene.get_name() == scene_name][0]
            own = scene.get_clip_slot(track).get_shape(Shape.SWELL)
            self.assertNotIn(track, melodies)
            self.assertLess(own.end, scene.get_shape(Shape.SWELL).end)
            self.assertGreaterEqual(own.end, round(scene.get_shape(Shape.SWELL).end * LEAST_KEPT))

    def test_the_same_choices_make_the_same_trades(self):
        choices = arena_rock()
        self.assertEqual(choices.made_setlist(name=A_NAME, version=VERSION).to_data(), WizardChoices.from_data(choices.to_data()).made_setlist(name=A_NAME, version=VERSION).to_data())


if __name__ == '__main__':
    unittest.main()
