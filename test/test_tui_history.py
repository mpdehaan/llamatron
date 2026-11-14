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
"""The undo history underneath the tracker: the ring of snapshots, and the document stepping through it.

The pages' side, pressing Ctrl+Z and Ctrl+Y on every page, is in test_tui_undo.py.
"""

import os
import tempfile
import unittest
from unittest import mock

from llamatron.composition.file_format import ClipSlotSetting, Row, Section, SetlistSetting, SongSetting
from llamatron.composition.limits import MIN_REPEAT
from llamatron.composition.named_items import NamedItems
from llamatron.composition.pattern import Pattern
from llamatron.music.note import NoteName
from llamatron.tui.document import Document
from llamatron.tui.history import describe_change, History, HISTORY_DEPTH, renamed_items, Snapshot
from llamatron.strings.errors import ERR_CHANGED_SNAPSHOT, ERR_STALE_DATA, ERR_WRONG_RESTORE
from llamatron.support.memory import Memory, StaleAnswer
from llamatron.strings.messages import MSG_CHANGED_IN_SONG, MSG_CHANGED_NAMED, MSG_CHANGED_SCENE, MSG_CHANGED_THE_SET, MSG_CHANGED_WORDS
from ui_testing import a_song, fixed_text, LEAD, ONE, OTHER, TUNE

# A history short enough to fill in a test, which only tests ask for: the tracker's is HISTORY_DEPTH and nothing shows or sets it.
SHORT_DEPTH = 3
SECOND_SONG = 'second'
# What a test writes into a snapshot's data after handing the snapshot over, which nothing in the program may do.
CHANGED_BEHIND_ITS_BACK = 99
A_VELOCITY = 90
NEW_TRACK = 'pad'
RENAMED = 'renamed'
FIRST_SCENE = 0
TWICE = 2
# A scene number as the status line counts it, from 1.
SECOND_SCENE = 2


def behind_its_back(pattern):
    """Change a pattern as a method that forgot @notes_change would: through the setter itself, without the mark that moves the revision."""
    Pattern.set_value.__wrapped__(pattern, row=Row.VELOCITY, step=0, value=A_VELOCITY)


def unchecked_song(test):
    """Return the test song in a document that checks nothing, as the tracker's own documents are, with the checks back on when the test ends."""
    Memory.check_every_answer(checks=False)
    test.addCleanup(Memory.check_every_answer)
    return a_song()


def snapshot(number, *, song=ONE):
    """Return a snapshot whose data is just a number, enough for the ring to tell apart."""
    return Snapshot(data={SetlistSetting.TITLE: number}, song=song)


class TestHistory(unittest.TestCase):

    def setUp(self):
        self.history = History(depth=SHORT_DEPTH)
        self.history.reset(snapshot(0))

    def test_starts_with_nothing_to_undo_or_redo(self):
        self.assertFalse(self.history.can_undo())
        self.assertFalse(self.history.can_redo())
        self.assertIsNone(self.history.undo())
        self.assertIsNone(self.history.redo())

    def test_the_depth_defaults_to_the_trackers(self):
        self.assertEqual(History().depth(), HISTORY_DEPTH)

    def test_records_a_step_and_walks_it_back_and_forward(self):
        self.assertTrue(self.history.record(snapshot(1)))
        self.assertTrue(self.history.can_undo())
        self.assertEqual(self.history.undo(), snapshot(0))
        self.assertTrue(self.history.can_redo())
        self.assertEqual(self.history.redo(), snapshot(1))
        self.assertIsNone(self.history.redo())

    def test_an_unchanged_snapshot_is_not_a_step(self):
        self.assertFalse(self.history.record(snapshot(0)))
        self.assertFalse(self.history.can_undo())

    def test_a_new_step_drops_the_redo_steps(self):
        self.history.record(snapshot(1))
        self.history.undo()
        self.history.record(snapshot(2))
        self.assertFalse(self.history.can_redo())
        self.assertEqual(self.history.undo(), snapshot(0))

    def test_the_oldest_step_drops_off_the_end_without_a_word(self):
        for number in range(1, SHORT_DEPTH + TWICE):
            self.history.record(snapshot(number))
        undone = []
        while self.history.can_undo():
            undone.append(self.history.undo())
        self.assertEqual(undone, [snapshot(number) for number in reversed(range(1, SHORT_DEPTH + 1))])

    def test_a_continuing_step_joins_the_one_before(self):
        self.history.record(snapshot(1))
        self.history.record(snapshot(12), continues=True)
        self.assertEqual(self.history.undo(), snapshot(0))
        self.assertEqual(self.history.redo(), snapshot(12))

    def test_a_continuing_step_with_nothing_before_it_is_an_ordinary_step(self):
        self.history.record(snapshot(1), continues=True)
        self.assertEqual(self.history.undo(), snapshot(0))

    def test_snapshots_are_shared_in_and_out_and_never_copied(self):
        # A snapshot's data is the data the set's objects keep, shared between snapshots, so the history hands back what it was given.
        first = self.history.now()
        given = snapshot(1)
        self.history.record(given)
        self.assertIs(self.history.now(), given)
        self.assertIs(self.history.undo(), first)
        self.assertIs(self.history.redo(), given)

    def test_a_history_that_checks_refuses_a_snapshot_changed_after_it_was_kept(self):
        for step in (History.now, History.undo):
            with self.subTest(step=step.__name__):
                history = History(depth=SHORT_DEPTH, checks=True)
                start = snapshot(0)
                history.reset(start)
                history.record(snapshot(1))
                # Unchanged, both come back.
                self.assertEqual(history.now(), snapshot(1))
                # The one handed back by this step is changed behind the history's back.
                changed = history.now() if step is History.now else start
                changed.data[SetlistSetting.TITLE] = CHANGED_BEHIND_ITS_BACK
                with self.assertRaises(StaleAnswer) as raised:
                    step(history)
                self.assertEqual(str(raised.exception), ERR_CHANGED_SNAPSHOT)

    def test_a_history_that_does_not_check_copies_nothing_and_notices_nothing(self):
        given = snapshot(1)
        self.history.record(given)
        given.data[SetlistSetting.TITLE] = CHANGED_BEHIND_ITS_BACK
        self.assertIs(self.history.now(), given)
        self.assertEqual(self.history.now().data[SetlistSetting.TITLE], CHANGED_BEHIND_ITS_BACK)

    def test_a_history_that_checks_starts_its_proofs_again_with_the_history(self):
        history = History(depth=SHORT_DEPTH, checks=True)
        history.reset(snapshot(0))
        history.record(snapshot(1))
        history.reset(snapshot(5))
        self.assertEqual(history.now(), snapshot(5))
        self.assertIsNone(history.undo())

    def test_noting_the_song_leaves_the_snapshot_given_as_it_was(self):
        given = snapshot(1)
        self.history.record(given)
        self.history.note_song(SECOND_SONG)
        self.assertEqual(given.song, ONE)
        self.assertEqual(self.history.now().song, SECOND_SONG)
        self.assertIs(self.history.now().data, given.data)

    def test_the_current_song_is_noted_without_an_edit(self):
        self.history.note_song(SECOND_SONG)
        self.history.record(snapshot(1))
        self.assertEqual(self.history.undo(), snapshot(0, song=SECOND_SONG))

    def test_reset_forgets_everything(self):
        self.history.record(snapshot(1))
        self.history.reset(snapshot(5))
        self.assertFalse(self.history.can_undo())
        self.assertEqual(self.history.now(), snapshot(5))


class TestDescribingAChange(unittest.TestCase):

    def setUp(self):
        self.document = a_song()
        self.before = self.document.setlist().to_data()

    def described(self):
        return describe_change(leaving=Snapshot(data=self.document.setlist().to_data(), song=ONE), arriving=Snapshot(data=self.before, song=ONE))

    def test_names_a_shared_item(self):
        self.document.set_step_value(name=TUNE, row=Row.DEGREE, step=0, value=2)
        self.assertEqual(self.described(), MSG_CHANGED_NAMED.format(kind=MSG_CHANGED_WORDS[Section.PATTERNS], name=TUNE))

    def test_names_a_track_in_its_song(self):
        self.document.add_track(NEW_TRACK)
        what = MSG_CHANGED_NAMED.format(kind=MSG_CHANGED_WORDS[Section.TRACKS], name=NEW_TRACK)
        self.assertEqual(self.described(), MSG_CHANGED_IN_SONG.format(song=self.document.current_song_name(), what=what))

    def test_names_a_scene_by_its_number(self):
        self.document.add_clip_slot(index=1, track=LEAD, pattern=TUNE)
        self.assertEqual(self.described(), MSG_CHANGED_IN_SONG.format(song=self.document.current_song_name(), what=MSG_CHANGED_SCENE.format(number=SECOND_SCENE)))

    def test_names_a_song_setting(self):
        self.document.set_tempo(self.document.song().get_tempo() + 1)
        self.assertEqual(self.described(), MSG_CHANGED_IN_SONG.format(song=self.document.current_song_name(), what=MSG_CHANGED_WORDS[SongSetting.TEMPO]))

    def test_names_a_setting_of_the_set(self):
        self.document.set_title(NEW_TRACK)
        self.assertEqual(self.described(), MSG_CHANGED_WORDS[SetlistSetting.TITLE])

    def test_names_a_song_that_came_or_went(self):
        self.document.add_song(SECOND_SONG)
        self.assertEqual(self.described(), MSG_CHANGED_IN_SONG.format(song=SECOND_SONG, what=MSG_CHANGED_WORDS[Section.SONGS]))

    def test_says_the_set_when_nothing_it_knows_differs(self):
        self.assertEqual(self.described(), MSG_CHANGED_THE_SET)


class TestFindingRenames(unittest.TestCase):
    """A rename is a name that changed at the same place with the same data, which is what lets a page follow it."""

    def setUp(self):
        self.document = a_song()
        self.before = Snapshot(data=self.document.setlist().to_data(), song=self.document.current_song_name())

    def renames(self):
        return renamed_items(leaving=self.before, arriving=Snapshot(data=self.document.setlist().to_data(), song=self.document.current_song_name()))

    def test_a_renamed_pattern_is_found_though_the_clips_naming_it_changed_too(self):
        self.document.rename_named(section=Section.PATTERNS, old=TUNE, new=RENAMED)
        self.assertEqual(self.renames(), {Section.PATTERNS: {TUNE: RENAMED}})

    def test_a_renamed_track_is_found_in_the_current_song(self):
        self.document.rename_named(section=Section.TRACKS, old=LEAD, new=RENAMED)
        self.assertEqual(self.renames(), {Section.TRACKS: {LEAD: RENAMED}})

    def test_a_renamed_scene_is_found_by_its_place(self):
        self.document.set_scene_name(index=FIRST_SCENE, name=RENAMED)
        self.assertEqual(self.renames(), {Section.SCENES: {FIRST_SCENE: RENAMED}})

    def test_a_scale_named_after_its_root_is_the_same_scale_when_the_root_moves(self):
        name = self.document.song().get_scale_names()[0]
        renamed = self.document.set_scale_root(name=name, root=NoteName.D)
        self.assertNotEqual(renamed, name)
        self.assertEqual(self.renames(), {Section.SCALES: {name: renamed}})

    def test_a_removal_is_not_a_rename(self):
        self.document.delete_named(section=Section.TRACKS, name=LEAD)
        self.assertEqual(self.renames(), {})

    def test_an_edit_is_not_a_rename(self):
        self.document.set_tempo(self.document.song().get_tempo() + 1)
        self.document.set_step_value(name=TUNE, row=Row.DEGREE, step=0, value=2)
        self.assertEqual(self.renames(), {})

    def test_the_undo_returns_its_renames_the_other_way_round(self):
        self.document.rename_named(section=Section.TRACKS, old=LEAD, new=RENAMED)
        self.document.record_edit()
        self.assertEqual(self.document.undo().renames, {Section.TRACKS: {RENAMED: LEAD}})
        self.assertEqual(self.document.redo().renames, {Section.TRACKS: {LEAD: RENAMED}})


class TestDocumentHistory(unittest.TestCase):
    """The document records one step per call to record_edit, however many setters ran, and to undo puts the set back, reading again only what the edit changed."""

    def setUp(self):
        self.document = a_song()

    def data(self):
        return self.document.setlist().to_data()

    def test_edits_are_recorded_when_asked_and_undone_as_one_step(self):
        before = self.data()
        self.document.add_track(NEW_TRACK)
        self.document.set_tempo(self.document.song().get_tempo() + 1)
        self.assertTrue(self.document.record_edit())
        self.assertFalse(self.document.record_edit())
        self.assertIsNotNone(self.document.undo())
        self.assertEqual(self.data(), before)
        self.assertIsNone(self.document.undo())
        self.assertIsNotNone(self.document.redo())
        self.assertEqual(self.document.song().get_track_names()[-1], NEW_TRACK)

    def test_an_undo_keeps_what_the_edit_did_not_change_and_builds_what_it_did(self):
        setlist = self.document.setlist()
        tune = setlist.get_pattern(TUNE)
        other = setlist.get_pattern(OTHER)
        song = self.document.song()
        self.document.set_step_value(name=TUNE, row=Row.VELOCITY, step=0, value=A_VELOCITY)
        self.document.record_edit()
        edited = self.data()
        self.document.undo()
        # The set is the same set, the pattern that was edited is read again, and everything else is the object it was.
        self.assertIs(self.document.setlist(), setlist)
        self.assertIsNot(setlist.get_pattern(TUNE), tune)
        self.assertIsNone(setlist.get_pattern(TUNE).get_value(row=Row.VELOCITY, step=0))
        self.assertIs(setlist.get_pattern(OTHER), other)
        self.assertIs(self.document.song(), song)
        self.document.redo()
        self.assertEqual(self.data(), edited)
        self.assertIs(setlist.get_pattern(OTHER), other)
        self.assertIs(self.document.song(), song)

    def test_an_undo_of_a_change_to_a_song_reads_the_song_again_and_keeps_the_patterns(self):
        setlist = self.document.setlist()
        tune = setlist.get_pattern(TUNE)
        song = self.document.song()
        before = self.data()
        self.document.set_clip_slot_repeat(index=FIRST_SCENE, track=LEAD, repeat=TWICE)
        self.document.record_edit()
        self.document.undo()
        self.assertEqual(self.data(), before)
        self.assertIsNot(self.document.song(), song)
        self.assertIs(setlist.get_pattern(TUNE), tune)

    def test_snapshots_share_every_piece_that_no_edit_between_them_changed(self):
        first = self.document.setlist().kept_data()
        self.document.set_step_value(name=TUNE, row=Row.VELOCITY, step=0, value=A_VELOCITY)
        self.document.record_edit()
        second = self.document.setlist().kept_data()
        self.assertIsNot(second[Section.PATTERNS][TUNE], first[Section.PATTERNS][TUNE])
        self.assertIs(second[Section.PATTERNS][OTHER], first[Section.PATTERNS][OTHER])
        # After the undo, the pattern read again keeps data of its own, equal to the first snapshot's.
        self.document.undo()
        third = self.document.setlist().kept_data()
        self.assertEqual(third, first)
        self.assertIs(third[Section.PATTERNS][OTHER], first[Section.PATTERNS][OTHER])

    def test_a_document_that_checks_refuses_data_kept_past_a_change(self):
        document = a_song()
        pattern = document.setlist().get_pattern(TUNE)
        pattern.kept_data()
        # A change made behind the pattern's back, as a method that forgot @notes_change would make it: the data kept is now wrong.
        behind_its_back(pattern)
        document.changed()
        with self.assertRaises(StaleAnswer) as raised:
            document.record_edit()
        self.assertIn(fixed_text(ERR_STALE_DATA), str(raised.exception))

    def test_a_document_that_does_not_check_takes_the_data_kept_as_it_is(self):
        document = unchecked_song(self)
        pattern = document.setlist().get_pattern(TUNE)
        kept = pattern.kept_data()
        behind_its_back(pattern)
        document.changed()
        document.record_edit()
        self.assertIs(document.setlist().kept_data()[Section.PATTERNS][TUNE], kept)

    def test_a_document_that_checks_refuses_an_undo_that_differs_from_loading_the_snapshot(self):
        document = a_song()
        document.set_step_value(name=TUNE, row=Row.VELOCITY, step=0, value=A_VELOCITY)
        document.record_edit()
        # The set is told that the pattern it has is the one the snapshot holds, so the undo keeps the edited pattern: the mistake the check is there for.
        with mock.patch.object(NamedItems, NamedItems.same_item.__name__, lambda self, *, name, data: self.find(name)):
            with self.assertRaises(StaleAnswer) as raised:
                document.undo()
        self.assertIn(fixed_text(ERR_WRONG_RESTORE), str(raised.exception))

    def test_a_continued_edit_joins_the_one_before(self):
        before = self.data()
        self.document.set_tempo(1)
        self.document.record_edit()
        self.document.continue_edit()
        self.document.set_tempo(12)
        self.document.record_edit()
        self.document.undo()
        self.assertEqual(self.data(), before)

    def test_the_continuation_is_forgotten_if_nothing_changed(self):
        self.document.continue_edit()
        self.assertFalse(self.document.record_edit())
        self.document.set_tempo(1)
        self.document.record_edit()
        self.document.set_tempo(2)
        self.document.record_edit()
        self.document.undo()
        self.assertEqual(self.document.song().get_tempo(), 1)

    def test_undoing_back_to_the_saved_set_reads_as_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'set.yml')
            self.document.save(path=path)
            self.document.set_tempo(1)
            self.document.record_edit()
            self.assertTrue(self.document.is_dirty())
            self.document.undo()
            self.assertFalse(self.document.is_dirty())
            self.document.redo()
            self.assertTrue(self.document.is_dirty())

    def test_saving_keeps_the_history(self):
        with tempfile.TemporaryDirectory() as folder:
            self.document.set_tempo(1)
            self.document.record_edit()
            self.document.save(path=os.path.join(folder, 'set.yml'))
            self.assertTrue(self.document.can_undo())

    def test_a_loaded_set_has_nothing_to_undo_because_nothing_about_the_history_is_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'set.yml')
            self.document.set_tempo(1)
            self.document.record_edit()
            self.document.save(path=path)
            loaded = Document.load(path)
            self.assertFalse(loaded.can_undo())
            self.assertEqual(loaded.setlist().to_data(), self.data())

    def test_undo_goes_back_to_the_song_the_edit_was_made_in(self):
        self.document.add_song(SECOND_SONG)
        self.document.record_edit()
        self.document.select_song(SECOND_SONG)
        self.document.set_tempo(1)
        self.document.record_edit()
        self.document.select_song(self.document.song_names()[0])
        self.document.undo()
        self.assertEqual(self.document.current_song_name(), SECOND_SONG)
        self.document.undo()
        self.assertEqual(self.document.song_names(), [self.document.current_song_name()])

    def test_undoing_the_deletion_of_the_current_song_makes_it_current_again(self):
        self.document.add_song(SECOND_SONG)
        self.document.record_edit()
        self.document.select_song(SECOND_SONG)
        self.document.delete_named(section=Section.SONGS, name=SECOND_SONG)
        self.document.record_edit()
        self.assertNotEqual(self.document.current_song_name(), SECOND_SONG)
        self.document.undo()
        self.assertEqual(self.document.current_song_name(), SECOND_SONG)

    def test_the_lengths_follow_an_undo(self):
        seconds = self.document.lengths().song_seconds()
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.REPEAT, value=MIN_REPEAT + 3)
        self.document.record_edit()
        self.assertNotEqual(self.document.lengths().song_seconds(), seconds)
        self.document.undo()
        self.assertEqual(self.document.lengths().song_seconds(), seconds)

    def test_forgetting_the_history_starts_again_from_now(self):
        self.document.set_tempo(1)
        self.document.record_edit()
        self.document.forget_history()
        self.assertFalse(self.document.can_undo())
        self.assertEqual(self.document.song().get_tempo(), 1)


if __name__ == '__main__':
    unittest.main()
