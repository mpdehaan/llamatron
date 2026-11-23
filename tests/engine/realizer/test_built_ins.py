# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The built-in generators every clip and track holds: one of each kind a plugin builds in, switched off until switched on, a
clip's standing in for its track's, the ones before the lists running before them and the others after.

The songs are those of test_bypass_when: the lead plays one note, and a Chords generator moving every note to chord
II puts it one scale note higher, so a note a step higher is one a Chords generator ran on, and two steps higher one two ran on.
"""

import unittest

from llamatron.engine.generators import chords as chords_plugin, timing as timing_plugin
from llamatron.engine.generators.chords import model as chords_model
from llamatron.engine.generators.chords.model import ChordsSetting, ProgressionSetting
from llamatron.engine.realizer import chain_runs as chain_runs_values
from llamatron.engine.realizer.chain_runs import chain_runs
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.file.song_file_error import SongFileError
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import ClipSlotSetting, Section, TrackSetting
from tests.engine.realizer import test_bypass_when
from tests.engine.realizer.test_bypass_when import heard, notes_at, song
from tests.support.rendering import setlist_from_data

ON = {file_format.GENERATOR_ENABLED: True}
TO_CHORD_II = {ChordsSetting.MODE: chords_model.PROGRESSION, ProgressionSetting.CHORDS: [test_bypass_when.CHORD_II]}
CHORDS_ON = {chords_plugin.NAME: {**ON, **TO_CHORD_II}}
CHORDS_OFF = {chords_plugin.NAME: TO_CHORD_II}
UNMOVED = [0]
MOVED_ONCE = [test_bypass_when.MOVED_BY]
MOVED_TWICE = [test_bypass_when.MOVED_BY * 2]
RENAMED = 'melody'


def lead_of(data):
    """Return the lead track of a song's data, as the set reads it."""
    setlist = setlist_from_data(data)
    song_read = setlist.get_song(setlist.first_song_name())
    return song_read, song_read.get_track(test_bypass_when.LEAD)


class TestBuiltInsPlay(unittest.TestCase):

    def test_a_clips_built_in_plays_only_once_switched_on(self):
        self.assertEqual(heard(song(clip={ClipSlotSetting.BUILT_IN: CHORDS_OFF})), notes_at(UNMOVED))
        self.assertEqual(heard(song(clip={ClipSlotSetting.BUILT_IN: CHORDS_ON})), notes_at(MOVED_ONCE))

    def test_a_tracks_built_in_plays_on_its_clips(self):
        self.assertEqual(heard(song(track={TrackSetting.BUILT_IN: CHORDS_ON})), notes_at(MOVED_ONCE))

    def test_a_clips_built_in_switched_on_stands_in_for_its_tracks_of_the_same_kind(self):
        both = song(clip={ClipSlotSetting.BUILT_IN: CHORDS_ON}, track={TrackSetting.BUILT_IN: CHORDS_ON})
        self.assertEqual(heard(both), notes_at(MOVED_ONCE))
        clip_off = song(clip={ClipSlotSetting.BUILT_IN: CHORDS_OFF}, track={TrackSetting.BUILT_IN: CHORDS_ON})
        self.assertEqual(heard(clip_off), notes_at(MOVED_ONCE))

    def test_a_built_in_plays_beside_the_lists(self):
        self.assertEqual(heard(song(chained=True, clip={ClipSlotSetting.BUILT_IN: CHORDS_ON})), notes_at(MOVED_TWICE))

    def test_every_built_in_runs_in_its_place_and_the_lists_run_after_them_all(self):
        built_ins = {chords_plugin.NAME: ON, timing_plugin.NAME: ON}
        setlist = setlist_from_data(song(chained=True, clip={ClipSlotSetting.BUILT_IN: built_ins}))
        song_read = setlist.get_song(setlist.first_song_name())
        scene = song_read.get_scenes()[0]
        runs = chain_runs(setlist=setlist, clip_slot=scene.get_clip_slot(test_bypass_when.LEAD), scene=scene, track=song_read.get_track(test_bypass_when.LEAD))
        kinds = [step.kind for run in runs for step in run.chain.get_steps()]
        self.assertEqual(kinds, [chords_plugin.NAME, timing_plugin.NAME, chords_plugin.NAME])
        self.assertEqual([run.name for run in runs], [chain_runs_values.BUILT_IN_NAME, chain_runs_values.BUILT_IN_NAME, test_bypass_when.DOUBLED])


class TestBuiltInsAsStored(unittest.TestCase):

    def test_switching_on_writes_only_what_is_set_and_off_again_writes_nothing(self):
        song_read, lead = lead_of(song())
        self.assertEqual(lead.built_ins_on(), [])
        self.assertFalse(lead.get_built_in(chords_plugin.NAME).is_enabled())
        lead.set_built_in_setting(kind=chords_plugin.NAME, name=file_format.GENERATOR_ENABLED, value=True)
        self.assertEqual(lead.to_data()[TrackSetting.BUILT_IN], {chords_plugin.NAME: ON})
        self.assertEqual(lead.built_ins_on(), [chords_plugin.NAME])
        lead.set_built_in_setting(kind=chords_plugin.NAME, name=file_format.GENERATOR_ENABLED, value=None)
        self.assertNotIn(TrackSetting.BUILT_IN, lead.to_data())

    def test_a_change_through_the_built_ins_own_setters_is_kept_by_its_holder(self):
        song_read, lead = lead_of(song())
        revision = lead.get_revision()
        settings = lead.get_built_in(chords_plugin.NAME)
        settings.set_written(name=file_format.GENERATOR_ENABLED, value=True)
        settings.set_written(name=ChordsSetting.MODE, value=chords_model.PROGRESSION)
        self.assertEqual(lead.to_data()[TrackSetting.BUILT_IN], {chords_plugin.NAME: {**ON, ChordsSetting.MODE: chords_model.PROGRESSION}})
        self.assertNotEqual(lead.get_revision(), revision)
        settings.copy().set_written(name=ChordsSetting.MODE, value=None)
        self.assertEqual(lead.get_built_in(chords_plugin.NAME).get_written(ChordsSetting.MODE), chords_model.PROGRESSION)

    def test_a_setting_is_checked_as_the_sets_list_checks_it(self):
        song_read, lead = lead_of(song())
        with self.assertRaises(InvalidValue):
            lead.set_built_in_setting(kind=chords_plugin.NAME, name=ChordsSetting.MODE, value=RENAMED)
        self.assertNotIn(TrackSetting.BUILT_IN, lead.to_data())

    def test_a_file_naming_no_built_in_kind_is_refused_and_an_unknown_setting_passed_over(self):
        with self.assertRaises(SongFileError):
            setlist_from_data(song(track={TrackSetting.BUILT_IN: {Section.CHAINS: ON}}))
        song_read, lead = lead_of(song(track={TrackSetting.BUILT_IN: {chords_plugin.NAME: {**ON, RENAMED: test_bypass_when.CHORD_II}}}))
        self.assertEqual(lead.to_data()[TrackSetting.BUILT_IN], {chords_plugin.NAME: ON})

    def test_renaming_a_track_a_built_in_follows_renames_it_there(self):
        following = {chords_plugin.NAME: {ChordsSetting.MODE: chords_model.FOLLOW_PROGRESSION, ChordsSetting.CHORDS_FROM: test_bypass_when.LEAD}}
        song_read, lead = lead_of(song(other={ClipSlotSetting.BUILT_IN: following}))
        other = song_read.get_scenes()[0].get_clip_slot(song_read.get_track_names()[1])
        revision = other.get_revision()
        self.assertTrue(other.names_item(section=Section.TRACKS, name=test_bypass_when.LEAD))
        song_read.rename_item(section=Section.TRACKS, old=test_bypass_when.LEAD, new=RENAMED)
        self.assertEqual(other.get_built_in(chords_plugin.NAME).get_written(ChordsSetting.CHORDS_FROM), RENAMED)
        self.assertNotEqual(other.get_revision(), revision)


if __name__ == '__main__':
    unittest.main()
