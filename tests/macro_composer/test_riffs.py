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

"""Tests of a riff, a song's second hook: its notes as drawn, and the riff in the song wizard's choices, who plays it, where, its notes by hand and another take."""

import unittest

from llamatron.composition.file_format import Section
from llamatron.macro_composer import line_edits
from llamatron.macro_composer import riffs
from llamatron.macro_composer.notation import ACCENT, ACCIDENTAL, CHORD, DEGREE, FLAT, GHOST, LEVEL, LOUD, NONE, OCTAVE, REST, STEPS, VELOCITY
from llamatron.macro_composer.riffs import (ACCENT_CHORDS, FIRST_TAKE, HOME, IN_FULL, LEAVES_A_GAP, MOVES_WHOLE, MUTED_ROOTS, RESTS_BETWEEN, RIFF_BAR_COUNT, RIFF_BARS, RIFF_BETWEEN, RIFF_NOTES,
                                            RIFF_UNDER_TUNE, RIFF_WITH_CHORDS, SINGLE_NOTES, STAYS_HOME, heavy_line, riff_line)
from llamatron.macro_composer.wizard_choices import RIFF_EVERYWHERE, RIFF_INTRO_AND_VERSES, RIFF_SETTINGS, RIFF_UNDER_CHORUSES, WizardChoices
from llamatron.strings.macro_composer import MSG_PART_OF_SECTION
from llamatron.support.version import VERSION

A_NAME = 'made'
A_SEED = 11
ANOTHER_SEED = 12
EIGHTHS = 8
A_GENRE = 'rock'
A_SUBGENRE = 'hard rock'
A_GENRE_OF_NO_FIGURES = 'experimental'
THE_GUITAR = 'guitar'
THE_BASS = 'bass'
THE_SINGER = 'lead'
THE_RIFF = 'riff'
NOT_A_WAY = 'sideways'
MANY_SEEDS = 40
A_KIND_WITH_NO_RIFF = 'punk'
A_PROGRESSION_AT_HOME = 'riff on one'
THE_KICK = 'kick'
A_VERSE = 'verse'
MAJOR = 'major'
MINOR = 'minor'
HOME_CHORD = {DEGREE: 1}
AWAY_CHORD = {DEGREE: 4}
FLAT_SEVEN = {DEGREE: 7, ACCIDENTAL: FLAT}
NOT_A_SETTING = 'sideways'
ONE_BAR = 1


def of_hard_rock():
    """Choices for the kind of music that is built on a riff, with the riff the kind gives."""
    choices = WizardChoices()
    choices.set_genre(A_GENRE)
    choices.set_subgenre(A_SUBGENRE)
    choices.set_seed(A_SEED)
    return choices


def lasts(note):
    return note.get(REST, note.get(STEPS))


def places(line):
    """Each note of a line with the eighth it starts on."""
    at = 0
    found = []
    for note in line:
        found.append((at, note))
        at += lasts(note)
    return found


def chosen(*, genre=A_GENRE, subgenre=A_SUBGENRE):
    choices = WizardChoices()
    choices.set_genre(genre)
    choices.set_subgenre(subgenre if genre == A_GENRE else choices.subgenres()[0])
    choices.set_seed(A_SEED)
    # A song with no riff until one is given: the riff a kind of music is built on is taken away.
    choices.set_riff(players=[])
    return choices


def made(choices):
    return choices.made_setlist(name=A_NAME, version=VERSION)


def patterns(choices):
    return made(choices).to_data()[Section.PATTERNS]


class TestRiffLine(unittest.TestCase):
    """A riff's notes as drawn."""

    __slots__ = ()

    def test_a_riff_is_two_bars_that_start_on_the_root_the_second_answering_the_first(self):
        for seed in range(MANY_SEEDS):
            line = riff_line(seed=seed, take=FIRST_TAKE, eighths=EIGHTHS)
            self.assertEqual(line_edits.steps_of(line), RIFF_BARS * EIGHTHS)
            self.assertEqual((line[0][DEGREE], line[0].get(OCTAVE, 0)), HOME)
            first, second = self.bars(line)
            self.assertEqual([line_edits.length_of(note) for note in first], [line_edits.length_of(note) for note in second])
            self.assertEqual([REST in note for note in first], [REST in note for note in second])
            self.assertEqual(first[0], second[0])

    def bars(self, line):
        half = len(line) // RIFF_BARS
        return line[:half], line[half:]

    def test_a_seed_and_a_take_make_one_riff_and_another_take_another(self):
        self.assertEqual(riff_line(seed=A_SEED, take=FIRST_TAKE, eighths=EIGHTHS), riff_line(seed=A_SEED, take=FIRST_TAKE, eighths=EIGHTHS))
        self.assertNotEqual(riff_line(seed=A_SEED, take=FIRST_TAKE, eighths=EIGHTHS), riff_line(seed=A_SEED, take=FIRST_TAKE + 1, eighths=EIGHTHS))
        self.assertNotEqual(riff_line(seed=A_SEED, take=FIRST_TAKE, eighths=EIGHTHS), riff_line(seed=ANOTHER_SEED, take=FIRST_TAKE, eighths=EIGHTHS))


class TestHeavyRiff(unittest.TestCase):
    """A riff of chords on its accents, as drawn."""

    __slots__ = ()

    def test_the_riff_starts_on_the_roots_chord_and_has_an_accent_off_the_beat_in_every_bar(self):
        for seed in range(MANY_SEEDS):
            for gap in (False, True):
                line = heavy_line(seed=seed, take=FIRST_TAKE, eighths=EIGHTHS, gap=gap)
                with self.subTest(seed=seed, gap=gap):
                    self.assertEqual(sum(lasts(note) for note in line), RIFF_BARS * EIGHTHS)
                    first = line[0]
                    self.assertEqual((first[DEGREE], first[CHORD], first[LEVEL]), (HOME[0], riffs.POWER_CHORD, ACCENT))
                    accents = [at for at, note in places(line) if note.get(LEVEL) == ACCENT]
                    for bar in range(RIFF_BARS):
                        self.assertIn(bar * EIGHTHS, accents)
                        self.assertTrue(any(at % 2 for at in accents if at // EIGHTHS == bar))
                    # Every accent is a chord, and nothing else is.
                    self.assertTrue(all((CHORD in note) == (note.get(LEVEL) == ACCENT) for note in line if REST not in note))

    def test_half_the_notes_or_more_are_the_root_and_the_last_are_single_notes_that_lead_back(self):
        for seed in range(MANY_SEEDS):
            line = heavy_line(seed=seed, take=FIRST_TAKE, eighths=EIGHTHS)
            sounding = [note for note in line if REST not in note]
            with self.subTest(seed=seed):
                self.assertGreaterEqual(2 * sum(riffs.is_root(note) for note in sounding), len(sounding))
                tail = [tuple(note[DEGREE] for note in line[-len(ending):]) for ending in riffs.TAILS]
                self.assertIn(True, [found == tuple(place[0] for place in ending) for found, ending in zip(tail, riffs.TAILS)])
                self.assertTrue(all(CHORD not in note and LEVEL not in note and note[STEPS] == 1 for note in line[-2:]))

    def test_between_the_accents_lie_short_quiet_roots_or_rests(self):
        for seed in range(MANY_SEEDS):
            muted = heavy_line(seed=seed, take=FIRST_TAKE, eighths=EIGHTHS, between=MUTED_ROOTS)
            rests = heavy_line(seed=seed, take=FIRST_TAKE, eighths=EIGHTHS, between=RESTS_BETWEEN)
            with self.subTest(seed=seed):
                self.assertTrue(all(riffs.is_root(note) and note[riffs.GATE] == riffs.MUTED_GATE and note[STEPS] == 1 for note in muted if note.get(LEVEL) == GHOST))
                self.assertFalse(any(REST in note for note in muted))
                self.assertFalse(any(note.get(LEVEL) == GHOST for note in rests))

    def test_a_riff_of_one_bar_is_the_last_bar_and_a_gap_empties_the_second_half_of_the_first(self):
        one = heavy_line(seed=A_SEED, take=FIRST_TAKE, eighths=EIGHTHS, bars=ONE_BAR)
        self.assertEqual(riffs.bars_of(line=one, eighths=EIGHTHS), ONE_BAR)
        self.assertTrue(all(CHORD not in note for note in one[-2:]))
        for seed in range(MANY_SEEDS):
            first, last = riffs.split_bars(line=heavy_line(seed=seed, take=FIRST_TAKE, eighths=EIGHTHS, gap=True), eighths=EIGHTHS)
            self.assertEqual(first[-1], {REST: EIGHTHS // 2})
            self.assertFalse(any(REST in note for note in last))
            # Both bars start alike: the last bar is the first again, with the tail.
            self.assertEqual(first[0], last[0])
        # A gap is the first bar's of two, and a riff of one bar has none.
        self.assertEqual(heavy_line(seed=A_SEED, take=FIRST_TAKE, eighths=EIGHTHS, bars=ONE_BAR, gap=True), one)

    def test_the_third_and_the_seventh_are_flattened_over_a_scale_that_has_them_major(self):
        self.assertEqual(riffs.flattened_in(MAJOR), riffs.FLATTENED)
        self.assertEqual(riffs.flattened_in(MINOR), ())
        for seed in range(MANY_SEEDS):
            line = heavy_line(seed=seed, take=FIRST_TAKE, eighths=EIGHTHS, flattened=riffs.FLATTENED)
            plain = heavy_line(seed=seed, take=FIRST_TAKE, eighths=EIGHTHS)
            self.assertTrue(all(note.get(ACCIDENTAL) == FLAT for note in line if note.get(DEGREE) in riffs.FLATTENED))
            self.assertEqual([note.get(DEGREE) for note in line], [note.get(DEGREE) for note in plain])

    def test_a_seed_and_a_take_make_one_riff_and_others_another(self):
        self.assertEqual(heavy_line(seed=A_SEED, take=FIRST_TAKE, eighths=EIGHTHS), heavy_line(seed=A_SEED, take=FIRST_TAKE, eighths=EIGHTHS))
        self.assertGreater(len({repr(heavy_line(seed=seed, take=FIRST_TAKE, eighths=EIGHTHS)) for seed in range(MANY_SEEDS)}), MANY_SEEDS // 2)
        self.assertGreater(len({repr(heavy_line(seed=A_SEED, take=take, eighths=EIGHTHS)) for take in range(MANY_SEEDS)}), MANY_SEEDS // 2)

    def test_a_second_player_plays_the_notes_alone_and_a_kick_strikes_the_accents(self):
        line = heavy_line(seed=A_SEED, take=FIRST_TAKE, eighths=EIGHTHS)
        under = riffs.single(line)
        self.assertFalse(any(CHORD in note for note in under))
        self.assertEqual([{field: value for field, value in note.items() if field != CHORD} for note in line], under)
        bars = riffs.accent_bars(line=line, eighths=EIGHTHS)
        self.assertEqual([len(bar) for bar in bars], [EIGHTHS] * RIFF_BARS)
        struck = [at for at, hit in enumerate(hit for bar in bars for hit in bar) if hit == LOUD]
        self.assertEqual(struck, [at for at, note in places(line) if note.get(LEVEL) == ACCENT])
        self.assertEqual({hit for bar in bars for hit in bar}, {LOUD, NONE})

    def test_a_riff_that_stays_plays_over_the_home_chord_where_the_section_is_mostly_at_home(self):
        at_home = [HOME_CHORD] * 4 + [AWAY_CHORD, FLAT_SEVEN] + [HOME_CHORD] * 2
        self.assertEqual(riffs.bars_played(chords=at_home, bars=8, count=RIFF_BARS, stays=True), [0, 1, 0, 1, None, None, 0, 1])
        self.assertEqual(riffs.bars_played(chords=at_home, bars=8, count=RIFF_BARS, stays=False), [0, 1] * 4)
        # Fewer than half the bars at home, or never two bars together: the riff moves with each chord.
        self.assertEqual(riffs.bars_played(chords=[HOME_CHORD, AWAY_CHORD, AWAY_CHORD, AWAY_CHORD], bars=8, count=RIFF_BARS, stays=True), [0, 1] * 4)
        self.assertEqual(riffs.bars_played(chords=[HOME_CHORD, AWAY_CHORD], bars=8, count=RIFF_BARS, stays=True), [0, 1] * 4)
        self.assertEqual(riffs.bars_played(chords=[HOME_CHORD, AWAY_CHORD], bars=4, count=ONE_BAR, stays=True), [0, None, 0, None])
        self.assertFalse(riffs.is_home(FLAT_SEVEN))

    def test_a_line_is_split_into_its_bars_unless_a_note_is_held_over_a_bar_line(self):
        self.assertIsNone(riffs.split_bars(line=[{DEGREE: 1, STEPS: EIGHTHS + 1}, {REST: EIGHTHS - 1}], eighths=EIGHTHS))
        self.assertEqual(riffs.split_bars(line=[{DEGREE: 1, STEPS: EIGHTHS}, {REST: EIGHTHS}], eighths=EIGHTHS), [[{DEGREE: 1, STEPS: EIGHTHS}], [{REST: EIGHTHS}]])


class TestWizardRiffOfAKind(unittest.TestCase):
    """The riff a kind of music is built on, and a riff's settings."""

    __slots__ = ()

    def test_hard_rock_has_its_riff_before_any_is_given_and_another_kind_has_none(self):
        choices = of_hard_rock()
        self.assertTrue(choices.has_riff())
        self.assertEqual(choices.get_riff_players(), [THE_GUITAR, THE_BASS])
        self.assertEqual(choices.get_riff_said(), RIFF_INTRO_AND_VERSES)
        self.assertEqual([choices.get_riff_setting(field) for field in (RIFF_NOTES, RIFF_WITH_CHORDS, RIFF_UNDER_TUNE)], [ACCENT_CHORDS, STAYS_HOME, LEAVES_A_GAP])
        choices.set_subgenre(A_KIND_WITH_NO_RIFF)
        self.assertFalse(choices.has_riff())
        choices.set_subgenre(A_SUBGENRE)
        self.assertTrue(choices.has_riff())

    def test_the_kinds_riff_is_taken_away_and_stays_away_in_the_song_kept(self):
        choices = of_hard_rock()
        with_riff = patterns(choices)
        choices.set_riff(players=[])
        self.assertFalse(choices.has_riff())
        self.assertNotEqual(patterns(choices), with_riff)
        self.assertFalse(WizardChoices.from_data(choices.to_data()).has_riff())
        kept = WizardChoices.from_data(of_hard_rock().to_data())
        self.assertTrue(kept.has_riff())
        self.assertEqual(patterns(kept), with_riff)

    def test_the_guitar_plays_the_chords_the_bass_the_notes_alone_and_the_kick_the_accents(self):
        choices = of_hard_rock()
        choices.set_riff_setting(field=RIFF_WITH_CHORDS, value=MOVES_WHOLE)
        made = patterns(choices)
        guitar = made[MSG_PART_OF_SECTION.format(THE_GUITAR, THE_RIFF)]
        bass = made[MSG_PART_OF_SECTION.format(THE_BASS, THE_RIFF)]
        self.assertTrue(any(guitar[CHORD]))
        self.assertFalse(any(bass.get(CHORD) or []))
        self.assertEqual([degree is None for degree in guitar[DEGREE]], [degree is None for degree in bass[DEGREE]])
        # The accents are the loudest of the guitar's notes, and the muted roots the quietest.
        accents = choices.riff_kick()
        self.assertTrue(accents)
        loud = [guitar[VELOCITY][step] for step in accents]
        others = [velocity for step, velocity in enumerate(guitar[VELOCITY]) if velocity is not None and step not in accents]
        self.assertGreater(min(loud), max(others))
        kick = next(pattern for name, pattern in made.items() if name.startswith(THE_KICK) and A_VERSE in name)
        per_eighth = len(kick[VELOCITY]) // (choices.section_bars(choices.riff_scene() + 1) * EIGHTHS) or 1
        first_bars = [step // per_eighth for step, velocity in enumerate(kick[VELOCITY]) if velocity is not None and not step % per_eighth and step // per_eighth < RIFF_BARS * EIGHTHS]
        self.assertEqual(first_bars, accents)

    def test_a_riff_of_single_notes_leaves_the_kick_alone(self):
        choices = of_hard_rock()
        choices.set_riff_setting(field=RIFF_NOTES, value=SINGLE_NOTES)
        self.assertIsNone(choices.riff_kick())
        without = of_hard_rock()
        without.set_riff(players=[])
        kicks = lambda made: {name: pattern for name, pattern in made.items() if name.startswith(THE_KICK)}
        self.assertEqual(kicks(patterns(choices)), kicks(patterns(without)))
        choices.set_riff_setting(field=RIFF_NOTES, value=ACCENT_CHORDS)
        self.assertNotEqual(kicks(patterns(choices)), kicks(patterns(without)))
        choices.set_piece_on(piece=THE_KICK, on=False)
        self.assertIsNone(choices.riff_kick())

    def test_each_setting_offered_changes_the_song_and_the_settings_follow_how_the_riff_is_made(self):
        choices = of_hard_rock()
        # A progression that is at home for four bars and then away, over which a riff that stays is heard to.
        choices.set_way(trait=choices.progression_trait(), value=A_PROGRESSION_AT_HOME)
        self.assertEqual(choices.riff_settings_offered(), [RIFF_NOTES, RIFF_BAR_COUNT, RIFF_BETWEEN, RIFF_UNDER_TUNE, RIFF_WITH_CHORDS])
        for field in choices.riff_settings_offered():
            other = next(value for value in RIFF_SETTINGS[field] if value != choices.get_riff_setting(field))
            trial = WizardChoices.from_data(choices.to_data())
            trial.set_riff_setting(field=field, value=other)
            with self.subTest(field=field):
                self.assertEqual(trial.get_riff_setting(field), other)
                self.assertNotEqual(patterns(trial), patterns(choices))
        choices.set_riff_setting(field=RIFF_BAR_COUNT, value=ONE_BAR)
        self.assertNotIn(RIFF_UNDER_TUNE, choices.riff_settings_offered())
        self.assertEqual(riffs.bars_of(line=choices.riff_line(), eighths=EIGHTHS), ONE_BAR)
        choices.set_riff_setting(field=RIFF_NOTES, value=SINGLE_NOTES)
        self.assertEqual([field for field in choices.riff_settings_offered() if field != RIFF_WITH_CHORDS], [RIFF_NOTES])
        self.assertEqual(riffs.bars_of(line=choices.riff_line(), eighths=EIGHTHS), RIFF_BARS)

    def test_notes_written_by_hand_are_drawn_no_way(self):
        choices = of_hard_rock()
        line = choices.riff_line()
        moved = [dict(note) for note in line]
        last = next(count for count in reversed(range(len(moved))) if REST not in moved[count])
        moved[last] = line_edits.at_place(note=moved[last], place=line_edits.place_of(moved[last]) + 1)
        choices.set_riff_line(moved)
        self.assertTrue(choices.riff_is_own())
        self.assertEqual([field for field in choices.riff_settings_offered() if field != RIFF_WITH_CHORDS], [])
        # The riff's chords and its quiet roots are still the riff's, and the kick still strikes its accents.
        self.assertEqual(choices.riff_kick(), of_hard_rock().riff_kick())
        with self.assertRaises(ValueError):
            choices.set_riff_line(moved[:-1])

    def test_what_is_no_setting_is_refused_and_a_song_with_no_riff_has_none(self):
        choices = of_hard_rock()
        for field, value in ((NOT_A_SETTING, IN_FULL), (RIFF_NOTES, NOT_A_SETTING), (RIFF_BAR_COUNT, RIFF_BARS + 1)):
            with self.assertRaises(ValueError):
                choices.set_riff_setting(field=field, value=value)
        self.assertEqual(choices.to_data(), of_hard_rock().to_data())
        choices.set_riff(players=[])
        self.assertEqual(choices.riff_settings_offered(), [])
        with self.assertRaises(ValueError):
            choices.set_riff_setting(field=RIFF_NOTES, value=SINGLE_NOTES)

    def test_the_usual_way_of_a_setting_is_not_kept(self):
        choices = of_hard_rock()
        choices.set_riff_setting(field=RIFF_BETWEEN, value=RESTS_BETWEEN)
        self.assertNotEqual(choices.to_data(), of_hard_rock().to_data())
        choices.set_riff_setting(field=RIFF_BETWEEN, value=MUTED_ROOTS)
        self.assertEqual(choices.to_data(), of_hard_rock().to_data())


class TestWizardRiff(unittest.TestCase):
    """The riff in the wizard's choices."""

    __slots__ = ()

    def test_a_song_has_no_riff_until_a_player_of_a_figure_is_given_one(self):
        choices = chosen()
        self.assertFalse(choices.has_riff())
        self.assertIsNone(choices.riff_line())
        self.assertIsNone(choices.riff_notes())
        offered = choices.riff_players_offered()
        self.assertIn([THE_GUITAR], offered)
        self.assertIn([THE_GUITAR, THE_BASS], offered)
        self.assertNotIn([THE_SINGER], offered)
        self.assertEqual(chosen(genre=A_GENRE_OF_NO_FIGURES).riff_players_offered(), [])
        self.assertEqual(WizardChoices().riff_players_offered(), [])

    def test_the_riff_takes_the_place_of_its_players_figures_in_the_sections_it_is_played_in(self):
        choices = chosen()
        usual = patterns(choices)
        choices.set_riff(players=[THE_GUITAR, THE_BASS])
        self.assertEqual(choices.get_riff_players(), [THE_GUITAR, THE_BASS])
        self.assertEqual(choices.get_riff_said(), RIFF_INTRO_AND_VERSES)
        with_riff = patterns(choices)
        with_riff_made = made(choices).to_data()
        self.assertNotEqual(with_riff, usual)
        for role in (THE_GUITAR, THE_BASS):
            self.assertIn(MSG_PART_OF_SECTION.format(role, THE_RIFF), with_riff)
        song = made(choices).get_song(A_NAME)
        riff_scenes = [scene.get_name() for scene in song.get_scenes() if MSG_PART_OF_SECTION.format(THE_GUITAR, THE_RIFF) in str(scene.to_data())]
        self.assertTrue(riff_scenes)
        self.assertTrue(all(name.startswith(('intro', 'verse')) for name in riff_scenes))
        choices.set_riff(players=[THE_GUITAR, THE_BASS], said=RIFF_UNDER_CHORUSES)
        self.assertEqual(choices.get_riff_said(), RIFF_UNDER_CHORUSES)
        # The same riff, played in other sections: the patterns may be the same ones, and the scenes that play them differ.
        self.assertNotEqual(made(choices).to_data(), with_riff_made)
        choices.set_riff(players=[])
        self.assertFalse(choices.has_riff())
        self.assertEqual(patterns(choices), usual)

    def test_another_take_is_another_riff_and_notes_by_hand_are_the_riff(self):
        choices = chosen()
        choices.set_riff(players=[THE_BASS], said=RIFF_EVERYWHERE)
        first = choices.riff_line()
        choices.new_riff()
        second = choices.riff_line()
        self.assertNotEqual(first, second)
        written = line_edits.moved(line=second, step=0, by=2)
        choices.set_riff_line(written)
        self.assertTrue(choices.riff_is_own())
        self.assertEqual(line_edits.place_of(choices.riff_line()[0]), line_edits.place_of(second[0]) + 2)
        steps, in_bar, notes = choices.riff_notes()
        self.assertEqual((steps, in_bar), (RIFF_BARS * EIGHTHS, EIGHTHS))
        self.assertEqual(len(notes), len([note for note in written if REST not in note]))
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual(again.riff_line(), choices.riff_line())
        self.assertEqual(patterns(again), patterns(choices))
        choices.set_riff_line(None)
        self.assertEqual(choices.riff_line(), second)

    def test_what_is_no_riff_is_refused_and_a_change_of_genre_leaves_the_riff_behind(self):
        choices = chosen()
        for refused in (dict(players=[THE_SINGER]), dict(players=[THE_BASS], said=NOT_A_WAY)):
            with self.assertRaises(ValueError):
                choices.set_riff(**refused)
        for without in (choices.new_riff, lambda: choices.set_riff_line([])):
            with self.assertRaises(ValueError):
                without()
        choices.set_riff(players=[THE_BASS])
        with self.assertRaises(ValueError):
            choices.set_riff_line(choices.riff_line()[:1])
        choices.set_genre(A_GENRE_OF_NO_FIGURES)
        choices.set_subgenre(choices.subgenres()[0])
        self.assertFalse(choices.has_riff())

    def test_every_genre_s_riff_makes_a_song_wherever_it_is_played(self):
        for genre in ('rock', 'sixties_pop', 'soul_funk', 'blues', 'electronic'):
            choices = chosen(genre=genre)
            for players in (choices.riff_players_offered()[0], choices.riff_players_offered()[-1]):
                for said in choices.riff_said_offered():
                    with self.subTest(genre=genre, players=players, said=said):
                        choices.set_riff(players=players, said=said)
                        made(choices)
