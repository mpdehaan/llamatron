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
"""Phrasing: a tune's lines end early for a breath as the clip plays, the shorter lines sooner, a note of some lines comes an eighth early, a kind of section says its own, and a note marked whole in the pattern is left as written."""

import unittest

from llamatron.composition.file_format import ClipSlotSetting, GeneratorKind, PatternSetting, Row, SceneSetting, Section, SectionKind
from llamatron.composition.generator_settings import DEFAULT_EARLY_NOTES, DEFAULT_LINE_BARS, PhrasingSetting, PhrasingSettings
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.song_file_error import SongFileError
from llamatron.exporters.timing import timed_events
from llamatron.generators.phrasing import EVEN_LINES, LONG_BREATH, LONG_THEN_SHORT, MEDIUM_BREATH, MOST_EARLY, NO_BREATH, SHORT_THEN_LONG
from llamatron.strings.errors import ERR_BAD_BY_SECTION, ERR_NOT_A_CHOICE
from llamatron.support.rational import Rational
from tests.playback.test_registers import LEAD, pattern, song
from tests.support.rendering import render_data, setlist_from_data
from tests.support.ui_testing import fixed_text

TUNE = 'tune'
BREATHING = 'breathing'
CHAIN = 'sung'
NOT_A_BREATH = 'gasping'
NOT_A_SECTION = 'middle bit'
EIGHTH = Rational(1, 8)
EIGHTH_STEP = '1/8'
BAR = Rational(1)
# A tune of four lines of two bars, written in eighths: each line is a note an eighth long on every step, so that where a line stops is where its notes stop.
STEPS_IN_LINE = 16
LINES = 4
STEPS = STEPS_IN_LINE * LINES
LINE = 2 * BAR
NO_EARLY = 0
# The eighths of breath after a longer line and after a shorter one, at the breath a Phrasing starts with.
AFTER_LONGER = 3
AFTER_SHORTER = 5
AFTER_LONGER_WHEN_LONG = 4


def phrased_data(*, settings=None, section=None, rows=None, steps=STEPS):
    """Return a song's data whose lead plays the tune through a chain of one Phrasing, in a scene of a kind of section or of none."""
    tune = pattern(steps, **(rows or {}))
    tune[PatternSetting.STEP_SIZE] = EIGHTH_STEP
    scene = {SceneSetting.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: TUNE, ClipSlotSetting.CHAINS: [CHAIN]}}}
    if section is not None:
        scene[SceneSetting.SECTION] = section
    data = song(patterns={TUNE: tune}, scenes=[scene])
    data[Section.PHRASINGS] = {BREATHING: {PhrasingSetting.EARLY_NOTES: NO_EARLY} if settings is None else settings}
    data[Section.CHAINS] = {CHAIN: [{GeneratorKind.PHRASING: BREATHING}]}
    return data


def heard(data):
    """Return when each note the lead plays starts and how long it lasts, in whole notes, in time order."""
    grid = render_data(data)
    clip = grid.get_clip(row=grid.get_rows()[0], column=grid.get_columns()[0])
    return sorted((start, end - start) for start, end, _, _ in timed_events(clip=clip, scale=clip.get_scale())[0])


def line_ends(data):
    """Return how many eighths before its end each line's last note stops."""
    notes = heard(data)
    ends = []
    for line in range(LINES):
        last = max(start + length for start, length in notes if line * LINE <= start < (line + 1) * LINE)
        ends.append(((line + 1) * LINE - last) / EIGHTH)
    return ends


class TestPhrasing(unittest.TestCase):

    def test_each_line_ends_early_for_a_breath_and_the_second_and_fourth_sooner(self):
        self.assertEqual(line_ends(phrased_data()), [AFTER_LONGER, AFTER_SHORTER, AFTER_LONGER, AFTER_SHORTER])

    def test_no_note_moves_or_changes_but_those_in_a_breath(self):
        notes = heard(phrased_data())
        self.assertEqual(len(notes), STEPS - 2 * AFTER_LONGER - 2 * AFTER_SHORTER)
        self.assertTrue(all(length == EIGHTH and (start / EIGHTH).is_whole() for start, length in notes))

    def test_the_line_lengths_say_which_lines_are_the_shorter(self):
        short_first = phrased_data(settings={PhrasingSetting.EARLY_NOTES: NO_EARLY, PhrasingSetting.LINE_LENGTHS: SHORT_THEN_LONG})
        self.assertEqual(line_ends(short_first), [AFTER_SHORTER, AFTER_LONGER, AFTER_SHORTER, AFTER_LONGER])
        even = phrased_data(settings={PhrasingSetting.EARLY_NOTES: NO_EARLY, PhrasingSetting.LINE_LENGTHS: EVEN_LINES})
        self.assertEqual(line_ends(even), [AFTER_LONGER] * LINES)

    def test_a_breath_of_off_leaves_the_tune_as_written(self):
        off = phrased_data(settings={PhrasingSetting.EARLY_NOTES: NO_EARLY, PhrasingSetting.BREATH: NO_BREATH})
        self.assertEqual(line_ends(off), [0] * LINES)
        self.assertEqual(len(heard(off)), STEPS)

    def test_a_line_of_one_bar_breathes_every_bar(self):
        one_bar = phrased_data(settings={PhrasingSetting.EARLY_NOTES: NO_EARLY, PhrasingSetting.LINE_BARS: 1, PhrasingSetting.LINE_LENGTHS: EVEN_LINES})
        self.assertEqual(len(heard(one_bar)), STEPS - 2 * LINES * AFTER_LONGER)

    def test_a_long_note_that_sounds_into_the_breath_stops_where_the_breath_begins(self):
        # The line's second bar is one note held for the whole bar, by ties.
        ties = ([False] * 9 + [True] * 7) * LINES
        degrees = ([1] * 9 + [None] * 7) * LINES
        notes = heard(phrased_data(rows={Row.DEGREE: degrees, Row.TIE: ties}))
        held = [length for start, length in notes if start == BAR]
        self.assertEqual(held, [BAR - AFTER_LONGER * EIGHTH])

    def test_a_note_marked_whole_in_the_pattern_is_left_as_written(self):
        # The first line is the hook: every step of it is marked.
        whole = [True] * STEPS_IN_LINE + [False] * (STEPS - STEPS_IN_LINE)
        self.assertEqual(line_ends(phrased_data(rows={Row.NO_BREATH: whole})), [0, AFTER_SHORTER, AFTER_LONGER, AFTER_SHORTER])

    def test_early_notes_bring_a_note_of_so_many_lines_in_four_an_eighth_early(self):
        # Quarter notes, so that the note before one that comes early is long enough to give an eighth up.
        ties = [False, True] * (STEPS // 2)
        degrees = [1, None] * (STEPS // 2)
        rows = {Row.DEGREE: degrees, Row.TIE: ties}
        on_the_grid = [start for start, _ in heard(phrased_data(rows=rows, settings={PhrasingSetting.EARLY_NOTES: NO_EARLY, PhrasingSetting.BREATH: NO_BREATH}))]
        for early in range(MOST_EARLY + 1):
            starts = [start for start, _ in heard(phrased_data(rows=rows, settings={PhrasingSetting.EARLY_NOTES: early, PhrasingSetting.BREATH: NO_BREATH}))]
            moved = [(before, after) for before, after in zip(on_the_grid, starts) if before != after]
            self.assertEqual(len(moved), early)
            self.assertTrue(all(before - after == EIGHTH for before, after in moved))
            self.assertEqual(len({int(before // LINE) for before, _ in moved}), early)

    def test_a_kind_of_section_says_its_own_and_another_takes_the_phrasings(self):
        settings = {PhrasingSetting.EARLY_NOTES: NO_EARLY, PhrasingSetting.BY_SECTION: {SectionKind.CHORUS: {PhrasingSetting.BREATH: LONG_BREATH, PhrasingSetting.LINE_LENGTHS: EVEN_LINES}}}
        self.assertEqual(line_ends(phrased_data(settings=settings, section=SectionKind.CHORUS)), [AFTER_LONGER_WHEN_LONG] * LINES)
        for other in (SectionKind.VERSE, None):
            self.assertEqual(line_ends(phrased_data(settings=settings, section=other)), [AFTER_LONGER, AFTER_SHORTER, AFTER_LONGER, AFTER_SHORTER])

    def test_the_same_settings_always_play_the_same(self):
        self.assertEqual(heard(phrased_data(settings={})), heard(phrased_data(settings={})))


class TestPhrasingSettings(unittest.TestCase):

    def test_a_new_one_starts_with_lines_of_two_bars_a_medium_breath_long_then_short_and_two_early(self):
        settings = PhrasingSettings.new()
        self.assertEqual(settings.get_line_bars(), DEFAULT_LINE_BARS)
        self.assertEqual(settings.get_own(PhrasingSetting.BREATH), MEDIUM_BREATH)
        self.assertEqual(settings.get_own(PhrasingSetting.LINE_LENGTHS), LONG_THEN_SHORT)
        self.assertEqual(settings.get_own(PhrasingSetting.EARLY_NOTES), DEFAULT_EARLY_NOTES)
        self.assertEqual(settings.to_data(), {})

    def test_a_sections_own_value_is_set_read_written_and_cleared(self):
        settings = PhrasingSettings.new()
        settings.set_section_own(section=SectionKind.CHORUS, name=PhrasingSetting.BREATH, value=NO_BREATH)
        self.assertEqual(settings.get_section_own(section=SectionKind.CHORUS, name=PhrasingSetting.BREATH), NO_BREATH)
        self.assertEqual(settings.get_for(section=SectionKind.CHORUS, name=PhrasingSetting.BREATH), NO_BREATH)
        self.assertEqual(settings.get_for(section=SectionKind.VERSE, name=PhrasingSetting.BREATH), MEDIUM_BREATH)
        self.assertEqual(settings.to_data(), {PhrasingSetting.BY_SECTION: {SectionKind.CHORUS: {PhrasingSetting.BREATH: NO_BREATH}}})
        settings.set_section_own(section=SectionKind.CHORUS, name=PhrasingSetting.BREATH, value=None)
        self.assertEqual(settings.to_data(), {})

    def test_a_wrong_value_is_refused_by_the_setter_and_by_a_file_in_the_same_words(self):
        settings = PhrasingSettings.new()
        with self.assertRaises(InvalidValue) as refused:
            settings.set_setting(name=PhrasingSetting.BREATH, value=NOT_A_BREATH)
        self.assertIn(fixed_text(ERR_NOT_A_CHOICE), str(refused.exception))
        with self.assertRaises(SongFileError) as unread:
            setlist_from_data(phrased_data(settings={PhrasingSetting.BREATH: NOT_A_BREATH}))
        self.assertIn(fixed_text(ERR_NOT_A_CHOICE), str(unread.exception))

    def test_a_section_that_is_no_kind_of_section_and_a_wrong_value_of_its_own_are_refused(self):
        settings = PhrasingSettings.new()
        with self.assertRaises(InvalidValue) as refused:
            settings.set_section_own(section=NOT_A_SECTION, name=PhrasingSetting.BREATH, value=NO_BREATH)
        self.assertIn(fixed_text(ERR_BAD_BY_SECTION), str(refused.exception))
        with self.assertRaises(InvalidValue):
            settings.set_section_own(section=SectionKind.CHORUS, name=PhrasingSetting.BREATH, value=NOT_A_BREATH)
        self.assertEqual(settings.to_data(), {})
        with self.assertRaises(SongFileError):
            setlist_from_data(phrased_data(settings={PhrasingSetting.BY_SECTION: {NOT_A_SECTION: {}}}))
