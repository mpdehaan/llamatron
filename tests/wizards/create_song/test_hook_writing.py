# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The written hook and the body of its chorus: a behavior and gauges make a bar, and the lines around the hook follow theirs."""

import itertools
import unittest

from llamatron.music_theory.hooks import hook_bars
from llamatron.wizards.create_song import arranger, hook_writing, melody, notation, wizard_names

ROCK = 'rock'
COMMON_TIME = '4/4'
SEEDS = range(1, 21)
CHORDS = [{notation.DEGREE: 1}, {notation.DEGREE: 4}, {notation.DEGREE: 5}, {notation.DEGREE: 1}]
VERSE_PLAN = [{melody.LINE: 'a'}, {melody.LINE: 'b'}, {melody.LINE: 'a', melody.VARIED: True}, {melody.LINE: 'c'}]
# A chorus whose hook is its first and third lines, with a line that leads to the hook and a line that closes.
CHORUS_PLAN = [{melody.LINE: 'hook', melody.HOOK: True, melody.HIGHER: True}, {melody.LINE: 'd', melody.HIGHER: True},
               {melody.LINE: 'hook', melody.HOOK: True, melody.HIGHER: True}, {melody.LINE: 'e', melody.HIGHER: True}]
# A chorus whose second line is neither before a hook nor the last, and returns.
FREE_PLAN = [{melody.LINE: 'hook', melody.HOOK: True, melody.HIGHER: True}, {melody.LINE: 'd', melody.HIGHER: True}, {melody.LINE: 'd', melody.HIGHER: True, melody.VARIED: True},
             {melody.LINE: 'e', melody.HIGHER: True}]
A_FEW = 3
AN_ORDER = 1
HOME_CHORD_DEGREES = (1, 3, 5)
EVERY_SECOND_POSITION = range(hook_bars.LOWEST_GAUGE, hook_bars.HIGHEST_GAUGE + 1, 3)


def habits_with(*, behavior=hook_writing.DEFAULT_BEHAVIOR, hook=None, body=None):
    """A real style's habits with a behavior and gauges set over the gauges every hook and every body starts from."""
    style = arranger.style_named(ROCK)
    return {**style[arranger.MELODY][COMMON_TIME],
            wizard_names.HOOK_WRITING: {hook_writing.BEHAVIOR: behavior, hook_writing.GAUGES: {**hook_writing.HOOK_GAUGES, **(hook or {})}},
            wizard_names.BODY_WRITING: {hook_writing.GAUGES: {**hook_writing.BODY_GAUGES, **(body or {})}}}


def sections(*, habits, seed, plans=(VERSE_PLAN, CHORUS_PLAN)):
    letters = [entry[melody.LINE] for plan in plans for entry in plan]
    return [melody.sketched(habits=habits, plan=plan, chords=CHORDS, scale_type=melody.MAJOR, seed=seed, answers=False, engine=melody.SMART, letters=letters, hook=True) for plan in plans]


def lasts(note):
    return note.get(notation.REST, note.get(notation.STEPS, 0))


def bars_of(*, line, grid):
    """A line's notes bar by bar."""
    bars = [[]]
    for note in line:
        if sum(lasts(other) for other in bars[-1]) == grid:
            bars.append([])
        bars[-1].append(note)
    return bars


def rhythm_of(notes):
    return [(notation.REST in note, lasts(note)) for note in notes]


def places_of(*, line, habits):
    ladder = melody.ladder_of(notes=habits[melody.LADDER], scale_type=melody.MAJOR)
    rungs = [rung for _, rung in ladder]
    return [rungs.index({field: note[field] for field in melody.PITCH_FIELDS if field in note}) for note in line if notation.REST not in note]


def silence_at_end(line):
    return sum(lasts(note) for note in itertools.takewhile(lambda note: notation.REST in note, reversed(line)))


def degree_of(note):
    return note[notation.DEGREE]


class TestBars(unittest.TestCase):
    """A behavior and gauges make one bar of eight units, whatever the gauges say."""

    __slots__ = ()

    def test_every_behavior_fills_a_bar_at_every_position_of_every_gauge(self):
        for behavior in hook_bars.BEHAVIORS:
            names = hook_bars.GAUGES_OF[behavior]
            for positions in itertools.product(EVERY_SECOND_POSITION, repeat=len(names)):
                gauges = {**hook_writing.HOOK_GAUGES, **dict(zip(names, positions))}
                for take in range(A_FEW):
                    lengths, depths = hook_bars.bar_of(behavior=behavior, gauges=gauges, order=AN_ORDER, take=take)
                    self.assertEqual(sum(abs(length) for length in lengths), hook_bars.UNITS, (behavior, gauges))
                    self.assertEqual(len(depths), sum(1 for length in lengths if length > 0), (behavior, gauges))
                    self.assertTrue(all(depth >= 0 for depth in depths), (behavior, gauges))

    def test_a_chant_stays_on_its_note_and_a_ladder_only_climbs_by_rungs_as_wide_as_leap_says(self):
        spans = []
        for take in range(A_FEW):
            _, chant = hook_bars.bar_of(behavior=hook_bars.CHANT, gauges=hook_writing.HOOK_GAUGES, order=AN_ORDER, take=take)
            self.assertLessEqual(max(chant) - min(chant), 1)
        for position in (hook_bars.LOWEST_GAUGE, hook_bars.HIGHEST_GAUGE):
            _, ladder = hook_bars.bar_of(behavior=hook_bars.LADDER, gauges={**hook_writing.HOOK_GAUGES, hook_bars.LEAP: position}, order=AN_ORDER, take=0)
            self.assertEqual(ladder[-1], 0)
            self.assertLessEqual(max(ladder), hook_bars.LADDER_DEEPEST)
            spans.append(max(ladder))
        self.assertLess(spans[0], spans[1])
        self.assertIn(hook_bars.LEAP, hook_bars.GAUGES_OF[hook_bars.LADDER])
        self.assertNotIn(hook_bars.LEAP, hook_bars.GAUGES_OF[hook_bars.CHANT])

    def test_a_plainer_bar_has_no_more_notes_and_fills_the_bar(self):
        lengths, _ = hook_bars.bar_of(behavior=hook_bars.ARCH, gauges={**hook_writing.HOOK_GAUGES, hook_bars.SIMPLICITY: hook_bars.LOWEST_GAUGE}, order=AN_ORDER, take=0)
        plain = hook_bars.plainer(lengths)
        self.assertEqual(sum(abs(length) for length in plain), hook_bars.UNITS)
        self.assertLessEqual(len(plain), len(lengths))

    def test_what_is_no_position_is_not_one(self):
        for value in (hook_bars.LOWEST_GAUGE - 1, hook_bars.HIGHEST_GAUGE + 1, True, None, '5'):
            self.assertFalse(hook_bars.is_position(value))
        self.assertTrue(hook_bars.is_position(hook_bars.LOWEST_GAUGE))
        self.assertTrue(hook_bars.is_position(hook_bars.HIGHEST_GAUGE))

    def test_a_song_s_ways_are_laid_over_the_gauges_every_hook_starts_from(self):
        self.assertEqual(hook_writing.hook_ways({}), (hook_writing.DEFAULT_BEHAVIOR, hook_writing.HOOK_GAUGES))
        behavior, gauges = hook_writing.hook_ways({wizard_names.HOOK_WRITING: {hook_writing.BEHAVIOR: hook_bars.CHANT, hook_writing.GAUGES: {hook_bars.HOLD: hook_bars.LOWEST_GAUGE}}})
        self.assertEqual(behavior, hook_bars.CHANT)
        self.assertEqual(gauges, {**hook_writing.HOOK_GAUGES, hook_bars.HOLD: hook_bars.LOWEST_GAUGE})
        self.assertEqual(hook_writing.body_ways({wizard_names.BODY_WRITING: {hook_writing.GAUGES: {hook_writing.SPACE: hook_bars.HIGHEST_GAUGE}}}), {**hook_writing.BODY_GAUGES, hook_writing.SPACE: hook_bars.HIGHEST_GAUGE})


class TestWrittenHook(unittest.TestCase):
    """The hook a behavior and gauges write, on every seed."""

    __slots__ = ()

    def test_the_hook_s_bar_returns_note_for_note_and_the_hook_line_returns_the_same(self):
        for behavior in hook_bars.BEHAVIORS:
            habits = habits_with(behavior=behavior)
            grid = habits[melody.GRID]
            for seed in SEEDS:
                _, chorus = sections(habits=habits, seed=seed)
                bars = bars_of(line=chorus[0], grid=grid)
                self.assertEqual(sum(lasts(note) for note in chorus[0]), grid * habits[melody.LINE_BARS])
                self.assertEqual(rhythm_of(bars[0]), rhythm_of(bars[2]) if len(bars) > 2 else rhythm_of(bars[0]), behavior)
                self.assertEqual(chorus[0], chorus[2], behavior)

    def test_the_hook_s_top_is_above_every_line_of_the_verse_and_of_its_chorus(self):
        habits = habits_with()
        for seed in SEEDS:
            verse, chorus = sections(habits=habits, seed=seed)
            top = max(places_of(line=chorus[0], habits=habits))
            for line in (*verse, chorus[1], chorus[3]):
                self.assertLess(max(places_of(line=line, habits=habits)), top)

    def test_height_sets_the_hook_higher_and_the_other_lines_stay_under_it(self):
        tops = []
        for position in (hook_bars.LOWEST_GAUGE, hook_bars.HIGHEST_GAUGE):
            habits = habits_with(hook={hook_bars.HEIGHT: position})
            verse, chorus = sections(habits=habits, seed=SEEDS[0])
            tops.append(max(places_of(line=chorus[0], habits=habits)))
            self.assertLess(max(place for line in verse for place in places_of(line=line, habits=habits)), tops[-1])
        self.assertLess(tops[0], tops[1])

    def test_catchiness_brings_the_answer_nearer_the_hook(self):
        grid = habits_with()[melody.GRID]
        plain = bars_of(line=sections(habits=habits_with(hook={hook_bars.CATCHINESS: hook_bars.LOWEST_GAUGE}), seed=SEEDS[0])[1][0], grid=grid)
        same = bars_of(line=sections(habits=habits_with(hook={hook_bars.CATCHINESS: hook_bars.HIGHEST_GAUGE}), seed=SEEDS[0])[1][0], grid=grid)
        self.assertEqual(rhythm_of(plain[0]), rhythm_of(same[0]))
        self.assertNotEqual(plain[1], same[1])
        self.assertLessEqual(len([note for note in plain[1] if notation.REST not in note]), len([note for note in same[1] if notation.REST not in note]))

    def test_the_answer_leaves_room_a_breath_or_a_held_last_note_and_leaves_no_note_out(self):
        for behavior in hook_bars.BEHAVIORS:
            habits = habits_with(behavior=behavior)
            grid = habits[melody.GRID]
            for seed in SEEDS:
                line = sections(habits=habits, seed=seed)[1][0]
                last = [note for note in line if notation.REST not in note][-1]
                self.assertGreaterEqual(silence_at_end(line) + last[notation.STEPS], grid * melody.ANSWER_BREATH // hook_bars.UNITS, behavior)
                figure, answer = bars_of(line=line, grid=grid)[:2]
                if hook_writing.HOOK_GAUGES[hook_bars.CATCHINESS] >= hook_writing.SAME_RHYTHM_FROM:
                    self.assertEqual(len([note for note in answer if notation.REST not in note]), len([note for note in figure if notation.REST not in note]), behavior)

    def test_a_held_last_note_is_left_whole(self):
        habits = habits_with(hook={hook_bars.HOLD: hook_bars.HIGHEST_GAUGE, hook_bars.SIMPLICITY: hook_bars.HIGHEST_GAUGE})
        line = sections(habits=habits, seed=SEEDS[0])[1][0]
        figure, answer = bars_of(line=line, grid=habits[melody.GRID])[:2]
        self.assertEqual(lasts([note for note in answer if notation.REST not in note][-1]), lasts([note for note in figure if notation.REST not in note][-1]))

    def test_the_same_seed_writes_the_same_hook_and_each_behavior_another(self):
        self.assertEqual(sections(habits=habits_with(), seed=SEEDS[0]), sections(habits=habits_with(), seed=SEEDS[0]))
        hooks = {repr(sections(habits=habits_with(behavior=behavior), seed=SEEDS[0])[1][0]) for behavior in hook_bars.BEHAVIORS}
        self.assertEqual(len(hooks), len(hook_bars.BEHAVIORS))

    def test_a_bar_not_counted_in_eight_keeps_the_hook_of_a_kind(self):
        habits = {**habits_with(), melody.GRID: 12}
        self.assertIsNone(melody.Hooks(habits=habits, chords=CHORDS, scale_type=melody.MAJOR, seed=SEEDS[0], answers=False).written())


class TestBody(unittest.TestCase):
    """The lines of a chorus that are no hook, written around it by their gauges."""

    __slots__ = ()

    def test_a_line_before_the_hook_ends_open_and_the_last_line_ends_on_a_note_of_the_home_chord(self):
        habits = habits_with()
        for seed in SEEDS:
            _, chorus = sections(habits=habits, seed=seed)
            leads = [note for note in chorus[1] if notation.REST not in note][-1]
            closes = [note for note in chorus[3] if notation.REST not in note][-1]
            self.assertIn(degree_of(leads), melody.LEADING_DEGREES)
            self.assertIn(degree_of(closes), HOME_CHORD_DEGREES)

    def test_space_never_leaves_fewer_than_half_of_a_line_s_notes(self):
        for seed in SEEDS:
            none = sections(habits=habits_with(body={hook_writing.SPACE: hook_bars.LOWEST_GAUGE}), seed=seed)[1][1]
            most = sections(habits=habits_with(body={hook_writing.SPACE: hook_bars.HIGHEST_GAUGE}), seed=seed)[1][1]
            self.assertGreaterEqual(2 * len([note for note in most if notation.REST not in note]), len([note for note in none if notation.REST not in note]))

    def test_space_is_the_silence_a_line_ends_in(self):
        silences = []
        for position in (hook_bars.LOWEST_GAUGE, hook_bars.HIGHEST_GAUGE):
            _, chorus = sections(habits=habits_with(body={hook_writing.SPACE: position}), seed=SEEDS[0])
            silences.append(silence_at_end(chorus[1]))
        self.assertLess(silences[0], silences[1])

    def test_lift_raises_every_line_of_the_body_and_none_reaches_the_hook(self):
        tops = []
        for position in (hook_bars.LOWEST_GAUGE, hook_bars.HIGHEST_GAUGE):
            habits = habits_with(body={hook_writing.LIFT: position})
            _, chorus = sections(habits=habits, seed=SEEDS[0])
            tops.append(max(places_of(line=chorus[1], habits=habits)))
            self.assertLess(tops[-1], max(places_of(line=chorus[0], habits=habits)))
        self.assertLess(tops[0], tops[1])

    def test_sameness_gives_the_body_the_hook_s_rhythm_in_more_of_its_bars(self):
        grid = habits_with()[melody.GRID]
        alike = []
        for position in (hook_bars.LOWEST_GAUGE, hook_bars.HIGHEST_GAUGE):
            # With no silence asked for, a bar of the body is the hook's bar or a plainer one, whole.
            _, chorus = sections(habits=habits_with(body={hook_writing.SAMENESS: position, hook_writing.SPACE: hook_bars.LOWEST_GAUGE}), seed=SEEDS[0])
            hook_bar = rhythm_of(bars_of(line=chorus[0], grid=grid)[0])
            alike.append(sum(1 for bar in bars_of(line=chorus[1], grid=grid)[:1] if rhythm_of(bar) == hook_bar))
        self.assertLess(alike[0], alike[1])

    def test_resolve_settles_a_free_line_on_the_chord_or_leaves_it_off_the_chord(self):
        endings = []
        for position in (hook_bars.LOWEST_GAUGE, hook_bars.HIGHEST_GAUGE):
            _, chorus = sections(habits=habits_with(body={hook_writing.RESOLVE: position}), seed=SEEDS[0], plans=(VERSE_PLAN, FREE_PLAN))
            endings.append([note for note in chorus[1] if notation.REST not in note][-1])
        self.assertNotEqual(endings[0], endings[1])

    def test_call_and_answer_decides_whether_a_line_that_returns_keeps_its_notes(self):
        kept = []
        for position in (hook_bars.LOWEST_GAUGE, hook_bars.HIGHEST_GAUGE):
            _, chorus = sections(habits=habits_with(body={hook_writing.CALL_AND_ANSWER: position, hook_writing.RESOLVE: hook_bars.LOWEST_GAUGE}), seed=SEEDS[0], plans=(VERSE_PLAN, FREE_PLAN))
            first = [note for note in chorus[1] if notation.REST not in note]
            again = [note for note in chorus[2] if notation.REST not in note]
            kept.append(first[:-1] == again[:-1])
            if position == hook_bars.HIGHEST_GAUGE:
                # An answer settles where the line it answers was left open.
                self.assertNotEqual(first[-1], again[-1])
        self.assertEqual(kept, [False, True])

    def test_a_writer_whose_lines_are_its_own_keeps_its_chorus(self):
        letters = [entry[melody.LINE] for entry in VERSE_PLAN + CHORUS_PLAN]
        for engine in (melody.SERIAL, melody.EVOLVING):
            given = dict(chords=CHORDS, scale_type=melody.MAJOR, seed=SEEDS[0], answers=False, engine=engine, letters=letters, hook=True, plan=CHORUS_PLAN)
            with_body = melody.sketched(habits=habits_with(body={hook_writing.SPACE: hook_bars.HIGHEST_GAUGE}), **given)
            self.assertEqual(with_body[1], melody.sketched(habits=habits_with(body={hook_writing.SPACE: hook_bars.LOWEST_GAUGE}), **given)[1], engine)
