# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Phrasing: a tune's lines end early for a breath as the clip plays, the shorter lines sooner, a note of some lines comes an eighth early, a kind of section says its own, and a note marked whole in the pattern is left as written."""

import unittest

from llamatron.engine.generators import phrasing as phrasing_plugin
from llamatron.engine.generators.phrasing import generator as phrasing, settings as phrasing_settings
from llamatron.engine.generators.phrasing.settings import PhrasingSetting, PhrasingSettings
from llamatron.engine.timing.timing import timed_events
from llamatron.math.rational import Rational
from llamatron.model.schema.file_format import ClipSlotSetting, PatternSetting, Row, SceneSetting, Section
from tests.playback import test_registers
from tests.playback.test_registers import pattern, song
from tests.support.rendering import render_data

TUNE = 'tune'
DELIVERY = 'delivery'
CHAIN = 'sung'
EIGHTH = Rational(1, 8)
QUARTER = Rational(1, 4)
HALF = Rational(1, 2)
EIGHTH_STEP = '1/8'
BAR = Rational(1)
# A tune of four lines of two bars, written in eighths.
STEPS_IN_LINE = 16
LINES = 4
STEPS = STEPS_IN_LINE * LINES
LINE = 2 * BAR
# A line that ends on a half note: twelve eighths, then a note tied through the line's last four steps.
MOVING_STEPS = 12
HELD_STEPS = STEPS_IN_LINE - MOVING_STEPS
NOTES_IN_LINE = MOVING_STEPS + 1
LINE_ENDING_HELD = {Row.DEGREE: ([1] * NOTES_IN_LINE + [None] * (HELD_STEPS - 1)) * LINES, Row.TIE: ([False] * NOTES_IN_LINE + [True] * (HELD_STEPS - 1)) * LINES}
# Where the held note of the first line starts.
HELD_NOTE_START = MOVING_STEPS * EIGHTH
# A line of notes an eighth long with an eighth of rest after each, on one pitch and on two in turn.
ONE_PITCH_WITH_RESTS = {Row.DEGREE: [1, None] * (STEPS // 2)}
TWO_PITCHES_WITH_RESTS = {Row.DEGREE: [1, None, 2, None] * (STEPS // 4)}
# A Phrasing that changes one thing only starts from one that changes nothing.
PLAIN = {PhrasingSetting.BREATH: phrasing.NO_BREATH, PhrasingSetting.RISE_AND_FALL: phrasing.NO_RISE, PhrasingSetting.NOTES: phrasing.NOTES_AS_WRITTEN}
START = 0
LENGTH = 1
MIDI = 2
VELOCITY = 3


def only(*, changed=None):
    """Return the settings of a Phrasing that changes nothing but the settings given."""
    return {**PLAIN, **(changed or {})}


def phrased_data(*, settings, rows=None, steps=STEPS):
    """Return a song's data whose lead plays the tune through a chain of one Phrasing."""
    tune = pattern(steps, **(rows or {}))
    tune[PatternSetting.STEP_SIZE] = EIGHTH_STEP
    scene = {SceneSetting.TRACKS: {test_registers.LEAD: {ClipSlotSetting.PATTERN: TUNE, ClipSlotSetting.CHAINS: [CHAIN]}}}
    data = song(patterns={TUNE: tune}, scenes=[scene])
    data[phrasing_plugin.SECTION] = {DELIVERY: settings}
    data[Section.CHAINS] = {CHAIN: [{phrasing_plugin.NAME: DELIVERY}]}
    return data


def heard(data):
    """Return each note the lead plays as (start, length, pitch, velocity), times in whole notes, in time order."""
    grid = render_data(data)
    clip = grid.get_clip(row=grid.get_rows()[0], column=grid.get_columns()[0])
    return sorted((start, end - start, midi, velocity) for start, end, midi, velocity in timed_events(clip=clip, scale=clip.get_scale())[0])


def line_ends(data):
    """Return how long before its end each line's last note stops."""
    notes = heard(data)
    ends = []
    for line in range(LINES):
        last = max(note[START] + note[LENGTH] for note in notes if line * LINE <= note[START] < (line + 1) * LINE)
        ends.append((line + 1) * LINE - last)
    return ends


def first_line(notes):
    return [note for note in notes if note[START] < LINE]


class TestPhrasingBreath(unittest.TestCase):

    def test_a_quick_breath_takes_an_eighth_off_each_lines_last_note_and_a_deep_one_a_quarter(self):
        self.assertEqual(line_ends(phrased_data(settings=only(changed={PhrasingSetting.BREATH: phrasing.QUICK_BREATH}), rows=LINE_ENDING_HELD)), [EIGHTH] * LINES)
        self.assertEqual(line_ends(phrased_data(settings=only(changed={PhrasingSetting.BREATH: phrasing.DEEP_BREATH}), rows=LINE_ENDING_HELD)), [QUARTER] * LINES)

    def test_no_breath_leaves_every_line_as_long_as_written(self):
        self.assertEqual(line_ends(phrased_data(settings=only(), rows=LINE_ENDING_HELD)), [0] * LINES)

    def test_no_note_is_left_out_or_moved(self):
        written = heard(phrased_data(settings=only(), rows=LINE_ENDING_HELD))
        breathing = heard(phrased_data(settings=only(changed={PhrasingSetting.BREATH: phrasing.DEEP_BREATH}), rows=LINE_ENDING_HELD))
        self.assertEqual([note[START] for note in breathing], [note[START] for note in written])

    def test_a_breath_takes_no_more_than_half_of_the_note_it_shortens(self):
        # Every note of the tune is an eighth, so a deep breath, a quarter, can take only a sixteenth.
        self.assertEqual(line_ends(phrased_data(settings=only(changed={PhrasingSetting.BREATH: phrasing.DEEP_BREATH}))), [EIGHTH / 2] * LINES)

    def test_only_a_lines_last_note_is_shortened(self):
        notes = heard(phrased_data(settings=only(changed={PhrasingSetting.BREATH: phrasing.DEEP_BREATH}), rows=LINE_ENDING_HELD))
        self.assertEqual([note[LENGTH] for note in first_line(notes)], [EIGHTH] * MOVING_STEPS + [HALF - QUARTER])

    def test_where_the_tune_already_rests_nothing_is_cut(self):
        # Each line's last two steps are rests: a quarter of silence, as much as a deep breath.
        resting = {Row.DEGREE: ([1] * (STEPS_IN_LINE - 2) + [None] * 2) * LINES}
        self.assertEqual(line_ends(phrased_data(settings=only(changed={PhrasingSetting.BREATH: phrasing.DEEP_BREATH}), rows=resting)), [QUARTER] * LINES)

    def test_a_line_of_one_bar_breathes_every_bar(self):
        notes = heard(phrased_data(settings=only(changed={PhrasingSetting.BREATH: phrasing.QUICK_BREATH, PhrasingSetting.LINE_BARS: 1})))
        shortened = [note[START] for note in notes if note[LENGTH] < EIGHTH]
        self.assertEqual(shortened, [bar * BAR + BAR - EIGHTH for bar in range(2 * LINES)])

    def test_a_note_that_sounds_on_into_the_next_line_is_left(self):
        # The first line's last note is tied through the first step of the second line.
        degrees = [1] * STEPS_IN_LINE + [None] + [1] * (STEPS - STEPS_IN_LINE - 1)
        ties = [False] * STEPS_IN_LINE + [True] + [False] * (STEPS - STEPS_IN_LINE - 1)
        notes = heard(phrased_data(settings=only(changed={PhrasingSetting.BREATH: phrasing.DEEP_BREATH}), rows={Row.DEGREE: degrees, Row.TIE: ties}))
        crossing = [note for note in notes if note[START] == LINE - EIGHTH]
        self.assertEqual([note[LENGTH] for note in crossing], [QUARTER])


class TestPhrasingRiseAndFall(unittest.TestCase):

    def loudness(self, rise):
        return heard(phrased_data(settings=only(changed={PhrasingSetting.RISE_AND_FALL: rise}), rows=LINE_ENDING_HELD))

    def test_no_rise_leaves_every_note_as_loud_as_written(self):
        self.assertEqual(len({note[VELOCITY] for note in self.loudness(phrasing.NO_RISE)}), 1)

    def test_a_lines_main_note_is_its_long_note_late_in_the_line_and_is_as_loud_as_written(self):
        written = self.loudness(phrasing.NO_RISE)[0][VELOCITY]
        line = first_line(self.loudness(phrasing.LITTLE_RISE))
        main = [note for note in line if note[START] == HELD_NOTE_START]
        self.assertEqual([note[VELOCITY] for note in main], [written])
        self.assertTrue(all(note[VELOCITY] < written for note in line if note[START] != HELD_NOTE_START))

    def test_a_line_grows_toward_its_main_note(self):
        line = first_line(self.loudness(phrasing.LITTLE_RISE))
        # The notes of the second bar, which starts on a bar line that is louder by itself, climb to the main note.
        climbing = [note[VELOCITY] for note in line if BAR < note[START] <= HELD_NOTE_START]
        self.assertEqual(climbing, sorted(climbing))
        self.assertLess(line[1][VELOCITY], line[-2][VELOCITY])

    def test_a_lot_rises_further_than_a_little(self):
        little = first_line(self.loudness(phrasing.LITTLE_RISE))
        much = first_line(self.loudness(phrasing.BIG_RISE))
        self.assertLess(much[1][VELOCITY], little[1][VELOCITY])
        self.assertLess(phrasing.RISE_DEPTHS[phrasing.LITTLE_RISE], phrasing.RISE_DEPTHS[phrasing.BIG_RISE])

    def test_the_notes_after_the_main_note_fall_away_and_the_last_is_the_softest(self):
        # Each line's long note comes in the middle of its second bar and four eighths follow it.
        degrees = ([1] * 9 + [None] * 3 + [1] * 4) * LINES
        ties = ([False] * 9 + [True] * 3 + [False] * 4) * LINES
        line = first_line(heard(phrased_data(settings=only(changed={PhrasingSetting.RISE_AND_FALL: phrasing.BIG_RISE}), rows={Row.DEGREE: degrees, Row.TIE: ties})))
        falling = [note[VELOCITY] for note in line if note[START] >= BAR]
        self.assertEqual(falling, sorted(falling, reverse=True))
        self.assertEqual(min(note[VELOCITY] for note in line), line[-1][VELOCITY])

    def test_no_note_starts_or_ends_anywhere_else(self):
        timed = [(note[START], note[LENGTH]) for note in self.loudness(phrasing.BIG_RISE)]
        self.assertEqual(timed, [(note[START], note[LENGTH]) for note in self.loudness(phrasing.NO_RISE)])


class TestPhrasingNotes(unittest.TestCase):

    def test_choppy_halves_a_short_note_and_takes_an_eighth_off_a_long_one(self):
        line = first_line(heard(phrased_data(settings=only(changed={PhrasingSetting.NOTES: phrasing.CHOPPY_NOTES}), rows=LINE_ENDING_HELD)))
        self.assertEqual([note[LENGTH] for note in line], [EIGHTH / 2] * MOVING_STEPS + [HALF - EIGHTH])

    def test_flowing_holds_each_note_until_the_next_starts(self):
        line = first_line(heard(phrased_data(settings=only(changed={PhrasingSetting.NOTES: phrasing.FLOWING_NOTES}), rows=TWO_PITCHES_WITH_RESTS)))
        self.assertEqual([note[LENGTH] for note in line[:-1]], [QUARTER] * (len(line) - 1))

    def test_flowing_leaves_a_lines_last_note_as_written(self):
        line = first_line(heard(phrased_data(settings=only(changed={PhrasingSetting.NOTES: phrasing.FLOWING_NOTES}), rows=TWO_PITCHES_WITH_RESTS)))
        self.assertEqual(line[-1][LENGTH], EIGHTH)

    def test_flowing_stops_short_of_a_note_of_the_same_pitch_so_that_it_is_struck_again(self):
        line = first_line(heard(phrased_data(settings=only(changed={PhrasingSetting.NOTES: phrasing.FLOWING_NOTES}), rows=ONE_PITCH_WITH_RESTS)))
        self.assertEqual([note[LENGTH] for note in line[:-1]], [QUARTER - phrasing.GAP_BEFORE_SAME_PITCH] * (len(line) - 1))

    def test_as_written_changes_no_note(self):
        self.assertEqual({note[LENGTH] for note in heard(phrased_data(settings=only(), rows=ONE_PITCH_WITH_RESTS))}, {EIGHTH})

    def test_the_same_settings_always_play_the_same(self):
        self.assertEqual(heard(phrased_data(settings={})), heard(phrased_data(settings={})))


class TestPhrasingSettings(unittest.TestCase):

    def test_a_new_one_starts_with_lines_of_two_bars_a_quick_breath_a_little_rise_and_notes_as_written(self):
        settings = PhrasingSettings.new()
        self.assertEqual(settings.get_own(PhrasingSetting.LINE_BARS), phrasing_settings.DEFAULT_LINE_BARS)
        self.assertEqual(settings.get_own(PhrasingSetting.BREATH), phrasing.QUICK_BREATH)
        self.assertEqual(settings.get_own(PhrasingSetting.RISE_AND_FALL), phrasing.LITTLE_RISE)
        self.assertEqual(settings.get_own(PhrasingSetting.NOTES), phrasing.NOTES_AS_WRITTEN)
        self.assertEqual(settings.to_data(), {})
