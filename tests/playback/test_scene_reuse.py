# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later


"""Which scenes of a song an edit cannot change: the first scene that differs or names a changed pattern, and the first scene
when anything else changed (playback/scene_reuse.py). tests/realtime/test_scene_reuse.py holds the scores made from it to a
whole render."""

import unittest

from llamatron.composition.file_format import ClipSlotSetting, Row, SceneSetting, Section
from llamatron.composition.setlist import Setlist
from llamatron.playback import scene_reuse
from llamatron.playback.scene_reuse import first_changed_scene
from tests.support import song_testing

SONG = 'song'
# Three scenes: the first plays the pattern called opening, the second and third the pattern called later.
OPENING = 'opening'
LATER = 'later'
TRACK = 'lead'
FIRST = 'one'
SECOND = 'two'
THIRD = 'three'
CHANGED_VELOCITY = 33
CHANGED_TEMPO = 133
CHANGED_TITLE = 'another title'


def a_set():
    """Return a set of one song whose first scene plays opening and whose other two play later."""
    def scene(name, pattern):
        return {SceneSetting.NAME: name, Section.TRACKS: {TRACK: {ClipSlotSetting.PATTERNS: [pattern]}}}
    data = {
        Section.PATTERNS: {OPENING: song_testing.pat([1, 1], [2, 1], [3, 1], [4, 1]), LATER: song_testing.pat([5, 1], [4, 1], [3, 1], [2, 1])},
        Section.SONGS: {SONG: {Section.TRACKS: {TRACK: {}}, Section.SCENES: [scene(FIRST, OPENING), scene(SECOND, LATER), scene(THIRD, LATER)]}},
    }
    return Setlist.from_data(data=data)


def first_changed(*, setlist, before):
    """Return the place of the first scene of the song that may play differently now than when the set's data was before."""
    return first_changed_scene(before=before, after=setlist.kept_data(), song_name=SONG, scenes=setlist.get_song(SONG).get_scenes())


class TestFirstChangedScene(unittest.TestCase):

    def setUp(self):
        self.setlist = a_set()
        self.before = self.setlist.kept_data()

    def test_with_nothing_changed_no_scene_changed(self):
        self.assertEqual(first_changed(setlist=self.setlist, before=self.before), len(self.setlist.get_song(SONG).get_scenes()))

    def test_a_changed_pattern_changes_the_first_scene_that_plays_it(self):
        self.setlist.get_pattern(LATER).set_value(row=Row.VELOCITY, step=0, value=CHANGED_VELOCITY)
        self.assertEqual(first_changed(setlist=self.setlist, before=self.before), 1)

    def test_a_pattern_the_first_scene_plays_changes_everything(self):
        self.setlist.get_pattern(OPENING).set_value(row=Row.VELOCITY, step=0, value=CHANGED_VELOCITY)
        self.assertEqual(first_changed(setlist=self.setlist, before=self.before), scene_reuse.FIRST_SCENE)

    def test_a_changed_scene_is_the_first_changed(self):
        self.setlist.get_song(SONG).get_scenes()[2].set_tempo(CHANGED_TEMPO)
        self.assertEqual(first_changed(setlist=self.setlist, before=self.before), 2)

    def test_anything_of_the_song_but_its_scenes_changes_everything(self):
        self.setlist.get_song(SONG).set_tempo(CHANGED_TEMPO)
        self.assertEqual(first_changed(setlist=self.setlist, before=self.before), scene_reuse.FIRST_SCENE)

    def test_anything_of_the_set_but_its_patterns_changes_everything(self):
        self.setlist.set_title(CHANGED_TITLE)
        self.assertEqual(first_changed(setlist=self.setlist, before=self.before), scene_reuse.FIRST_SCENE)

    def test_a_scene_taken_away_at_the_end_leaves_the_scenes_before_it(self):
        song = self.setlist.get_song(SONG)
        song.remove_scene(2)
        self.assertEqual(first_changed(setlist=self.setlist, before=self.before), 2)


if __name__ == '__main__':
    unittest.main()
