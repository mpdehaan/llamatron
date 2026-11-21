# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests of a riff, a song's second hook: its notes as drawn. The riffs of the song wizard's choices are tested in test_wizard_riffs.py."""

import unittest

from llamatron.wizards.create_song import line_edits, notation, riffs
from llamatron.wizards.create_song.riffs import heavy_line, riff_line

A_SEED = 11
ANOTHER_SEED = 12
EIGHTHS = 8
MANY_SEEDS = 40
MAJOR = 'major'
MINOR = 'minor'
HOME_CHORD = {notation.DEGREE: 1}
AWAY_CHORD = {notation.DEGREE: 4}
FLAT_SEVEN = {notation.DEGREE: 7, notation.ACCIDENTAL: notation.FLAT}
ONE_BAR = 1


def lasts(note):
    return note.get(notation.REST, note.get(notation.STEPS))


def places(line):
    """Each note of a line with the eighth it starts on."""
    at = 0
    found = []
    for note in line:
        found.append((at, note))
        at += lasts(note)
    return found


class TestRiffLine(unittest.TestCase):
    """A riff's notes as drawn."""

    __slots__ = ()

    def test_a_riff_is_two_bars_that_start_on_the_root_the_second_answering_the_first(self):
        for seed in range(MANY_SEEDS):
            line = riff_line(seed=seed, take=riffs.FIRST_TAKE, eighths=EIGHTHS)
            self.assertEqual(line_edits.steps_of(line), riffs.RIFF_BARS * EIGHTHS)
            self.assertEqual((line[0][notation.DEGREE], line[0].get(notation.OCTAVE, 0)), riffs.HOME)
            first, second = self.bars(line)
            self.assertEqual([line_edits.length_of(note) for note in first], [line_edits.length_of(note) for note in second])
            self.assertEqual([notation.REST in note for note in first], [notation.REST in note for note in second])
            self.assertEqual(first[0], second[0])

    def bars(self, line):
        half = len(line) // riffs.RIFF_BARS
        return line[:half], line[half:]

    def test_a_riff_of_one_bar_is_the_first_bar_alone(self):
        whole = riff_line(seed=A_SEED, take=riffs.FIRST_TAKE, eighths=EIGHTHS)
        one = riff_line(seed=A_SEED, take=riffs.FIRST_TAKE, eighths=EIGHTHS, bars=ONE_BAR)
        self.assertEqual(sum(lasts(note) for note in one), EIGHTHS)
        self.assertEqual(one, whole[:len(one)])

    def test_a_seed_and_a_take_make_one_riff_and_another_take_another(self):
        self.assertEqual(riff_line(seed=A_SEED, take=riffs.FIRST_TAKE, eighths=EIGHTHS), riff_line(seed=A_SEED, take=riffs.FIRST_TAKE, eighths=EIGHTHS))
        self.assertNotEqual(riff_line(seed=A_SEED, take=riffs.FIRST_TAKE, eighths=EIGHTHS), riff_line(seed=A_SEED, take=riffs.FIRST_TAKE + 1, eighths=EIGHTHS))
        self.assertNotEqual(riff_line(seed=A_SEED, take=riffs.FIRST_TAKE, eighths=EIGHTHS), riff_line(seed=ANOTHER_SEED, take=riffs.FIRST_TAKE, eighths=EIGHTHS))


class TestHeavyRiff(unittest.TestCase):
    """A riff of chords on its accents, as drawn."""

    __slots__ = ()

    def test_the_riff_starts_on_the_roots_chord_and_has_an_accent_off_the_beat_in_every_bar(self):
        for seed in range(MANY_SEEDS):
            for gap in (False, True):
                line = heavy_line(seed=seed, take=riffs.FIRST_TAKE, eighths=EIGHTHS, gap=gap)
                with self.subTest(seed=seed, gap=gap):
                    self.assertEqual(sum(lasts(note) for note in line), riffs.RIFF_BARS * EIGHTHS)
                    first = line[0]
                    self.assertEqual((first[notation.DEGREE], first[notation.CHORD], first[notation.LEVEL]), (riffs.HOME[0], riffs.POWER_CHORD, notation.ACCENT))
                    accents = [at for at, note in places(line) if note.get(notation.LEVEL) == notation.ACCENT]
                    for bar in range(riffs.RIFF_BARS):
                        self.assertIn(bar * EIGHTHS, accents)
                        self.assertTrue(any(at % 2 for at in accents if at // EIGHTHS == bar))
                    # Every accent is a chord, and nothing else is.
                    self.assertTrue(all((notation.CHORD in note) == (note.get(notation.LEVEL) == notation.ACCENT) for note in line if notation.REST not in note))

    def test_half_the_notes_or_more_are_the_root_and_the_last_are_single_notes_that_lead_back(self):
        for seed in range(MANY_SEEDS):
            line = heavy_line(seed=seed, take=riffs.FIRST_TAKE, eighths=EIGHTHS)
            sounding = [note for note in line if notation.REST not in note]
            with self.subTest(seed=seed):
                self.assertGreaterEqual(2 * sum(riffs.is_root(note) for note in sounding), len(sounding))
                tail = [tuple(note[notation.DEGREE] for note in line[-len(ending):]) for ending in riffs.TAILS]
                self.assertIn(True, [found == tuple(place[0] for place in ending) for found, ending in zip(tail, riffs.TAILS)])
                self.assertTrue(all(notation.CHORD not in note and notation.LEVEL not in note and note[notation.STEPS] == 1 for note in line[-2:]))

    def test_between_the_accents_lie_short_quiet_roots_or_rests(self):
        for seed in range(MANY_SEEDS):
            muted = heavy_line(seed=seed, take=riffs.FIRST_TAKE, eighths=EIGHTHS, between=riffs.MUTED_ROOTS)
            rests = heavy_line(seed=seed, take=riffs.FIRST_TAKE, eighths=EIGHTHS, between=riffs.RESTS_BETWEEN)
            with self.subTest(seed=seed):
                self.assertTrue(all(riffs.is_root(note) and note[riffs.GATE] == riffs.MUTED_GATE and note[notation.STEPS] == 1 for note in muted if note.get(notation.LEVEL) == notation.GHOST))
                self.assertFalse(any(notation.REST in note for note in muted))
                self.assertFalse(any(note.get(notation.LEVEL) == notation.GHOST for note in rests))

    def test_a_riff_of_one_bar_is_the_last_bar_and_a_gap_empties_the_second_half_of_the_first(self):
        one = heavy_line(seed=A_SEED, take=riffs.FIRST_TAKE, eighths=EIGHTHS, bars=ONE_BAR)
        self.assertEqual(riffs.bars_of(line=one, eighths=EIGHTHS), ONE_BAR)
        self.assertTrue(all(notation.CHORD not in note for note in one[-2:]))
        for seed in range(MANY_SEEDS):
            first, last = riffs.split_bars(line=heavy_line(seed=seed, take=riffs.FIRST_TAKE, eighths=EIGHTHS, gap=True), eighths=EIGHTHS)
            self.assertEqual(first[-1], {notation.REST: EIGHTHS // 2})
            self.assertFalse(any(notation.REST in note for note in last))
            # Both bars start alike: the last bar is the first again, with the tail.
            self.assertEqual(first[0], last[0])
        # A gap is the first bar's of two, and a riff of one bar has none.
        self.assertEqual(heavy_line(seed=A_SEED, take=riffs.FIRST_TAKE, eighths=EIGHTHS, bars=ONE_BAR, gap=True), one)

    def test_the_third_and_the_seventh_are_flattened_over_a_scale_that_has_them_major(self):
        self.assertEqual(riffs.flattened_in(MAJOR), riffs.FLATTENED)
        self.assertEqual(riffs.flattened_in(MINOR), ())
        for seed in range(MANY_SEEDS):
            line = heavy_line(seed=seed, take=riffs.FIRST_TAKE, eighths=EIGHTHS, flattened=riffs.FLATTENED)
            plain = heavy_line(seed=seed, take=riffs.FIRST_TAKE, eighths=EIGHTHS)
            self.assertTrue(all(note.get(notation.ACCIDENTAL) == notation.FLAT for note in line if note.get(notation.DEGREE) in riffs.FLATTENED))
            self.assertEqual([note.get(notation.DEGREE) for note in line], [note.get(notation.DEGREE) for note in plain])

    def test_a_seed_and_a_take_make_one_riff_and_others_another(self):
        self.assertEqual(heavy_line(seed=A_SEED, take=riffs.FIRST_TAKE, eighths=EIGHTHS), heavy_line(seed=A_SEED, take=riffs.FIRST_TAKE, eighths=EIGHTHS))
        self.assertGreater(len({repr(heavy_line(seed=seed, take=riffs.FIRST_TAKE, eighths=EIGHTHS)) for seed in range(MANY_SEEDS)}), MANY_SEEDS // 2)
        self.assertGreater(len({repr(heavy_line(seed=A_SEED, take=take, eighths=EIGHTHS)) for take in range(MANY_SEEDS)}), MANY_SEEDS // 2)

    def test_a_second_player_plays_the_notes_alone_and_a_kick_strikes_the_accents(self):
        line = heavy_line(seed=A_SEED, take=riffs.FIRST_TAKE, eighths=EIGHTHS)
        under = riffs.single(line)
        self.assertFalse(any(notation.CHORD in note for note in under))
        self.assertEqual([{field: value for field, value in note.items() if field != notation.CHORD} for note in line], under)
        bars = riffs.accent_bars(line=line, eighths=EIGHTHS)
        self.assertEqual([len(bar) for bar in bars], [EIGHTHS] * riffs.RIFF_BARS)
        struck = [at for at, hit in enumerate(hit for bar in bars for hit in bar) if hit == notation.LOUD]
        self.assertEqual(struck, [at for at, note in places(line) if note.get(notation.LEVEL) == notation.ACCENT])
        self.assertEqual({hit for bar in bars for hit in bar}, {notation.LOUD, notation.NONE})

    def test_a_riff_that_stays_plays_over_the_home_chord_where_the_section_is_mostly_at_home(self):
        at_home = [HOME_CHORD] * 4 + [AWAY_CHORD, FLAT_SEVEN] + [HOME_CHORD] * 2
        self.assertEqual(riffs.bars_played(chords=at_home, bars=8, count=riffs.RIFF_BARS, stays=True), [0, 1, 0, 1, None, None, 0, 1])
        self.assertEqual(riffs.bars_played(chords=at_home, bars=8, count=riffs.RIFF_BARS, stays=False), [0, 1] * 4)
        # Fewer than half the bars at home, or never two bars together: the riff moves with each chord.
        self.assertEqual(riffs.bars_played(chords=[HOME_CHORD, AWAY_CHORD, AWAY_CHORD, AWAY_CHORD], bars=8, count=riffs.RIFF_BARS, stays=True), [0, 1] * 4)
        self.assertEqual(riffs.bars_played(chords=[HOME_CHORD, AWAY_CHORD], bars=8, count=riffs.RIFF_BARS, stays=True), [0, 1] * 4)
        self.assertEqual(riffs.bars_played(chords=[HOME_CHORD, AWAY_CHORD], bars=4, count=ONE_BAR, stays=True), [0, None, 0, None])
        self.assertFalse(riffs.is_home(FLAT_SEVEN))

    def test_a_line_is_split_into_its_bars_unless_a_note_is_held_over_a_bar_line(self):
        self.assertIsNone(riffs.split_bars(line=[{notation.DEGREE: 1, notation.STEPS: EIGHTHS + 1}, {notation.REST: EIGHTHS - 1}], eighths=EIGHTHS))
        self.assertEqual(riffs.split_bars(line=[{notation.DEGREE: 1, notation.STEPS: EIGHTHS}, {notation.REST: EIGHTHS}], eighths=EIGHTHS), [[{notation.DEGREE: 1, notation.STEPS: EIGHTHS}], [{notation.REST: EIGHTHS}]])
