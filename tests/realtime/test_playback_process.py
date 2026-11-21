# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later


"""The render process (realtime/playback_process.py, realtime/render_process.py, realtime/set_changes.py): the set crossing as the items that changed, a launch played through a
recording Realtime Sender Process and its notes sent, what plays read from its status messages, and a song that cannot be
played refused as the transport's pages expect."""

import os
import signal
import subprocess
import sys
import threading
import time
import unittest

from llamatron.model.file.song_file_error import SongFileError
from llamatron.model.vocabulary.file_format import ClipSlotSetting, Row, Section
from llamatron.realtime import playback
from llamatron.realtime.playback import Launch, Wanted
from llamatron.realtime.playback_process import PlaybackProcess
from llamatron.realtime.set_changes import changed_items, with_changes
from llamatron.realtime.timeline import Route
from tests.support import song_testing
from tests.support.rendering import setlist_from_data

PORT = 'test port'
LEAD = song_testing.LEAD
KICK = 'kick'
TUNE = 'tune'
BEAT = 'beat'
SEED = 3
FIRST_REVISION = 1
NO_LEAD = 0.0
# A tune of four short notes at the default tempo, about a second.
NOTES = 4
SIXTEENTH = '1/16'
WAIT_SECONDS = 10.0
STEP_SECONDS = 0.05
NOTE_ON_STATUS = 0x90
STATUS_KIND = 0xF0
CHANGED_VELOCITY = 33
CHANGED_DEGREE = 5
ANOTHER_PATTERN = 'another'
# Closing asks, waits a second for an answer and a second for the process to end, then ends its group: well under five seconds.
CLOSING_ALLOWED_SECONDS = 5.0
# The stand-in for a tracker killed outright, run in an interpreter of its own from the top folder.
TOP_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
TRACKER_KILLED = os.path.join(TOP_FOLDER, 'tests', 'support', 'tracker_killed.py')
PYTHON_PATH = 'PYTHONPATH'
NEVER_QUIET = 'the render process still played after the wait'


def a_set(*, grabs_in_a_circle=False):
    """Return a set of one song whose lead plays a tune of four notes once, beside a kick, the two grabbing from each other in a circle when asked, which no render can play."""
    lead = {ClipSlotSetting.PATTERN: TUNE, ClipSlotSetting.REPEAT: 1}
    kick = {ClipSlotSetting.PATTERN: BEAT, ClipSlotSetting.REPEAT: 1}
    if grabs_in_a_circle:
        lead[ClipSlotSetting.GRAB_TRACK] = KICK
        kick[ClipSlotSetting.GRAB_TRACK] = LEAD
    tune = song_testing.pat(*[[1, SIXTEENTH]] * NOTES, grab=[True] * NOTES) if grabs_in_a_circle else song_testing.pat(*[[1, SIXTEENTH]] * NOTES)
    beat = song_testing.pat([1, SIXTEENTH], grab=[True]) if grabs_in_a_circle else song_testing.pat([1, SIXTEENTH])
    return setlist_from_data(song_testing.with_parts(patterns={TUNE: tune, BEAT: beat}, scenes=[{Section.TRACKS: {LEAD: lead, KICK: kick}}]))


def wanted_of(setlist, *, revision=FIRST_REVISION):
    """Return what a score of the set's song is made from, the lead through the test's port and the kick through nothing."""
    return Wanted(revision, setlist.first_song_name(), ((LEAD, Route(PORT, 0)),), SEED)


def note_ons(sent):
    """Return the note ons a recording sender sent on the test's port, from what its close handed back."""
    _start, by_port = sent
    return [data for _seconds, data in by_port[PORT] if data[0] & STATUS_KIND == NOTE_ON_STATUS and data[2] > 0]


def group_is_gone(group):
    """Return whether no process of a process group is left, waiting a moment for the system to reap what was ended."""
    done = threading.Event()
    for _ in range(round(WAIT_SECONDS / STEP_SECONDS)):
        try:
            os.killpg(group, 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            # Ended and not yet reaped.
            pass
        done.wait(STEP_SECONDS)
    return False


class TestChangedItems(unittest.TestCase):

    def setUp(self):
        self.setlist = a_set()
        self.before = self.setlist.kept_data()

    def test_nothing_changed_sends_nothing(self):
        self.assertEqual(changed_items(before=self.before, after=self.setlist.kept_data()), ([], []))

    def test_an_edit_to_a_step_sends_that_steps_value_alone(self):
        self.setlist.get_pattern(TUNE).set_value(row=Row.DEGREE, step=0, value=CHANGED_DEGREE)
        changes, removed = changed_items(before=self.before, after=self.setlist.kept_data())
        self.assertEqual(changes, [((Section.PATTERNS, TUNE, Row.DEGREE, 0), CHANGED_DEGREE)])
        self.assertEqual(removed, [])

    def test_the_changes_made_give_the_set_as_it_is_now_and_leave_the_data_before_alone(self):
        self.setlist.get_pattern(TUNE).set_value(row=Row.VELOCITY, step=0, value=CHANGED_VELOCITY)
        self.setlist.rename_item(section=Section.PATTERNS, old=BEAT, new=ANOTHER_PATTERN)
        after = self.setlist.kept_data()
        before_patterns = dict(self.before[Section.PATTERNS])
        changes, removed = changed_items(before=self.before, after=after)
        self.assertEqual(with_changes(data=self.before, changes=changes, removed=removed), after)
        self.assertEqual(self.before[Section.PATTERNS], before_patterns)

    def test_a_whole_part_that_goes_is_removed(self):
        changes, removed = changed_items(before={**self.before, ANOTHER_PATTERN: True}, after=self.before)
        self.assertEqual((changes, removed), ([], [(ANOTHER_PATTERN,)]))


class TestPlaybackProcess(unittest.TestCase):
    """A real render process with a recording sender, so that nothing is heard."""

    def setUp(self):
        self.playback = PlaybackProcess(lead=NO_LEAD, recording=True)
        self.addCleanup(self.playback.close)

    def wait_until_quiet(self):
        """Wait, ticking as the tracker would, until nothing plays."""
        done = threading.Event()
        for _ in range(round(WAIT_SECONDS / STEP_SECONDS)):
            self.playback.tick()
            if not self.playback.is_playing():
                return
            done.wait(STEP_SECONDS)
        self.fail(NEVER_QUIET)

    def test_a_launch_plays_every_note_and_its_status_says_what_plays(self):
        setlist = a_set()
        self.playback.take_set(setlist.kept_data())
        waits = self.playback.launch(wanted=wanted_of(setlist), launch=Launch(playback.LAUNCH_SCENE, 0), ports=[PORT])
        self.assertFalse(waits)
        self.assertTrue(self.playback.is_playing())
        self.assertEqual(self.playback.playing_scenes(), [0])
        self.assertTrue(self.playback.is_clip_playing(index=0, track=LEAD))
        self.assertIsNotNone(self.playback.scene_elapsed(0))
        self.wait_until_quiet()
        self.assertEqual(len(note_ons(self.playback.close())), NOTES)

    def test_a_score_built_ahead_is_told_of_and_launched_without_a_render(self):
        setlist = a_set()
        wanted = wanted_of(setlist)
        self.playback.take_set(setlist.kept_data())
        self.playback.build(wanted)
        done = threading.Event()
        for _ in range(round(WAIT_SECONDS / STEP_SECONDS)):
            if self.playback.built(wanted) is not None:
                break
            done.wait(STEP_SECONDS)
        self.assertIsNone(self.playback.built(wanted).problem)
        self.assertFalse(self.playback.launch(wanted=wanted, launch=Launch(playback.LAUNCH_SCENE, 0), ports=[PORT]))
        self.assertTrue(self.playback.has_score(wanted))

    def test_a_song_that_cannot_be_played_is_refused_and_the_process_plays_on(self):
        broken = a_set(grabs_in_a_circle=True)
        self.playback.take_set(broken.kept_data())
        with self.assertRaises(SongFileError):
            self.playback.launch(wanted=wanted_of(broken), launch=Launch(playback.LAUNCH_SCENE, 0), ports=[PORT])
        setlist = a_set()
        self.playback.take_set(setlist.kept_data())
        self.playback.launch(wanted=wanted_of(setlist, revision=FIRST_REVISION + 1), launch=Launch(playback.LAUNCH_SCENE, 0), ports=[PORT])
        self.wait_until_quiet()
        self.assertEqual(len(note_ons(self.playback.close())), NOTES)
        self.assertFalse(self.playback.has_ended())

    def test_a_stuck_render_process_and_its_sender_are_ended_by_closing_and_quickly(self):
        setlist = a_set()
        self.playback.take_set(setlist.kept_data())
        self.playback.launch(wanted=wanted_of(setlist), launch=Launch(playback.LAUNCH_SCENE, 0), ports=[PORT])
        group = self.playback.get_process_id()
        os.kill(group, signal.SIGSTOP)
        began = time.monotonic()
        self.playback.close()
        self.assertLess(time.monotonic() - began, CLOSING_ALLOWED_SECONDS)
        # Nothing of the render process's group is left, the Realtime Sender Process included, once the system has reaped what
        # was ended, which it answers for with "not permitted" for a moment.
        self.assertTrue(group_is_gone(group))


class TestKilledTracker(unittest.TestCase):
    """A tracker killed outright runs nothing of its closing, so the render process's watcher ends it (render_process.watch_lifeline)."""

    def test_a_render_process_and_its_sender_end_when_the_tracker_is_killed(self):
        tracker = subprocess.Popen([sys.executable, TRACKER_KILLED], stdout=subprocess.PIPE, text=True, cwd=TOP_FOLDER, env={**os.environ, PYTHON_PATH: TOP_FOLDER})
        self.addCleanup(tracker.wait)
        group = int(tracker.stdout.readline())
        os.kill(tracker.pid, signal.SIGKILL)
        tracker.stdout.close()
        self.assertTrue(group_is_gone(group))


if __name__ == '__main__':
    unittest.main()
