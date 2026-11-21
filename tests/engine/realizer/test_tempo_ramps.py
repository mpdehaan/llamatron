# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A scene's tempo ramps: the tempo of each step, the ramps across a scene's repeats, and every length and export that has to agree about them."""

from fractions import Fraction
import mido
import os
import unittest

from llamatron.engine.clips.row_clock import RowClock, seconds_per_whole
from llamatron.engine.realizer.song_realizer import SongRealizer
from llamatron.engine.realizer.tempo_ramps import ramped_tempos
from llamatron.exporters.midi_arrangement import MidiSong
from llamatron.model.objects.scene import TempoRamp
from llamatron.model.schema.file_format import ClipSlotSetting, SceneSetting, SongSetting
from llamatron.realtime.render_process import timeline
from llamatron.realtime.render_process.timeline import Route, song_timeline
from tests.support import song_testing
from tests.support.rendering import render_data, song_from_data
from tests.support.song_testing import with_parts

A = 'a'
# How many bars a scene of the tests' data lasts, which is its lead clip's repeat of the one-bar pattern.
BARS = 'bars'
# The MIDI messages the tests read from a written file.
NOTE_ON_MESSAGE = 'note_on'
SET_TEMPO_MESSAGE = 'set_tempo'
FIRST_CHANNEL = 0
PORT = 'port'
SONG_NAME = 'ramps'
# The song's tempo in the tests' data, and tempos a ramp starts from and reaches.
BASE = 120
SLOW = 100
FAST = 140
# A bar of four four and the step the unit tests ramp by, a quarter note, in whole notes, and those steps in a bar. A song's own step is a sixteenth.
BAR = Fraction(1)
BEAT = Fraction(1, 4)
BEATS_IN_A_BAR = 4
SIXTEENTH = Fraction(1, 16)
SIXTEENTHS_IN_A_BAR = 16
# The pattern a of the tests' data lasts one bar, so a clip's repeat is its bars.
EIGHT_BARS = 8
TWO_BARS = 2
FOUR_BARS = 4
# How close seconds worked out two ways must be: a MIDI file keeps a tempo as whole microseconds a beat.
CLOSE = 2


def tempos(*, length=EIGHT_BARS * BAR, ramp_in=None, ramp_out=None):
    return ramped_tempos(base=BASE, ramp_in=ramp_in, ramp_out=ramp_out, length=length, bar=BAR, step=BEAT)


def tempo_at(*, changes, time):
    """Return the tempo a list of changes gives a time."""
    return [change.tempo for change in changes if change.time <= time][-1]


def data_with(*scenes):
    """Return a song's data with the scenes given, each a dictionary of a scene's settings, whose lead plays the one-bar pattern for the scene's bars."""
    written = []
    for settings in scenes:
        settings = dict(settings)
        bars = settings.pop(BARS)
        written.append({**settings, SceneSetting.TRACKS: {song_testing.LEAD: {ClipSlotSetting.PATTERN: A, ClipSlotSetting.REPEAT: bars}}})
    return with_parts(scenes=written)


class TestTheTempoOfEachBeat(unittest.TestCase):

    def test_a_ramp_in_starts_at_its_start_and_arrives_on_the_beat_after_its_bars(self):
        changes = tempos(ramp_in=TempoRamp(SLOW, None, TWO_BARS))
        # 100 to the scene's 120 over 8 beats, 2.5 a beat.
        self.assertEqual([change.tempo for change in changes], [100.0, 102.5, 105.0, 107.5, 110.0, 112.5, 115.0, 117.5, 120.0])
        self.assertEqual([change.time for change in changes], [beat * BEAT for beat in range(TWO_BARS * BEATS_IN_A_BAR + 1)])

    def test_a_ramp_out_is_measured_back_from_the_end_and_is_at_its_end_on_the_last_beat(self):
        changes = tempos(ramp_out=TempoRamp(None, SLOW, TWO_BARS))
        self.assertEqual(changes[0], (0, float(BASE)))
        self.assertEqual(changes[1].time, (EIGHT_BARS - TWO_BARS) * BAR)
        self.assertEqual(changes[-1], (EIGHT_BARS * BAR - BEAT, float(SLOW)))
        self.assertEqual(len(changes), 1 + TWO_BARS * BEATS_IN_A_BAR)

    def test_between_the_ramps_the_tempo_is_the_scenes(self):
        changes = tempos(ramp_in=TempoRamp(SLOW, None, TWO_BARS), ramp_out=TempoRamp(None, FAST, TWO_BARS))
        for bar in range(TWO_BARS, EIGHT_BARS - TWO_BARS):
            self.assertEqual(tempo_at(changes=changes, time=bar * BAR), BASE)
        self.assertEqual(changes[-1].tempo, FAST)

    def test_where_the_ramps_overlap_the_ramp_in_wins(self):
        changes = tempos(length=FOUR_BARS * BAR, ramp_in=TempoRamp(SLOW, SLOW, FOUR_BARS - 1), ramp_out=TempoRamp(FAST, FAST, FOUR_BARS))
        self.assertEqual(changes, [(0, float(SLOW)), ((FOUR_BARS - 1) * BAR, float(FAST))])

    def test_a_ramp_over_the_whole_scene_never_holds_a_tempo_for_more_than_a_step(self):
        changes = tempos(ramp_in=TempoRamp(None, FAST, EIGHT_BARS))
        self.assertEqual(len(changes), EIGHT_BARS * BEATS_IN_A_BAR)
        self.assertEqual(changes[0].tempo, BASE)
        self.assertLess(changes[-1].tempo, FAST)
        self.assertEqual(tempo_at(changes=changes, time=EIGHT_BARS * BAR / 2), (BASE + FAST) / 2)

    def test_a_ramp_longer_than_the_scene_is_cut_where_the_scene_ends(self):
        changes = tempos(length=TWO_BARS * BAR, ramp_in=TempoRamp(SLOW, FAST, FOUR_BARS))
        self.assertEqual(changes[-1], (TWO_BARS * BAR - BEAT, 100 + 40 * 7 / 16))

    def test_a_ramp_that_goes_nowhere_changes_nothing(self):
        self.assertEqual(tempos(ramp_in=TempoRamp(BASE, BASE, TWO_BARS)), [(0, float(BASE))])


class TestTheRowClock(unittest.TestCase):

    def test_a_row_with_one_tempo_is_one_multiplication(self):
        clock = RowClock([(Fraction(0), BASE)])
        self.assertTrue(clock.has_one_tempo())
        self.assertEqual(clock.seconds_at(Fraction(3, 2)), 1.5 * seconds_per_whole(BASE))
        self.assertEqual(clock.whole_at(3.0), 3.0 / seconds_per_whole(BASE))
        self.assertEqual(clock.seconds_per_whole_at(1.0), seconds_per_whole(BASE))

    def test_a_row_with_changes_adds_each_stretch_at_its_own_tempo(self):
        clock = RowClock([(Fraction(0), 120), (Fraction(1), 60)])
        self.assertFalse(clock.has_one_tempo())
        # A whole note at 120 lasts 2 seconds, and at 60 lasts 4.
        self.assertEqual([clock.seconds_at(time) for time in (Fraction(1, 2), Fraction(1), Fraction(2))], [1.0, 2.0, 6.0])
        self.assertEqual([clock.whole_at(seconds) for seconds in (1.0, 2.0, 6.0)], [0.5, 1.0, 2.0])
        self.assertEqual((clock.seconds_per_whole_at(1.0), clock.seconds_per_whole_at(3.0)), (2.0, 4.0))


class TestARampInASong(unittest.TestCase):

    def test_a_scene_with_no_ramp_keeps_one_tempo(self):
        grid = render_data(data_with({BARS: TWO_BARS}))
        row = grid.get_rows()[0]
        self.assertEqual((row.get_tempo(), row.get_tempo_changes()), (None, ()))
        self.assertEqual(grid.tempos_in(row), [(0, BASE)])

    def test_the_rows_hold_the_tempo_of_each_beat(self):
        grid = render_data(data_with({BARS: TWO_BARS, SceneSetting.TEMPO_IN_START: SLOW, SceneSetting.TEMPO_IN_OVER: 1}))
        # The tempo moves at every step of the song, a sixteenth: 16 steps of 1.25 from 100, then the scene's 120.
        self.assertEqual(grid.tempos_in(grid.get_rows()[0]), [(step * SIXTEENTH, 100 + 1.25 * step) for step in range(SIXTEENTHS_IN_A_BAR + 1)])

    def test_a_ramp_with_no_bars_is_no_ramp(self):
        grid = render_data(data_with({BARS: TWO_BARS, SceneSetting.TEMPO_IN_START: SLOW, SceneSetting.TEMPO_IN_END: FAST}))
        self.assertEqual(grid.tempos_in(grid.get_rows()[0]), [(0, BASE)])

    def test_a_ramp_runs_across_every_repeat_of_its_scene_once(self):
        grid = render_data(data_with({BARS: TWO_BARS, SceneSetting.REPEAT: 2, SceneSetting.TEMPO_IN_END: FAST, SceneSetting.TEMPO_IN_OVER: FOUR_BARS}))
        first, second = grid.get_rows()
        # Four bars in all, 64 steps of 0.3125: the second repeat goes on from where the first stopped.
        self.assertEqual(grid.tempo_at(first), 120.0)
        self.assertEqual(grid.tempos_in(first)[-1], (TWO_BARS * BAR - SIXTEENTH, 129.6875))
        self.assertEqual(grid.tempo_at(second), 130.0)
        self.assertEqual(grid.tempos_in(second)[-1], (TWO_BARS * BAR - SIXTEENTH, 139.6875))

    def test_a_ramp_has_no_effect_after_its_scene(self):
        grid = render_data(data_with({BARS: TWO_BARS, SceneSetting.TEMPO_OUT_END: SLOW, SceneSetting.TEMPO_OUT_OVER: TWO_BARS}, {BARS: TWO_BARS}))
        after = grid.get_rows()[1]
        self.assertEqual(grid.tempos_in(after), [(0, BASE)])

    def test_a_blank_start_and_end_are_the_scenes_own_tempo_where_it_has_one(self):
        grid = render_data(data_with({BARS: TWO_BARS, SceneSetting.TEMPO: SLOW, SceneSetting.TEMPO_OUT_END: FAST, SceneSetting.TEMPO_OUT_OVER: 1}))
        changes = grid.tempos_in(grid.get_rows()[0])
        self.assertEqual((changes[0], changes[-1]), ((0, SLOW), (TWO_BARS * BAR - SIXTEENTH, float(FAST))))


class TestLengthsAgree(unittest.TestCase):
    """The song's length is one number however it is asked for: the estimate the pages show, the real-time timeline and the MIDI file."""

    def scenes(self):
        return data_with(
            {BARS: FOUR_BARS, SceneSetting.TEMPO_IN_START: SLOW, SceneSetting.TEMPO_IN_OVER: TWO_BARS},
            {BARS: TWO_BARS},
            {BARS: FOUR_BARS, SceneSetting.REPEAT: 2, SceneSetting.TEMPO_IN_END: FAST, SceneSetting.TEMPO_IN_OVER: EIGHT_BARS, SceneSetting.TEMPO_OUT_END: SLOW, SceneSetting.TEMPO_OUT_OVER: 1},
        )

    def test_the_estimate_the_timeline_and_the_midi_file_last_the_same(self):
        song = song_from_data(self.scenes())
        estimates = SongRealizer(song).estimate()
        estimated = sum(float(estimate.seconds) for estimate in estimates)
        grid = SongRealizer(song).render()
        by_clock = sum(grid.clock_of(row).seconds_at(grid.row_length(row)) for row in grid.get_rows())
        self.assertAlmostEqual(estimated, by_clock)
        midi = MidiSong(directory=os.curdir, grid=grid, name=SONG_NAME).midi_file()
        self.assertAlmostEqual(midi.length, estimated, places=CLOSE)
        # A ramp from slow makes the song longer than it would be at the song's tempo throughout.
        bars = sum(float(grid.row_length(row)) for row in grid.get_rows())
        self.assertNotAlmostEqual(estimated, bars * seconds_per_whole(BASE), places=CLOSE)

    def test_a_clips_seconds_are_measured_by_its_scenes_ramp(self):
        song = song_from_data(self.scenes())
        first = SongRealizer(song).estimate()[0]
        self.assertAlmostEqual(float(first.clip_seconds[song_testing.LEAD]), float(first.seconds))
        # Two bars from 100 to 120, a sixteenth at a time, then two bars at 120.
        steps = TWO_BARS * SIXTEENTHS_IN_A_BAR
        ramp = sum(float(SIXTEENTH) * seconds_per_whole(SLOW + (BASE - SLOW) * step / steps) for step in range(steps))
        self.assertAlmostEqual(float(first.seconds), ramp + TWO_BARS * seconds_per_whole(BASE))

    def test_every_note_of_the_timeline_is_where_the_midi_file_has_it(self):
        song = song_from_data(self.scenes())
        grid = SongRealizer(song).render()
        events = song_timeline(grid=grid, routes={song_testing.LEAD: Route(PORT, FIRST_CHANNEL, None)})
        midi = MidiSong(directory=os.curdir, grid=grid, name=SONG_NAME).midi_file()
        seconds = 0.0
        ons = []
        for message in midi:
            seconds += message.time
            if message.type == NOTE_ON_MESSAGE and message.velocity:
                ons.append(seconds)
        timeline_ons = sorted(event.seconds for event in events if event.kind == timeline.NOTE_ON)
        self.assertEqual(len(ons), len(timeline_ons))
        for written, played in zip(sorted(ons), timeline_ons):
            self.assertAlmostEqual(written, played, places=CLOSE)

    def test_the_midi_file_changes_tempo_at_each_step_of_a_ramp(self):
        grid = render_data(data_with({BARS: TWO_BARS, SceneSetting.TEMPO_IN_START: SLOW, SceneSetting.TEMPO_IN_OVER: 1}))
        midi = MidiSong(directory=os.curdir, grid=grid, name=SONG_NAME).midi_file()
        written = [round(mido.tempo2bpm(message.tempo), 2) for message in midi.tracks[0] if message.type == SET_TEMPO_MESSAGE]
        self.assertEqual(written, [100 + 1.25 * step for step in range(SIXTEENTHS_IN_A_BAR + 1)])


class TestTheSongsTempo(unittest.TestCase):

    def test_the_songs_tempo_is_what_a_blank_ramp_part_takes(self):
        data = data_with({BARS: TWO_BARS, SceneSetting.TEMPO_IN_END: FAST, SceneSetting.TEMPO_IN_OVER: TWO_BARS})
        data[SongSetting.TEMPO] = SLOW
        grid = render_data(data)
        self.assertEqual(grid.tempo_at(grid.get_rows()[0]), SLOW)
