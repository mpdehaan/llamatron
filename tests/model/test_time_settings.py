# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The one list of times every time setting chooses from: an arp's Step, a drift's Every and a shape's Over, each a length in whole notes or a count of bars that the song's time signature measures."""

import unittest

from llamatron.engine.generators import arp as arp_plugin, drift as drift_plugin
from llamatron.engine.generators.arp.model import ArpSetting
from llamatron.engine.generators.drift.model import DriftSetting
from llamatron.engine.generators.drift.play import DriftPlay
from llamatron.math.rational import Rational
from llamatron.model.file.checks import Bars, in_whole_notes, time_length
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.file.song_file_error import SongFileError
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import ClipSlotSetting, PatternSetting, SceneSetting, Section, Shape, shape_setting, ShapePart, ShapeThen, SongSetting
from llamatron.tui.screens.generators.time_field import time_field
from llamatron.user_strings import labels
from tests.engine.generators.test_drift import drifting
from tests.playback import test_registers
from tests.playback.test_registers import pattern, song
from tests.playback.test_shapes import notes, one_scene
from tests.support.rendering import setlist_from_data, song_from_data

TWO_BARS = '2 bars'
THREE_FOUR = '3/4'
WALTZ_BAR = Rational(3, 4)
SEED = 3
CHORD = '3'
ARP = 'up'
ARPEGGIATED = 'arpeggiated'
STEPS = 4


class TestTheList(unittest.TestCase):

    def test_each_triplet_follows_its_straight_value_and_then_the_dotted_one(self):
        for straight, triplet, dotted in (('1/16', '1/24', '3/32'), ('1/8', '1/12', '3/16')):
            place = file_format.TIME_CHOICES.index(straight)
            self.assertEqual(file_format.TIME_CHOICES[place + 1:place + 3], [triplet, dotted])

    def test_the_straight_lengths_get_longer_and_the_list_ends_in_bars(self):
        lengths = [time_length(time) for time in file_format.TIME_CHOICES if not isinstance(time_length(time), Bars) and time not in labels.MSG_TIME_NAMES]
        self.assertEqual(lengths, sorted(lengths))
        self.assertEqual([time_length(time).count for time in file_format.TIME_CHOICES if isinstance(time_length(time), Bars)], [1, 2, 4, 8, 16])

    def test_every_dotted_and_triplet_value_has_a_name(self):
        for written, name in labels.MSG_TIME_NAMES.items():
            self.assertIn(written, file_format.TIME_CHOICES, name)


class TestTimeLength(unittest.TestCase):

    def test_bars_and_lengths(self):
        self.assertEqual(time_length(file_format.ONE_BAR_WRITTEN), Bars(1))
        self.assertEqual(time_length(TWO_BARS), Bars(2))
        self.assertEqual(time_length('3/32'), Rational(3, 32))
        self.assertEqual(time_length(2), Rational(2))

    def test_a_bar_is_the_time_signatures(self):
        self.assertEqual(in_whole_notes(time=TWO_BARS, bar=WALTZ_BAR), Rational(3, 2))
        self.assertEqual(in_whole_notes(time='1/8', bar=WALTZ_BAR), Rational(1, 8))

    def test_what_is_refused(self):
        for wrong in ('0 bars', 'two bars', 'bars', 0, '-1/8', '2 beats', True):
            with self.subTest(wrong=wrong), self.assertRaises(InvalidValue):
                time_length(wrong)


class TestBarsInTheRender(unittest.TestCase):
    """A setting in bars follows the song's time signature."""

    def test_a_drifts_every_in_bars(self):
        data = drifting(drift={DriftSetting.EVERY: TWO_BARS})
        data[SongSetting.TIME_SIGNATURE] = THREE_FOUR
        play = DriftPlay(song=song_from_data(data), seed=SEED)
        self.assertEqual(play.every(next(iter(data[drift_plugin.SECTION]))), Rational(3, 2))

    def test_a_shapes_over_in_bars(self):
        ramp = {
            shape_setting(shape=Shape.DENSITY, part=ShapePart.START): 0, shape_setting(shape=Shape.DENSITY, part=ShapePart.END): 100,
            shape_setting(shape=Shape.DENSITY, part=ShapePart.OVER): file_format.ONE_BAR_WRITTEN, shape_setting(shape=Shape.DENSITY, part=ShapePart.THEN): ShapeThen.REPEAT,
        }
        played = notes(one_scene(repeat=2, scene=ramp))
        # Each bar ramps from nothing again, so the two bars play alike.
        first = [start for start, _, _, _ in played if start < 1]
        second = [start - 1 for start, _, _, _ in played if start >= 1]
        self.assertEqual(first, second)

    def test_an_arps_step_in_bars(self):
        data = song(
            patterns={test_registers.X: dict(pattern(STEPS, chord=[CHORD] * STEPS), **{PatternSetting.STEP_SIZE: '1/4'})},
            scenes=[{SceneSetting.TRACKS: {test_registers.LEAD: {ClipSlotSetting.PATTERN: test_registers.X, ClipSlotSetting.CHAINS: [ARPEGGIATED]}}}],
        )
        data[arp_plugin.SECTION] = {ARP: {ArpSetting.STEP: file_format.ONE_BAR_WRITTEN}}
        data[Section.CHAINS] = {ARPEGGIATED: [{arp_plugin.NAME: ARP}]}
        # A step as long as a bar is longer than each quarter-note chord, so each chord plays one note, where a sixteenth plays four.
        self.assertEqual(len(notes(data)), STEPS)
        data[arp_plugin.SECTION][ARP][ArpSetting.STEP] = '1/16'
        self.assertEqual(len(notes(data)), STEPS * STEPS)

    def test_a_wrong_time_in_a_file_is_refused(self):
        data = drifting(drift={DriftSetting.EVERY: 'soon'})
        with self.assertRaises(SongFileError):
            setlist_from_data(data)


class TestTimeField(unittest.TestCase):
    """The field every time setting shares."""

    LABEL = 'Every'
    BLANK = '(blank)'
    TYPED = 3

    def field(self, *, written, first=BLANK):
        stored = []
        return time_field(page=None, label=self.LABEL, written=written, first=first, store=stored.append), stored

    def test_first_stands_for_blank_and_then_the_list(self):
        field, stored = self.field(written=None)
        self.assertEqual(field.choices, [self.BLANK, *file_format.TIME_CHOICES])
        self.assertEqual(field.text(), self.BLANK)
        field.set(self.BLANK)
        self.assertEqual(stored, [None])

    def test_a_first_that_is_in_the_list_is_not_offered_twice(self):
        field, _ = self.field(written=None, first=file_format.ONE_BAR_WRITTEN)
        self.assertEqual(field.choices.count(file_format.ONE_BAR_WRITTEN), 1)

    def test_a_value_outside_the_list_is_kept_and_offered_last(self):
        field, _ = self.field(written=self.TYPED)
        self.assertEqual(field.choices[-1], str(self.TYPED))
        self.assertEqual(field.text(), str(self.TYPED))

    def test_a_dotted_length_shows_its_name(self):
        field, stored = self.field(written='3/32')
        self.assertEqual(field.text(), labels.MSG_TIME_NAMES['3/32'])
        field.set('3/16')
        self.assertEqual(stored, ['3/16'])
