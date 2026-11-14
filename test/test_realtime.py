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

"""Real-time playback below the tracker: the timeline against the MIDI export, the engine on a stepped clock, and the Realtime Sender Process on the real one.

The timeline test is the exact one: every example's timeline holds the events its MIDI export writes, tick for tick,
so whatever the export plays, real time plays. The engine tests press stop and check that the note offs, all notes
off and all sound off arrive for the right notes and channels, with no time passing. The process test is the short
lag test, a few seconds of a real song through the real process with recording outputs, allowed a few milliseconds
because the suite loads the machine; the ultra-tight check is `internal_tools/realtime_report.sh` on an idle machine.
"""

import os
import subprocess
import sys
import tempfile
import time
import unittest

import mido

from llamatron.composition.file_format import ClipSlotSetting, FollowAction, PatternSetting, Row, ScaleSetting, SceneSetting, Section, SongSetting
from llamatron.composition.named_scale import scale_type_name
from llamatron.composition.setlist import DEFAULT_SCALE
from llamatron.music.note import ROOT_NAMES
from llamatron.music.scale import ScaleType
from llamatron.composition.setlist import Setlist
from llamatron.music.midi import MAX_MIDI_NUMBER, MIN_MIDI_NUMBER
from llamatron.exporters.midi_arrangement import MidiSong
from llamatron.exporters.midi_messages import ticks
from llamatron.playback.song_renderer import SongRenderer
from llamatron.realtime.engine import ALL_NOTES_OFF, ALL_SOUND_OFF, PlaybackEngine, SteppedClock
from llamatron.realtime.outputs import RecordingOutput
from llamatron.realtime.player import Player
from llamatron.realtime.score import Score
from llamatron.realtime.sender_process import RealtimeMIDISenderProcess, SenderNotStarted
from llamatron.strings.errors import ERR_SENDER_DID_NOT_START
from sender_under_capture import STARTED
from llamatron.realtime.timeline import CONTROL_CHANGE, KIND_MASK, NOTE_OFF, NOTE_ON, NO_VELOCITY, Playing, Route, Tag, song_timeline
from llamatron.support.example_sets import example_sets

from rendering import song_from_data, song_from_file

EXAMPLES = example_sets()
SEED = 1
PORT = 'test port'
OTHER_PORT = 'other port'
# The export writes every track on channel 0, so the timeline is compared on that channel.
EXPORT_CHANNEL = 0
NOTE_ON_MESSAGE = 'note_on'
NOTE_OFF_MESSAGE = 'note_off'
CONTROL_CHANGE_MESSAGE = 'control_change'
KIND_OF_MESSAGE = {NOTE_ON_MESSAGE: NOTE_ON, NOTE_OFF_MESSAGE: NOTE_OFF, CONTROL_CHANGE_MESSAGE: CONTROL_CHANGE}
# The conductor track comes first in the export, then one track per unmuted track.
CONDUCTOR_TRACKS = 1
# The short lag test: how much of a song, how long to wait for it, and how far off an event may be in the loaded suite.
LAG_SONG = 'examples/by_genre/ragtime/entertainer.yml'
LAG_SECONDS = 3.0
LAG_SETTLE_SECONDS = 0.3
LAG_LIMIT_SECONDS = 0.010
UNDER_CAPTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sender_under_capture.py')
SUBPROCESS_TIMEOUT_SECONDS = 60
SUCCESS = 0
NO_SUCH_PORT = 'no such port anywhere'
MILLISECONDS = 1000
MIDDLE_C = 60
A_FIFTH_UP = 67
VELOCITY = 100
SCENE_ONE = Tag(0, 'lead')
SCENE_TWO = Tag(1, 'lead')
BASS_TAG = Tag(0, 'bass')


def rendered_songs(path):
    """Return each song of a set file with its grid, rendered with one seed."""
    setlist = Setlist.read_file(path)
    for name in setlist.get_song_names():
        yield name, SongRenderer(setlist.get_song(name), seed=SEED).render()


def routes_on_one_channel(grid):
    """Return a route for every unmuted track, all on the export's channel of one port."""
    return {track.get_name(): Route(PORT, EXPORT_CHANNEL) for track in grid.get_columns() if not track.get_mute()}


def exported_events(grid):
    """Return what the MIDI export writes for a grid, as (track place, tick, kind, number, value) with note offs' velocity left out."""
    with tempfile.TemporaryDirectory() as directory:
        exporter = MidiSong(directory=directory, grid=grid)
        exporter.export()
        midi_file = mido.MidiFile(exporter.path())
    events = set()
    for place, track in enumerate(midi_file.tracks[CONDUCTOR_TRACKS:]):
        tick = 0
        for message in track:
            tick += message.time
            if message.type in KIND_OF_MESSAGE:
                events.add(described(place=place, tick=tick, kind=KIND_OF_MESSAGE[message.type], number=message_number(message), value=message_value(message)))
    return events


def message_number(message):
    return message.control if message.type == CONTROL_CHANGE_MESSAGE else message.note


def message_value(message):
    if message.type == NOTE_OFF_MESSAGE:
        return NO_VELOCITY
    return message.value if message.type == CONTROL_CHANGE_MESSAGE else message.velocity


def described(*, place, tick, kind, number, value):
    return (place, tick, kind, number, value)


def timeline_events(*, grid, timeline):
    """Return a timeline's events described like the export's, with the track's place among the unmuted tracks."""
    places = {track.get_name(): place for place, track in enumerate(track for track in grid.get_columns() if not track.get_mute())}
    return {described(place=places[event.tag.track], tick=ticks(event.whole), kind=event.kind, number=event.number, value=event.value) for event in timeline}


class TestTimeline(unittest.TestCase):
    """The timeline holds what the MIDI export writes, for every example."""

    def test_every_examples_timeline_holds_the_events_its_midi_export_writes_tick_for_tick(self):
        for path in EXAMPLES:
            for name, grid in rendered_songs(path):
                with self.subTest(path=path, song=name):
                    timeline = song_timeline(grid=grid, routes=routes_on_one_channel(grid))
                    self.assertEqual(timeline_events(grid=grid, timeline=timeline), exported_events(grid))

    def test_the_timeline_is_in_time_order_with_note_offs_before_note_ons_at_one_instant(self):
        for path in EXAMPLES:
            for name, grid in rendered_songs(path):
                timeline = song_timeline(grid=grid, routes=routes_on_one_channel(grid))
                for earlier, later in zip(timeline, timeline[1:]):
                    self.assertLessEqual(earlier.whole, later.whole)
                    self.assertLessEqual(earlier.seconds, later.seconds)
                    if earlier.whole == later.whole and earlier.kind == NOTE_ON:
                        self.assertNotEqual(later.kind, NOTE_OFF)

    def test_a_track_with_no_route_and_a_muted_track_are_left_out(self):
        song = song_from_file(LAG_SONG)
        grid = SongRenderer(song, seed=SEED).render()
        routes = routes_on_one_channel(grid)
        left_out = next(iter(routes))
        del routes[left_out]
        timeline = song_timeline(grid=grid, routes=routes)
        self.assertTrue(timeline)
        self.assertNotIn(left_out, {event.tag.track for event in timeline})
        self.assertTrue(set(routes) >= {event.tag.track for event in timeline})


def note(*, seconds, number, tag, kind=NOTE_ON, port=PORT, channel=0):
    return Playing(seconds, seconds, port, channel, kind, number, VELOCITY if kind == NOTE_ON else NO_VELOCITY, tag)


class TestPlaybackEngine(unittest.TestCase):
    """The engine on a stepped clock: events go out on time, and stopping silences what sounds."""

    def setUp(self):
        self.clock = SteppedClock()
        self.output = RecordingOutput()
        self.other = RecordingOutput()
        self.engine = PlaybackEngine(clock=self.clock, outputs={PORT: self.output, OTHER_PORT: self.other})
        self.engine.start()

    def sent(self):
        return [data for _, data in self.output.sent]

    def sent_elsewhere(self):
        return [data for _, data in self.other.sent]

    def test_an_event_is_sent_when_its_time_comes_and_not_before(self):
        self.engine.add([note(seconds=1.0, number=MIDDLE_C, tag=SCENE_ONE)])
        self.clock.advance(0.999)
        self.assertEqual(self.engine.send_due(), 0)
        self.assertEqual(self.sent(), [])
        self.clock.advance(0.001)
        self.assertEqual(self.engine.send_due(), 1)
        self.assertEqual(self.sent(), [[NOTE_ON, MIDDLE_C, VELOCITY]])
        self.assertEqual(self.engine.next_due(), None)

    def test_events_added_out_of_order_are_sent_in_order_with_note_offs_first_at_one_instant(self):
        self.engine.add([
            note(seconds=2.0, number=MIDDLE_C, tag=SCENE_ONE),
            note(seconds=1.0, number=MIDDLE_C, tag=SCENE_ONE),
            note(seconds=2.0, number=MIDDLE_C, tag=SCENE_ONE, kind=NOTE_OFF),
        ])
        self.clock.advance(2.0)
        self.engine.send_due()
        self.assertEqual(self.sent(), [[NOTE_ON, MIDDLE_C, VELOCITY], [NOTE_OFF, MIDDLE_C, NO_VELOCITY], [NOTE_ON, MIDDLE_C, VELOCITY]])

    def test_stop_all_sends_note_offs_for_the_sounding_notes_then_silences_every_channel_used(self):
        self.engine.add([
            note(seconds=0.0, number=MIDDLE_C, tag=SCENE_ONE),
            note(seconds=0.0, number=A_FIFTH_UP, tag=BASS_TAG, channel=1),
            note(seconds=0.5, number=A_FIFTH_UP, tag=BASS_TAG, channel=1, kind=NOTE_OFF),
            note(seconds=5.0, number=MIDDLE_C, tag=SCENE_ONE, kind=NOTE_OFF),
        ])
        self.clock.advance(1.0)
        self.engine.send_due()
        self.assertEqual(self.engine.sounding(), [(PORT, 0, MIDDLE_C)])
        self.output.sent.clear()
        self.engine.stop_all()
        self.assertEqual(self.sent(), [
            [NOTE_OFF, MIDDLE_C, NO_VELOCITY],
            [CONTROL_CHANGE, ALL_NOTES_OFF, 0], [CONTROL_CHANGE, ALL_SOUND_OFF, 0],
            [CONTROL_CHANGE | 1, ALL_NOTES_OFF, 0], [CONTROL_CHANGE | 1, ALL_SOUND_OFF, 0],
        ])
        self.assertEqual(self.engine.sounding(), [])
        self.assertEqual(self.engine.pending(), [])

    def test_stopping_one_tag_silences_its_notes_and_drops_its_events_and_leaves_the_others_alone(self):
        self.engine.add([
            note(seconds=0.0, number=MIDDLE_C, tag=SCENE_ONE),
            note(seconds=0.0, number=A_FIFTH_UP, tag=BASS_TAG),
            note(seconds=3.0, number=MIDDLE_C, tag=SCENE_ONE, kind=NOTE_OFF),
            note(seconds=3.0, number=A_FIFTH_UP, tag=BASS_TAG, kind=NOTE_OFF),
        ])
        self.engine.send_due()
        self.output.sent.clear()
        self.engine.stop_tag(SCENE_ONE)
        self.assertEqual(self.sent(), [[NOTE_OFF, MIDDLE_C, NO_VELOCITY]])
        self.assertEqual(self.engine.sounding(), [(PORT, 0, A_FIFTH_UP)])
        self.assertEqual([event.tag for event in self.engine.pending()], [BASS_TAG])

    def test_dropping_a_tag_from_a_time_keeps_its_earlier_events_and_what_is_sounding(self):
        self.engine.add([
            note(seconds=0.0, number=MIDDLE_C, tag=SCENE_ONE),
            note(seconds=1.0, number=MIDDLE_C, tag=SCENE_ONE, kind=NOTE_OFF),
            note(seconds=2.0, number=A_FIFTH_UP, tag=SCENE_ONE),
            note(seconds=2.0, number=A_FIFTH_UP, tag=SCENE_TWO),
        ])
        self.engine.send_due()
        self.engine.drop(tag=SCENE_ONE, after=1.5)
        self.assertEqual([(event.seconds, event.tag) for event in self.engine.pending()], [(1.0, SCENE_ONE), (2.0, SCENE_TWO)])
        self.assertEqual(self.engine.sounding(), [(PORT, 0, MIDDLE_C)])

    def test_events_go_to_the_port_of_their_route_and_close_silences_and_closes_every_port(self):
        self.engine.add([note(seconds=0.0, number=MIDDLE_C, tag=SCENE_ONE, port=OTHER_PORT, channel=3)])
        self.engine.send_due()
        self.assertEqual(self.sent(), [])
        self.assertEqual(self.sent_elsewhere(), [[NOTE_ON | 3, MIDDLE_C, VELOCITY]])
        self.engine.close()
        self.assertEqual(self.sent_elsewhere()[1:], [[NOTE_OFF | 3, MIDDLE_C, NO_VELOCITY], [CONTROL_CHANGE | 3, ALL_NOTES_OFF, 0], [CONTROL_CHANGE | 3, ALL_SOUND_OFF, 0]])


class TestRealtimeSenderProcess(unittest.TestCase):
    """The real process on the real clock, sending a few seconds of a song into recording outputs."""

    def test_it_starts_while_textual_has_replaced_standard_error(self):
        """In a fresh interpreter, whose resource tracker hasn't started, the process starts with a stderr like Textual's capture in place, which failed on 2026-11-10."""
        result = subprocess.run([sys.executable, UNDER_CAPTURE], capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_SECONDS, check=False)
        self.assertEqual(result.returncode, SUCCESS, result.stderr)
        self.assertEqual(result.stdout.strip(), STARTED)

    def test_closing_a_sender_whose_process_never_ran_returns_at_once(self):
        sender = RealtimeMIDISenderProcess(ports=[PORT], recording=True)
        self.assertIsNone(sender.close())

    def test_a_port_that_cannot_be_opened_fails_the_start_in_the_programs_words(self):
        sender = RealtimeMIDISenderProcess(ports=[NO_SUCH_PORT])
        with self.assertRaises(SenderNotStarted) as caught:
            sender.start()
        self.assertEqual(str(caught.exception), ERR_SENDER_DID_NOT_START)
        self.assertIsNone(sender.close())

    def test_a_few_seconds_of_a_song_arrive_in_order_within_the_suites_limit_and_stop_silences(self):
        song = song_from_file(LAG_SONG)
        grid = SongRenderer(song, seed=SEED).render()
        routes = {track.get_name(): Route(PORT, place) for place, track in enumerate(grid.get_columns())}
        events = [event for event in song_timeline(grid=grid, routes=routes) if event.seconds < LAG_SECONDS]
        sender = RealtimeMIDISenderProcess(ports=[PORT], recording=True)
        sender.start()
        sender.add(events)
        time.sleep(LAG_SECONDS + LAG_SETTLE_SECONDS)
        started, sent = sender.close()
        arrived = sent[PORT][:len(events)]
        self.assertEqual([data for _, data in arrived], [event.data() for event in events])
        worst = max(abs((at - started) - event.seconds) for event, (at, _) in zip(events, arrived))
        self.assertLess(worst, LAG_LIMIT_SECONDS, worst * MILLISECONDS)
        # Closing cut the song short, so the notes still sounding get their note offs first, then every channel is silenced.
        silencing = [data for _, data in sent[PORT][len(events):]]
        channels = sorted({event.channel for event in events})
        controls = [[CONTROL_CHANGE | channel, number, 0] for channel in channels for number in (ALL_NOTES_OFF, ALL_SOUND_OFF)]
        self.assertEqual(silencing[-len(controls):], controls)
        self.assertTrue(all(data[0] & KIND_MASK == NOTE_OFF for data in silencing[:-len(controls)]))


if __name__ == '__main__':
    unittest.main()


# The player's song: two tracks and three scenes of one-bar patterns, each scene a whole note long at the default tempo, so a scene lasts two seconds.
LEAD = 'lead'
BASS = 'bass'
HIGH = 'high'
LOW = 'low'
SCENE_SECONDS = 2.0
QUARTER = '1/4'
FAR_AHEAD = 1000.0
HALF_A_SCENE = 1.0
TWO_FOUR = '2/4'
ONE_ONE = '1/1'
STEP = 0.25
FIRST = 0
SECOND = 1
THIRD = 2
NO_PLAYS = 0


def player_song(*, follow_actions=(), launch_apart=(), loops=(), steps=4):
    """Return a song of three scenes on two tracks: follow_actions maps (scene, track) to a follow action, launch_apart lists the scenes with Launch together off, loops the (scene, track) that loop, and steps is how many quarter-note steps each pattern has."""
    scenes = []
    for place in range(3):
        tracks = {}
        for track, pattern in ((LEAD, HIGH), (BASS, LOW)):
            clip = {ClipSlotSetting.PATTERN: pattern}
            if (place, track) in follow_actions:
                clip[ClipSlotSetting.FOLLOW_ACTION] = follow_actions[(place, track)]
            if (place, track) in loops:
                clip[ClipSlotSetting.LOOP] = True
            tracks[track] = clip
        scene = {SceneSetting.TRACKS: tracks}
        if place in launch_apart:
            scene[SceneSetting.LAUNCH_TOGETHER] = False
        scenes.append(scene)
    data = {
        Section.PATTERNS: {
            HIGH: {PatternSetting.STEPS: steps, PatternSetting.STEP_SIZE: QUARTER, Row.DEGREE: [1, 2, 3, 4][:steps], Row.OCTAVE: [6, 6, 6, 6][:steps]},
            LOW: {PatternSetting.STEPS: steps, PatternSetting.STEP_SIZE: QUARTER, Row.DEGREE: [1, None, 1, None][:steps], Row.OCTAVE: [3, None, 3, None][:steps]},
        },
        Section.SCALES: {DEFAULT_SCALE: {ScaleSetting.ROOT: ROOT_NAMES[0], ScaleSetting.TYPE: scale_type_name(ScaleType.MAJOR)}},
        SongSetting.SCALE: DEFAULT_SCALE, Section.TRACKS: {LEAD: {}, BASS: {}}, Section.SCENES: scenes,
    }
    return song_from_data(data)


def two_routes():
    return {LEAD: Route(PORT, EXPORT_CHANNEL), BASS: Route(OTHER_PORT, EXPORT_CHANNEL)}


class PlayerTest(unittest.TestCase):
    """A player on an engine with a stepped clock, so that nothing waits."""

    def start(self, song, *, routes=None, time_signature=None):
        routes = two_routes() if routes is None else routes
        if time_signature is not None:
            song.set_time_signature(time_signature)
        self.clock = SteppedClock()
        self.outputs = {PORT: RecordingOutput(), OTHER_PORT: RecordingOutput()}
        self.engine = PlaybackEngine(clock=self.clock, outputs=self.outputs)
        self.engine.start()
        self.sent = {PORT: [], OTHER_PORT: []}
        self.score = Score(song=song, routes=routes, seed=SEED)
        self.player = Player(score=self.score, sender=self.engine, now=self.engine.elapsed)
        return self.player

    def run_until(self, seconds):
        """Let the clock run to a moment in small steps, ticking and sending as the tracker would, and note what was sent at each step on the stepped clock."""
        while True:
            self.player.tick()
            self.engine.send_due()
            for port, output in self.outputs.items():
                self.sent[port].extend((self.engine.elapsed(), data) for _, data in output.sent)
                output.sent.clear()
            if self.engine.elapsed() >= seconds:
                break
            self.clock.advance(min(STEP, seconds - self.engine.elapsed()))

    def note_ons(self, port):
        """Return the seconds of every note on sent to a port, to the step the clock was on when it went out."""
        return [round(seconds, 6) for seconds, data in self.sent[port] if data[0] & KIND_MASK == NOTE_ON]

    def pending_ons(self, track):
        """Return the seconds of every note on still queued for a track."""
        return [round(event.seconds, 6) for event in self.engine.pending() if event.kind == NOTE_ON and event.tag.track == track]


class TestScore(unittest.TestCase):

    def test_a_scene_lasts_its_rows_and_each_clips_events_count_from_the_scenes_start(self):
        score = Score(song=player_song(), routes=two_routes(), seed=SEED)
        self.assertEqual(score.scene_count(), 3)
        self.assertEqual([score.scene_seconds(place) for place in range(3)], [SCENE_SECONDS] * 3)
        self.assertEqual([score.scene_start(place) for place in range(3)], [0.0, SCENE_SECONDS, 2 * SCENE_SECONDS])
        self.assertEqual(score.song_seconds(), 3 * SCENE_SECONDS)
        starts = [event.seconds for event in score.events(scene=SECOND, track=LEAD) if event.kind == NOTE_ON]
        self.assertEqual(starts, [0.0, 0.5, 1.0, 1.5])
        self.assertEqual(score.events(scene=SECOND, track=BASS)[0].port, OTHER_PORT)

    def test_a_track_with_no_route_has_no_events_and_an_empty_slot_counts_as_with_scene(self):
        song = player_song()
        song.get_scene(THIRD).remove_clip_slot(BASS)
        score = Score(song=song, routes={LEAD: Route(PORT, EXPORT_CHANNEL)}, seed=SEED)
        self.assertEqual(score.events(scene=FIRST, track=BASS), [])
        self.assertEqual(score.follow_action(scene=THIRD, track=BASS), FollowAction.WITH_SCENE)
        self.assertFalse(score.loops(scene=THIRD, track=BASS))

    def test_the_sounding_notes_and_the_repeats_left_are_read_from_the_events(self):
        score = Score(song=player_song(), routes=two_routes(), seed=SEED)
        self.assertTrue(score.is_sounding(scene=FIRST, track=LEAD, elapsed=0.1))
        self.assertFalse(score.is_sounding(scene=FIRST, track=BASS, elapsed=0.6))
        self.assertEqual(score.sounding_across(scene=FIRST, track=LEAD, elapsed=0.1), [(PORT, EXPORT_CHANNEL, score.events(scene=FIRST, track=LEAD)[0].number)])
        self.assertEqual(score.repeats_left(scene=FIRST, track=LEAD, elapsed=0.1), 1)

    def test_how_far_into_a_clip_a_moment_is_stops_at_the_clips_end_and_starts_over_for_a_looping_clip(self):
        score = Score(song=player_song(loops={(FIRST, BASS)}), routes=two_routes(), seed=SEED)
        self.assertAlmostEqual(score.clip_elapsed(scene=FIRST, track=LEAD, elapsed=HALF_A_SCENE), HALF_A_SCENE)
        self.assertAlmostEqual(score.clip_elapsed(scene=FIRST, track=LEAD, elapsed=SCENE_SECONDS + HALF_A_SCENE), SCENE_SECONDS)
        self.assertAlmostEqual(score.clip_elapsed(scene=FIRST, track=BASS, elapsed=SCENE_SECONDS + HALF_A_SCENE), HALF_A_SCENE)
        song = player_song()
        song.get_scene(THIRD).remove_clip_slot(BASS)
        self.assertIsNone(Score(song=song, routes=two_routes(), seed=SEED).clip_elapsed(scene=THIRD, track=BASS, elapsed=0.0))


class TestPlayerFollowsTheExport(PlayerTest):

    def test_every_example_played_from_the_top_sends_what_its_timeline_holds_and_ends(self):
        """Every song plays to its end as the export has it, looping clips included, since a scene is done when its clips that don't loop have finished (the user's rule of 2026-11-10)."""
        songs_that_loop = 0
        for path in EXAMPLES:
            setlist = Setlist.read_file(path)
            for name in setlist.get_song_names():
                with self.subTest(path=path, song=name):
                    song = setlist.get_song(name)
                    songs_that_loop += song_has_a_loop(song)
                    routes = {track: Route(PORT, EXPORT_CHANNEL) for track in song.get_track_names()}
                    timeline = song_timeline(grid=SongRenderer(song, seed=SEED).render(), routes=routes)
                    player = self.start(song, routes=routes)
                    player.play_song()
                    self.clock.advance(FAR_AHEAD)
                    player.tick()
                    self.assertEqual(comparable(self.engine.pending()), comparable(timeline))
                    self.assertFalse(player.is_playing())
        self.assertGreater(songs_that_loop, 0)


def song_has_a_loop(song):
    """Return whether any clip of a song loops."""
    return any(scene.get_clip_slot(track).loops() for scene in song.get_scenes() for track in song.get_track_names() if scene.has_clip_slot(track))


def comparable(events, *, until=None):
    """Return events as the tuples two timelines are compared by, their seconds rounded past float addition's noise, leaving out the ones from a moment on."""
    return sorted((round(event.seconds, 6), event.port, event.channel, event.kind, event.number, event.value) for event in events if until is None or event.seconds < until)


class TestPlayerFollowActions(PlayerTest):

    def test_with_scene_sends_the_scene_below_a_start_when_the_scene_is_done_and_off_leaves_the_track_silent(self):
        player = self.start(player_song(follow_actions={(FIRST, BASS): FollowAction.OFF}))
        player.play_song()
        self.run_until(3 * SCENE_SECONDS)
        # The lead goes on through every scene, launching each whole scene below, which brings the bass back in the third scene through the lead's start.
        self.assertEqual(self.note_ons(PORT), [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5])
        self.assertEqual(self.note_ons(OTHER_PORT), [0.0, 1.0, 2.0, 3.0, 4.0, 5.0])

    def test_every_clip_off_ends_the_song_after_the_scene(self):
        player = self.start(player_song(follow_actions={(FIRST, LEAD): FollowAction.OFF, (FIRST, BASS): FollowAction.OFF}))
        player.play_song()
        self.run_until(3 * SCENE_SECONDS)
        self.assertEqual(self.note_ons(PORT), [0.0, 0.5, 1.0, 1.5])
        self.assertFalse(player.is_playing())

    def test_launch_together_off_starts_each_clip_from_the_clip_above_it_alone(self):
        # The bass in the first scene is "Off", so only the lead sends a start down; the second scene launches apart, so only the lead plays there, and the bass stays silent
        # until the lead's start reaches the third scene, which launches together.
        player = self.start(player_song(follow_actions={(FIRST, BASS): FollowAction.OFF}, launch_apart=(SECOND,)))
        player.play_song()
        self.run_until(SCENE_SECONDS + HALF_A_SCENE)
        self.assertEqual(player.playing_scenes(), [SECOND])
        self.assertFalse(player.is_clip_playing(scene=SECOND, track=BASS))
        self.run_until(3 * SCENE_SECONDS)
        self.assertEqual(self.note_ons(PORT), [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5])
        self.assertEqual(self.note_ons(OTHER_PORT), [0.0, 1.0, 4.0, 5.0])

    def test_a_looping_clip_does_not_hold_its_scene_and_the_scene_below_cuts_the_loop_where_it_starts(self):
        # The bass loops in the first scene, the lead doesn't: the scene is done when the lead finishes, the second scene launches whole, and the looping bass is cut there.
        player = self.start(player_song(loops={(FIRST, BASS)}))
        player.play_song()
        self.run_until(SCENE_SECONDS + HALF_A_SCENE)
        self.assertEqual(player.playing_scenes(), [SECOND])
        self.assertTrue(player.is_clip_playing(scene=SECOND, track=BASS))
        self.run_until(3 * SCENE_SECONDS)
        self.assertEqual(self.note_ons(OTHER_PORT), [0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertEqual(self.note_ons(PORT), [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5])
        self.assertFalse(player.is_playing())

    def test_a_loop_goes_on_where_nothing_below_starts_and_ends_with_the_last_scene_unless_its_advance_is_off(self):
        # Every clip of the first scene is "Off", so the scene is done and nothing below starts: the lead falls silent and the looping bass goes on alone until the human.
        player = self.start(player_song(loops={(FIRST, BASS)}, follow_actions={(FIRST, LEAD): FollowAction.OFF, (FIRST, BASS): FollowAction.OFF}))
        player.play_song()
        self.run_until(2 * SCENE_SECONDS + HALF_A_SCENE)
        self.assertEqual(player.playing_scenes(), [FIRST])
        self.assertTrue(player.is_clip_playing(scene=FIRST, track=BASS))
        self.assertFalse(player.is_clip_playing(scene=FIRST, track=LEAD))
        self.assertEqual(self.note_ons(PORT), [0.0, 0.5, 1.0, 1.5])
        # A loop in the last scene with "With Scene" ends with the scene, since its start has nowhere to go, so the song ends when the export does.
        player = self.start(player_song(loops={(THIRD, BASS)}))
        player.play_song()
        self.run_until(3 * SCENE_SECONDS + HALF_A_SCENE)
        self.assertFalse(player.is_playing())
        self.assertEqual(self.note_ons(OTHER_PORT), [0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
        # The same loop with "Off" goes on past the end, as it was told to send nothing.
        player = self.start(player_song(loops={(THIRD, BASS)}, follow_actions={(THIRD, BASS): FollowAction.OFF}))
        player.play_song()
        self.run_until(3 * SCENE_SECONDS + HALF_A_SCENE)
        self.assertTrue(player.is_clip_playing(scene=THIRD, track=BASS))

    def test_next_sends_its_start_the_moment_the_clips_own_repeats_end_cutting_the_rest_of_the_scene(self):
        # The bass's pattern is half as long as the lead's, so with Advance "Next" on the bass the second scene launches half way through the first, whole, cutting the lead.
        song = player_song(follow_actions={(FIRST, BASS): FollowAction.NEXT})
        song.get_pattern(LOW).set_steps(2)
        player = self.start(song)
        player.play_song()
        self.run_until(HALF_A_SCENE + STEP)
        self.assertEqual(player.playing_scenes(), [SECOND])
        self.run_until(3 * SCENE_SECONDS)
        # The second scene began at one second and the third at three, each as long as the lead's pattern, so the song ends at five.
        self.assertEqual(self.note_ons(PORT), [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5])
        self.assertEqual(self.note_ons(OTHER_PORT), [0.0, 1.0, 3.0])
        self.assertFalse(player.is_playing())
        # With the second scene launching apart, "Next" starts the bass below alone, and the lead plays its first scene out.
        song = player_song(follow_actions={(FIRST, BASS): FollowAction.NEXT}, launch_apart=(SECOND,))
        song.get_pattern(LOW).set_steps(2)
        player = self.start(song)
        player.play_song()
        self.run_until(HALF_A_SCENE + STEP)
        self.assertTrue(player.is_clip_playing(scene=SECOND, track=BASS))
        self.assertTrue(player.is_clip_playing(scene=FIRST, track=LEAD))

    def test_playing_a_clip_by_hand_replaces_its_tracks_play_and_the_other_tracks_go_on(self):
        # Each scene is one bar of 4/4 here, so a clip launched by hand half way through the first scene waits for the second scene's start, the next bar, and plays there instead of the second scene's own clip.
        player = self.start(player_song())
        player.play_song()
        self.run_until(HALF_A_SCENE)
        self.assertEqual(player.play_clip(scene=THIRD, track=LEAD), SCENE_SECONDS)
        self.run_until(HALF_A_SCENE + STEP)
        self.assertTrue(player.is_clip_playing(scene=FIRST, track=LEAD))
        self.run_until(SCENE_SECONDS + STEP)
        self.assertTrue(player.is_clip_playing(scene=THIRD, track=LEAD))
        self.assertTrue(player.is_clip_playing(scene=SECOND, track=BASS))
        self.run_until(3 * SCENE_SECONDS)
        # The clip played by hand finished with the second scene's bass, and sent no start of its own; the bass's start launched the third scene together.
        self.assertEqual(self.note_ons(PORT), [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5])
        self.assertEqual(self.note_ons(OTHER_PORT), [0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertFalse(player.is_playing())

    def test_a_launch_by_hand_waits_for_the_next_bar_and_a_scene_shorter_than_a_bar_hands_over_at_its_end(self):
        player = self.start(player_song(), time_signature=TWO_FOUR)
        # In 2/4 a bar is one second, half a scene, so a scene launched at a quarter of a second starts at one.
        player.play_song()
        self.run_until(STEP)
        self.assertEqual(player.play_scene(THIRD), HALF_A_SCENE)
        self.run_until(HALF_A_SCENE + STEP)
        self.assertEqual(player.playing_scenes(), [THIRD])
        self.assertEqual(self.note_ons(PORT), [0.0, 0.5, 1.0])
        self.assertEqual(self.note_ons(OTHER_PORT), [0.0, 1.0])
        # With nothing playing, a launch is at once.
        player.stop_all()
        self.assertEqual(player.play_scene(FIRST), self.engine.elapsed())
        # A scene lasting less than a bar hands over at its end: the short song's scenes last half a second in 1/1, where a bar is two.
        short = self.start(player_song(steps=1), time_signature=ONE_ONE)
        short.play_song()
        self.run_until(STEP)
        self.assertEqual(short.play_scene(THIRD), HALF_A_SCENE / 2)

    def test_stopping_a_clip_silences_its_track_at_once_and_stopping_all_silences_everything(self):
        player = self.start(player_song())
        player.play_song()
        self.run_until(0.1)
        self.assertTrue(player.is_track_sounding(LEAD))
        player.stop_clip(LEAD)
        self.assertFalse(player.is_clip_playing(scene=FIRST, track=LEAD))
        # The lead is silent until the second scene, which the bass's follow action launches, brings it back.
        self.assertEqual([seconds for seconds in self.pending_ons(LEAD) if seconds < SCENE_SECONDS], [])
        self.assertEqual([note for note in self.engine.sounding() if note[0] == PORT], [])
        self.assertTrue(player.is_track_sounding(BASS))
        self.run_until(HALF_A_SCENE)
        self.assertTrue(player.is_playing())
        player.stop_all()
        self.assertFalse(player.is_playing())
        self.assertEqual(self.engine.pending(), [])

    def test_the_lights_say_which_scene_and_clips_play_and_where_the_song_is(self):
        player = self.start(player_song())
        self.assertFalse(player.is_playing())
        self.assertIsNone(player.song_position())
        player.play_song()
        self.run_until(SCENE_SECONDS + HALF_A_SCENE)
        self.assertEqual(player.playing_scenes(), [SECOND])
        self.assertTrue(player.is_clip_playing(scene=SECOND, track=BASS))
        self.assertFalse(player.is_clip_playing(scene=FIRST, track=BASS))
        self.assertAlmostEqual(player.scene_elapsed(SECOND), HALF_A_SCENE)
        self.assertAlmostEqual(player.song_position(), SCENE_SECONDS + HALF_A_SCENE)
        self.assertEqual(player.repeats_left(scene=SECOND, track=LEAD), 1)
        self.assertAlmostEqual(player.clip_elapsed(scene=SECOND, track=LEAD), HALF_A_SCENE)
        self.assertIsNone(player.clip_elapsed(scene=FIRST, track=LEAD))


class TestEngineSilence(unittest.TestCase):

    def test_silence_sends_every_note_off_then_all_notes_off_and_all_sound_off_on_each_channel_given(self):
        output = RecordingOutput()
        engine = PlaybackEngine(clock=SteppedClock(), outputs={PORT: output})
        engine.silence(channels=[(PORT, EXPORT_CHANNEL)])
        kinds = [data[0] & KIND_MASK for _, data in output.sent]
        self.assertEqual(kinds.count(NOTE_OFF), MAX_MIDI_NUMBER - MIN_MIDI_NUMBER + 1)
        self.assertEqual([data for _, data in output.sent][-2:], [[CONTROL_CHANGE | EXPORT_CHANNEL, ALL_NOTES_OFF, NO_VELOCITY], [CONTROL_CHANGE | EXPORT_CHANNEL, ALL_SOUND_OFF, NO_VELOCITY]])
