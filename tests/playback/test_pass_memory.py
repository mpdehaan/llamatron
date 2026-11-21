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



"""The passes a render remembers (playback/pass_memory.py): a pass of a plain pattern remembered once however often and wherever it
plays, a pattern that plays by chance never remembered, a copy handed out each time, the memory handed on to the next render of the
song across an edit, and a remembered pass that differs from the pass worked out again failing as a stale answer."""

import unittest

from llamatron.composition.file_format import ClipSlotSetting, Row, SceneSetting, Section
from llamatron.grid.clip import Clip
from llamatron.music.sound import Sound
from llamatron.playback.pass_memory import PassMemory
from llamatron.playback.pattern_player import Pass
from llamatron.playback.song_renderer import SongRenderer
from llamatron.support.length import Length
from llamatron.support.memory import Memory, StaleAnswer
from llamatron.support.rational import Rational
from tests.support import song_testing
from tests.support.rendering import setlist_from_data

LEAD = 'lead'
BASS = 'bass'
# A plain pattern, one that plays by chance, and one an edit changes.
TUNE = 'tune'
CHANCE = 'chance'
EDITED = 'edited'
FIRST = 'one'
SECOND = 'two'
REPEATS = 4
HALF_THE_TIME = 50
EDITED_DEGREE = 5
# Where a key holds its pattern's name and its revision.
NAME = 1
REVISION = 2
KEY = 'key'
QUARTER = Rational(1, 4)
NOTHING_TIED = Rational(0)


def a_set():
    """Return a set of one song: both tracks play tune in both scenes, the lead four times over in the first; the second scene adds
    chance on the bass's place and edited on the lead's."""
    def slot(*patterns, repeat=1):
        return {ClipSlotSetting.PATTERNS: list(patterns), ClipSlotSetting.REPEAT: repeat}
    steps = ([1, 1], [3, 1], [5, 1], [3, 1])
    return setlist_from_data(song_testing.with_parts(
        patterns={TUNE: song_testing.pat(*steps), CHANCE: song_testing.pat(*steps, **{Row.PROBABILITY: [HALF_THE_TIME] * len(steps)}), EDITED: song_testing.pat(*steps)},
        tracks={LEAD: {}, BASS: {}},
        scenes=[
            {SceneSetting.NAME: FIRST, Section.TRACKS: {LEAD: slot(TUNE, repeat=REPEATS), BASS: slot(TUNE)}},
            {SceneSetting.NAME: SECOND, Section.TRACKS: {LEAD: slot(TUNE, EDITED), BASS: slot(CHANCE, TUNE)}},
        ],
    ))


def names_kept(renderer):
    """Return the name of the pattern of each pass a render's memory keeps."""
    return [key[NAME] for key in renderer.get_passes().get_kept()]


def a_pass():
    """Return a pass of a quarter note's rest, a made-up one for the memory alone."""
    return Pass(clip=Clip(sounds=[Sound.rest(Length.of(QUARTER))], scale=None), tied_from_before=NOTHING_TIED, length=QUARTER)


class CheckingTest(unittest.TestCase):
    """Every memory made in these tests checks its answers, as the suite's do."""

    def setUp(self):
        checking = Memory.checks_by_default()
        Memory.check_every_answer(checks=True)
        self.addCleanup(Memory.check_every_answer, checks=checking)


class TestRenderRemembersPasses(CheckingTest):

    def setUp(self):
        super().setUp()
        self.setlist = a_set()
        self.song = self.setlist.get_song(self.setlist.first_song_name())
        self.renderer = SongRenderer(self.song, seed=1)
        self.renderer.render()

    def test_a_plain_pattern_is_remembered_once_however_often_and_wherever_it_plays(self):
        self.assertEqual(names_kept(self.renderer).count(TUNE), 1)

    def test_a_pattern_that_plays_by_chance_is_never_remembered(self):
        self.assertNotIn(CHANCE, names_kept(self.renderer))

    def test_the_next_render_goes_on_with_the_memory_and_an_edited_pattern_is_kept_again_under_its_new_revision(self):
        before = [key for key in self.renderer.get_passes().get_kept() if key[NAME] == EDITED]
        self.setlist.get_pattern(EDITED).set_value(row=Row.DEGREE, step=0, value=EDITED_DEGREE)
        after = SongRenderer(self.song, seed=1)
        after.render(after=self.renderer)
        self.assertIs(after.get_passes().get_kept(), self.renderer.get_passes().get_kept())
        edited = [key for key in after.get_passes().get_kept() if key[NAME] == EDITED]
        self.assertEqual(len(edited), len(before) + 1)
        self.assertNotEqual(edited[-1][REVISION], before[0][REVISION])


class TestPassMemory(CheckingTest):

    def test_a_pass_recalled_is_a_copy_whose_changes_the_memory_does_not_keep(self):
        memory = PassMemory()
        memory.keep(key=KEY, played=a_pass(), remembered=None)
        recalled = memory.recall(KEY)
        recalled.length = QUARTER * 2
        self.assertEqual(memory.recall(KEY).length, QUARTER)

    def test_a_key_never_kept_recalls_nothing(self):
        self.assertIsNone(PassMemory().recall(KEY))

    def test_a_memory_made_from_the_one_before_recalls_what_that_kept(self):
        earlier = PassMemory()
        earlier.keep(key=KEY, played=a_pass(), remembered=None)
        self.assertEqual(PassMemory(earlier=earlier).recall(KEY).length, QUARTER)

    def test_a_remembered_pass_unlike_the_pass_worked_out_again_is_a_stale_answer(self):
        memory = PassMemory()
        self.assertTrue(memory.is_checking())
        with self.assertRaises(StaleAnswer):
            memory.keep(key=KEY, played=a_pass(), remembered=Pass(clip=Clip(sounds=[], scale=None), tied_from_before=NOTHING_TIED, length=QUARTER * 2))


if __name__ == '__main__':
    unittest.main()
