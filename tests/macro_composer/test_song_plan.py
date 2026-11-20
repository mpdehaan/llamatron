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

"""The song plan: each section's Energy, what follows from it, the joins, a drum solo, the kinds of hook and a tune that breathes."""

import random
import unittest

from llamatron.composition.setlist import Setlist
from llamatron.macro_composer import arranger, composer, drum_solo, joins, melody, notation, phrasing, song_plan, wizard_limits
from llamatron.macro_composer.song_plan import level_at, loudness_at, SongPlan
from llamatron.macro_composer.wizard_choices import WizardChoices
from llamatron.strings import macro_composer as composer_text
from llamatron.support import version

ROCK = 'rock'
ARENA = 'arena rock'
PUNK = 'punk'
BALLAD = 'six-eight ballad'
SONG_NAME = 'a_song'
KEY_ROOT = 'A'
MAJOR = 'major'
SEED = 11
SEEDS = range(1, 13)
INTRO = 'intro'
VERSE = 'verse'
PRE_CHORUS = 'pre-chorus'
CHORUS = 'chorus'
BRIDGE = 'bridge'
DRUM_SOLO = 'drum solo'
SOLO = 'solo'
ENDING = 'ending'
FORM = [INTRO, VERSE, PRE_CHORUS, CHORUS, VERSE, PRE_CHORUS, CHORUS, BRIDGE, DRUM_SOLO, SOLO, PRE_CHORUS, CHORUS, CHORUS, ENDING]
SECOND_VERSE = 4
FIRST_CHORUS = 3
LAST_CHORUSES = 11
BEFORE_DRUM_SOLO = 7
DRUM_SOLO_PLACE = 8
BEFORE_LAST_CHORUSES = 10
KEYS = 'keys'
VOICES = 'voices'
DRUMS = 'drums'
CHORDS_AT_HOME = [1, 4, 1, 1]
A_BAR = 16
SOLO_BARS = 8
EIGHTHS = 8
KICK = 'kick'
SNARE = 'snare'
CRASH = 'crash'
HAT = 'hat'
TAMB = 'tamb'
LINE = [{notation.STEPS: 2}, {notation.STEPS: 2}, {notation.STEPS: 2}, {notation.STEPS: 2}, {notation.STEPS: 2}, {notation.STEPS: 2}, {notation.STEPS: 2}, {notation.STEPS: 2}]
LINE_STEPS = 16
A_FIGURE = [[{notation.STEPS: 2}, {notation.STEPS: 2}, {notation.STEPS: 2}, {notation.STEPS: 2}]]
FOUR_BARS = 4
TAKES = range(7)
MANY_SOLOS = 8
A_LINE = 'line'
THE_HOOK = 'hook'
THE_SOLOIST = 'solo'
A_KIND_WITH_SOLOS = 'rock and roll'
BLUES = 'blues'
A_TAMBOURINE = 'tambourine'
TOM_LOW = 'tom low'
TWO_PHRASES = 8
A_CHOSEN_FILL = 'toms on four'
A_LEVEL_PLAN = {song_plan.GROWTH: 0, song_plan.CONTRAST: 0}
A_BLUES = 'shuffle'


def song(*, form=FORM, template=ARENA, plan=True, seed=SEED, sections=None):
    made = {arranger.NAME: SONG_NAME, arranger.TITLE: SONG_NAME, arranger.STYLE: ROCK, arranger.TEMPLATE: template, arranger.KEY: {arranger.ROOT: KEY_ROOT, arranger.TYPE: MAJOR},
            arranger.SEED: seed, arranger.FORM: list(form), song_plan.PLAN_OF_SONG: plan}
    if sections is not None:
        made[arranger.SECTIONS] = sections
    return made


def planned(given_song):
    """A song's plan, made as the arranger makes one."""
    style = arranger.style_named(ROCK)
    picks = arranger.picked(style=style, song=given_song)
    chord_entry = arranger.values_of(style=style, trait=arranger.CHORD_TRAIT)[picks[arranger.CHORD_TRAIT]]

    def chords_of(section):
        return [arranger.chord_of(chord) for chord in section.get(arranger.CHORDS) or chord_entry.get(arranger.BY_SECTION, {}).get(section[arranger.KIND]) or chord_entry[arranger.PATTERN]]
    return SongPlan(style=style, song=given_song, form_names=given_song[arranger.FORM], tempo=arranger.tempo_of(style=style, song=given_song, picks=picks), scale_type=MAJOR, chords_of=chords_of)


def sections_of(given_song):
    made = planned(given_song).planned()
    return [made[arranger.SECTIONS][name] for name in made[arranger.FORM]]


class TestEnergy(unittest.TestCase):

    def test_a_kind_that_returns_gains_and_the_last_choruses_take_the_most(self):
        energies = planned(song()).energies()
        self.assertGreater(energies[SECOND_VERSE], energies[FORM.index(VERSE)])
        self.assertGreater(energies[FIRST_CHORUS], energies[FORM.index(VERSE)])
        self.assertEqual(energies[LAST_CHORUSES], max(energies))
        self.assertTrue(all(song_plan.LOWEST_ENERGY <= energy <= song_plan.HIGHEST_ENERGY for energy in energies))

    def test_contrast_pulls_the_sections_apart_and_no_growth_keeps_returns_level(self):
        flat = planned(song(plan={song_plan.CONTRAST: 1})).energies()
        wide = planned(song(plan={song_plan.CONTRAST: song_plan.HIGHEST_ENERGY})).energies()
        self.assertLess(max(flat) - min(flat), max(wide) - min(wide))
        level = planned(song(plan={song_plan.GROWTH: 0})).energies()
        self.assertEqual(level[SECOND_VERSE], level[FORM.index(VERSE)])

    def test_a_song_gives_a_place_its_own_energy(self):
        by_place = [{} for _ in FORM]
        by_place[SECOND_VERSE] = {song_plan.ENERGY: song_plan.LOWEST_ENERGY}
        self.assertEqual(planned(song(plan={song_plan.BY_PLACE: by_place})).energies()[SECOND_VERSE], song_plan.LOWEST_ENERGY)

    def test_loudness_leaves_room_and_a_level_follows_the_change_points(self):
        self.assertEqual(loudness_at(song_plan.LOWEST_ENERGY), song_plan.QUIETEST)
        self.assertEqual(loudness_at(song_plan.HIGHEST_ENERGY), song_plan.LOUDEST)
        self.assertEqual([level_at(energy=energy, points=(1, 4, 7, 9)) for energy in (1, 3, 4, 8, 10)], [1, 1, 2, 3, 4])


class TestWhatFollowsFromEnergy(unittest.TestCase):

    def test_every_place_is_a_section_of_its_own_and_a_louder_one_is_louder(self):
        made = planned(song()).planned()
        self.assertEqual(len(set(made[arranger.FORM])), len(FORM))
        sections = sections_of(song())
        self.assertGreater(sections[FIRST_CHORUS][song_plan.SCENE_SETTINGS][song_plan.SCENE_VELOCITY], sections[FORM.index(VERSE)][song_plan.SCENE_SETTINGS][song_plan.SCENE_VELOCITY])
        rising = sections[FORM.index(PRE_CHORUS)][song_plan.SCENE_SETTINGS]
        self.assertLess(rising[song_plan.SCENE_VELOCITY_IN_START], rising[song_plan.SCENE_VELOCITY])

    def test_a_rising_section_ends_its_climb_at_the_loudness_of_the_section_it_leads_to(self):
        sections = sections_of(song())
        rising = sections[FORM.index(PRE_CHORUS)][song_plan.SCENE_SETTINGS]
        self.assertEqual(FORM.index(PRE_CHORUS) + 1, FIRST_CHORUS)
        self.assertEqual(rising[song_plan.SCENE_VELOCITY], sections[FIRST_CHORUS][song_plan.SCENE_SETTINGS][song_plan.SCENE_VELOCITY])

    def test_players_come_in_with_energy_and_reach_further(self):
        sections = sections_of(song())
        self.assertNotIn(VOICES, sections[FORM.index(VERSE)][song_plan.PLAYS])
        self.assertIn(VOICES, sections[LAST_CHORUSES][song_plan.PLAYS])
        self.assertGreater(sections[LAST_CHORUSES][song_plan.ALLOWS][DRUMS], sections[FORM.index(INTRO)][song_plan.ALLOWS][DRUMS])

    def test_the_kit_s_percussion_comes_in_from_an_energy_up_and_a_song_s_own_plays_all_through(self):
        given = song(form=[VERSE, CHORUS])
        starts = arranger.style_named(ROCK)[song_plan.PLAN_OF_SONG][song_plan.PERCUSSION_FROM]
        energies = planned(given).energies()
        self.assertLess(energies[0], starts)
        self.assertGreaterEqual(energies[1], starts)
        verse, chorus = sections_of(given)
        self.assertEqual(verse[arranger.PICKS][song_plan.PERCUSSION], song_plan.NO_PERCUSSION)
        self.assertNotIn(song_plan.PERCUSSION, chorus[arranger.PICKS])
        own = sections_of({**given, arranger.PICKS: {song_plan.PERCUSSION: A_TAMBOURINE}})
        self.assertTrue(all(song_plan.PERCUSSION not in section[arranger.PICKS] for section in own))

    def test_a_tambourine_is_heard_in_the_chorus_and_not_in_the_verse(self):
        style = arranger.style_named(ROCK)
        style = {**style, arranger.TEMPLATES: {**style[arranger.TEMPLATES], ARENA: {**style[arranger.TEMPLATES][ARENA], song_plan.PERCUSSION: A_TAMBOURINE}}}
        given = arranger.arranged(style=style, song=song(form=[VERSE, CHORUS]))
        verse, chorus = (entry[composer.PLAY] for entry in given[composer.FORM])
        self.assertNotIn(TAMB, verse)
        self.assertIn(TAMB, chorus)

    def test_a_section_arrived_at_from_below_starts_on_a_crash(self):
        sections = sections_of(song())
        self.assertTrue(sections[FIRST_CHORUS][song_plan.CRASH_START])
        self.assertFalse(sections[SECOND_VERSE][song_plan.CRASH_START])

    def test_the_plan_can_leave_the_tunes_as_written(self):
        made = planned(song(plan={song_plan.PHRASING: False})).planned()
        self.assertNotIn(melody.BREATHES, made[arranger.MELODY])
        self.assertIn(melody.BREATHES, planned(song()).planned()[arranger.MELODY])


class TestJoins(unittest.TestCase):

    def test_the_band_stops_before_a_drum_solo_drops_out_once_and_builds_from_a_pre_chorus(self):
        sections = sections_of(song())
        self.assertEqual(sections[BEFORE_DRUM_SOLO][joins.LEAVES][joins.TAIL], joins.STOPS)
        self.assertEqual(sections[BEFORE_LAST_CHORUSES][joins.LEAVES][joins.TAIL], joins.DROP_OUT)
        self.assertEqual(sections[FORM.index(PRE_CHORUS)][joins.LEAVES][joins.TAIL], joins.BUILD)
        dropped = [section for section in sections if section.get(joins.LEAVES, {}).get(joins.TAIL) == joins.DROP_OUT]
        self.assertEqual(len(dropped), 1)

    def test_no_fill_comes_twice_running(self):
        for seed in SEEDS:
            fills = [section.get(joins.LEAVES, {}).get(joins.FILL_OF_JOIN) for section in sections_of(song(seed=seed))]
            for before, after in zip(fills, fills[1:]):
                if before is not None:
                    self.assertNotEqual(before, after)

    def test_a_subgenre_does_only_what_belongs_to_it(self):
        tails = {section.get(joins.LEAVES, {}).get(joins.TAIL) for section in sections_of(song(template=PUNK, form=[VERSE, CHORUS, VERSE, CHORUS, BRIDGE, CHORUS, ENDING]))}
        self.assertNotIn(joins.DROP_OUT, tails)
        self.assertNotIn(joins.BUILD, tails)

    def test_a_last_bar_is_set_up_for_a_section_that_starts_at_home(self):
        sections = {VERSE: {arranger.KIND: VERSE, arranger.CHORDS: CHORDS_AT_HOME}, CHORUS: {arranger.KIND: CHORUS, arranger.CHORDS: CHORDS_AT_HOME}}
        made = sections_of(song(form=[VERSE, CHORUS, ENDING], sections=sections))
        self.assertEqual(made[0][song_plan.LAST_CHORD], song_plan.APPROACH)
        by_place = [{song_plan.SETUP: song_plan.NOT_AT_ALL}, {}, {}]
        self.assertNotIn(song_plan.LAST_CHORD, sections_of(song(form=[VERSE, CHORUS, ENDING], sections=sections, plan={song_plan.BY_PLACE: by_place}))[0])
        self.assertNotIn(song_plan.LAST_CHORD, sections_of(song(form=[VERSE, CHORUS, ENDING], sections=sections, template=PUNK))[0])

    def test_a_figure_is_written_out_with_its_last_bar_as_the_tail_says(self):
        dropped = joins.with_tail(bars=A_FIGURE, count=FOUR_BARS, tail=joins.DROP_OUT, eighths=EIGHTHS // 2)
        self.assertEqual(len(dropped), FOUR_BARS)
        self.assertEqual(dropped[0], A_FIGURE[0])
        self.assertEqual(dropped[-1][-1], {notation.REST: EIGHTHS // 2})
        stopped = joins.with_tail(bars=A_FIGURE, count=FOUR_BARS, tail=joins.STOPS, eighths=0)
        self.assertEqual([place for place, note in enumerate(stopped[-1]) if notation.REST not in note], list(joins.STOP_PLACES))
        self.assertEqual(joins.with_tail(bars=A_FIGURE, count=FOUR_BARS, tail=joins.BUILD, eighths=0)[-1], A_FIGURE[0])

    def test_the_kit_plays_the_tail(self):
        plain = [notation.LOUD, notation.NONE] * (EIGHTHS // 2)
        self.assertEqual(joins.drum_tail(piece=HAT, plain=plain, tail=joins.DROP_OUT, eighths=EIGHTHS // 2), plain[:EIGHTHS // 2] + [notation.NONE] * (EIGHTHS // 2))
        self.assertEqual(joins.drum_tail(piece=HAT, plain=plain, tail=joins.STOPS, eighths=0), [notation.NONE] * EIGHTHS)
        hits = joins.drum_tail(piece=CRASH, plain=[notation.NONE] * EIGHTHS, tail=joins.STOPS, eighths=0)
        self.assertEqual([place for place, hit in enumerate(hits) if hit == notation.LOUD], list(joins.STOP_PLACES))
        build = joins.drum_tail(piece=SNARE, plain=plain, tail=joins.BUILD, eighths=0)
        self.assertEqual(build, [notation.SOFT] * (EIGHTHS // 2) + [notation.LOUD] * (EIGHTHS // 2))
        self.assertEqual(joins.drum_tail(piece=KICK, plain=plain, tail=joins.BUILD, eighths=0), plain)

    def marker(self):
        return arranger.style_named(ROCK)[song_plan.PLAN_OF_SONG][song_plan.MARKER]

    def test_a_phrase_inside_a_section_ends_on_the_marker_and_a_section_of_one_phrase_has_none(self):
        made = sections_of(song(form=[INTRO, VERSE, CHORUS, ENDING], sections={INTRO: {arranger.BARS: song_plan.MARKER_BARS}, VERSE: {arranger.BARS: TWO_PHRASES}}))
        self.assertNotIn(song_plan.MARKER, made[0])
        self.assertEqual((made[1][song_plan.MARKER], made[1][song_plan.MARKER_EVERY]), (self.marker(), song_plan.MARKER_BARS))

    def test_a_song_that_chose_its_fill_or_how_often_fills_come_has_no_marker(self):
        form = [VERSE, CHORUS]
        chosen = {**song(form=form), arranger.PICKS: {arranger.FILLS: A_CHOSEN_FILL}}
        often = {**song(form=form), song_plan.FILLS_COME: song_plan.MARKER_BARS}
        for given in (chosen, often):
            self.assertTrue(all(song_plan.MARKER not in section for section in sections_of(given)))

    def test_the_kit_plays_the_marker_over_the_last_bar_of_a_phrase_and_never_over_the_section_s_last(self):
        style = arranger.style_named(ROCK)
        given = arranger.arranged(style=style, song=song(form=[VERSE, CHORUS], sections={VERSE: {arranger.BARS: TWO_PHRASES}}))
        part = given[composer.PARTS][given[composer.FORM][0][composer.PLAY][TOM_LOW][composer.PART]]
        hits = part[notation.HITS]
        grid = len(hits) // TWO_PHRASES
        stroke = self.marker()[TOM_LOW]
        marked = hits[(song_plan.MARKER_BARS - 1) * grid:song_plan.MARKER_BARS * grid]
        self.assertEqual([hit for hit in marked if hit != notation.NONE], [hit for hit in stroke if hit != notation.NONE])
        self.assertTrue(all(hit == notation.NONE for hit in hits[:(song_plan.MARKER_BARS - 1) * grid]))

    def test_the_last_chorus_is_come_into_on_the_big_fill_whatever_the_rise(self):
        style = arranger.style_named(ROCK)
        big = style[song_plan.PLAN_OF_SONG][arranger.FILLS][song_plan.BIG]
        form = [VERSE, CHORUS, VERSE, BRIDGE, CHORUS]
        # A song with no tail allowed before its last chorus and no rise into it still takes the big fill there.
        given = {**song(form=form, template=PUNK), song_plan.PLAN_OF_SONG: {**A_LEVEL_PLAN, song_plan.LAST_CHORUS: song_plan.LOWEST_ENERGY}}
        made = sections_of(given)
        self.assertEqual(made[3][joins.LEAVES].get(joins.FILL_OF_JOIN), big)


class TestStagedSolos(unittest.TestCase):
    """A kind of section that is staged, as a solo: each time after a song's first it takes another of its shapes."""

    def shapes(self):
        return arranger.style_named(ROCK)[arranger.SECTIONS][SOLO][song_plan.SHAPES]

    def test_the_first_solo_plays_its_own_plan_and_each_after_takes_the_next_shape_in_turn(self):
        self.assertTrue(arranger.style_named(ROCK)[arranger.SECTIONS][SOLO][song_plan.STAGED])
        names = list(self.shapes())
        form = [VERSE, SOLO, VERSE, *[SOLO] * (MANY_SOLOS - 1)]
        found = planned(song(form=form)).shapes()
        self.assertEqual(found[:2], [None, None])
        self.assertEqual(found[2], None)
        self.assertEqual(found[3:], [names[count % len(names)] for count in range(MANY_SOLOS - 1)])
        # No two solos running take one shape.
        self.assertTrue(all(one != another for one, another in zip(found[3:], found[4:])))

    def test_a_stage_has_lines_of_its_own_and_the_hook_is_the_songs(self):
        made = sections_of(song(form=[SOLO] * (len(self.shapes()) + 1)))
        self.assertNotIn(song_plan.SECTION_PLAN, made[0])
        for stage, (name, shape) in enumerate(self.shapes().items(), start=2):
            plan = made[stage - 1][song_plan.SECTION_PLAN]
            with self.subTest(shape=name):
                self.assertEqual(len(plan), len(shape))
                for line, written in zip(plan, shape):
                    self.assertEqual({**line, A_LINE: written[A_LINE]}, written)
                    self.assertEqual(line[A_LINE], written[A_LINE] if written.get(THE_HOOK) else song_plan.STAGE_LINE.format(written[A_LINE], stage))

    def test_a_kind_that_is_not_staged_plays_its_plan_every_time(self):
        self.assertEqual(planned(song(form=[VERSE, CHORUS, VERSE, CHORUS, CHORUS])).shapes(), [None] * 5)
        self.assertTrue(all(song_plan.SECTION_PLAN not in section for section in sections_of(song(form=[VERSE, CHORUS, VERSE, CHORUS]))))

    def test_a_shape_the_song_gives_a_solo_stands_over_its_stage(self):
        own = self.shapes()[list(self.shapes())[-1]]
        made = sections_of({**song(form=[SOLO, SOLO]), song_plan.PLAN_OF_SONG: {song_plan.BY_PLACE: [None, {song_plan.SECTION_PLAN: own}]}})
        self.assertEqual(made[1][song_plan.SECTION_PLAN], own)

    def test_solos_in_a_row_play_tunes_of_their_own(self):
        given = arranger.arranged(style=arranger.style_named(ROCK), song=song(form=[INTRO, SOLO, SOLO, SOLO, ENDING], template=A_KIND_WITH_SOLOS))
        solos = [entry[composer.PLAY][THE_SOLOIST][composer.PART] for entry in given[composer.FORM] if entry[composer.SCENE].startswith(SOLO)]
        self.assertEqual(len(solos), 3)
        self.assertEqual(len(set(solos)), 3)
        self.assertEqual(len({repr(given[composer.PARTS][part]) for part in solos}), 3)

    def test_every_solo_of_every_kind_of_band_music_has_a_player_of_a_tune(self):
        for name in (ROCK, 'sixties_pop', 'soul_funk', 'blues'):
            style = arranger.style_named(name)
            tunes = {role[arranger.ROLE] for role in style[arranger.ROLES] if not role.get(arranger.DRUMS)}
            for template in style[arranger.TEMPLATES]:
                # A kind with no soloist, as punk, plays a solo as the band alone, and disco has no shape with a solo.
                if style[arranger.TEMPLATES][template].get(THE_SOLOIST) == notation.NONE:
                    continue
                if not any(SOLO in shape[arranger.SECTIONS] for shape in arranger.forms_of(style=style, song={arranger.TEMPLATE: template})):
                    continue
                given = arranger.arranged(style=style, song={**song(form=[SOLO, SOLO], template=template), arranger.STYLE: name})
                for entry in given[composer.FORM]:
                    once = [role for role, played in entry[composer.PLAY].items() if role in tunes and isinstance(played, dict) and played.get(composer.ONCE)]
                    with self.subTest(style=name, template=template, scene=entry[composer.SCENE]):
                        self.assertTrue(once)

    def test_the_wizard_says_the_shape_each_solo_takes_and_a_solo_s_own_shape_stands(self):
        choices = WizardChoices()
        choices.set_genre(BLUES)
        choices.set_subgenre(A_BLUES)
        choices.set_seed(SEED)
        solos = [place for place, label in enumerate(choices.get_song_form().section_labels()) if label.startswith(SOLO)]
        self.assertGreater(len(solos), 1)
        names = choices.section(solos[0]).shapes()
        said = [choices.section(place).from_plan(field=wizard_limits.SHAPE_OF_SECTION) for place in solos]
        self.assertEqual(said, [wizard_limits.SHAPE_USUAL, *names[:len(solos) - 1]])
        before = choices.made_for_listening()[0].to_data()
        choices.section(solos[1]).set_own(field=wizard_limits.SHAPE_OF_SECTION, value=names[-1])
        self.assertEqual(choices.section(solos[1]).own(field=wizard_limits.SHAPE_OF_SECTION), names[-1])
        self.assertNotEqual(choices.made_for_listening()[0].to_data(), before)


class TestDrumSolo(unittest.TestCase):

    def test_a_solo_states_a_theme_builds_peaks_and_plays_the_band_in(self):
        bars = drum_solo.solo_bars(bars=SOLO_BARS, seed=SEED)
        self.assertEqual(len(bars), SOLO_BARS)
        theme = [place for place, hit in enumerate(bars[0][drum_solo.SNARE]) if hit != notation.NONE]
        self.assertEqual(len(theme), drum_solo.THEME_STROKES)
        strokes = [sum(1 for piece in drum_solo.PIECES for hit in bar[piece] if hit != notation.NONE) for bar in bars]
        self.assertGreater(strokes[-2], strokes[0])
        self.assertEqual(bars[-2][drum_solo.CRASH][0], notation.LOUD)
        self.assertTrue(any(hit != notation.NONE for hit in bars[-1][drum_solo.TOM_LOW][drum_solo.HALF_BAR:]))

    def test_the_same_seed_gives_the_same_solo_and_another_seed_another(self):
        self.assertEqual(drum_solo.solo_hits(bars=SOLO_BARS, seed=SEED), drum_solo.solo_hits(bars=SOLO_BARS, seed=SEED))
        self.assertTrue(any(drum_solo.solo_hits(bars=SOLO_BARS, seed=seed) != drum_solo.solo_hits(bars=SOLO_BARS, seed=SEED) for seed in SEEDS if seed != SEED))
        self.assertTrue(all(len(hits) == SOLO_BARS * A_BAR for hits in drum_solo.solo_hits(bars=SOLO_BARS, seed=SEED).values()))

    def test_only_the_drummer_plays_a_drum_solo_in_a_song(self):
        given = arranger.arranged(style=arranger.style_named(ROCK), song=song())
        played = given[arranger.FORM][DRUM_SOLO_PLACE][arranger.PLAY]
        self.assertTrue(all(given[arranger.TRACKS][track] == arranger.DRUM_KIT for track in played if track != composer_text.MSG_CHORDS_TRACK))
        self.assertIn(drum_solo.TOM_LOW, played)

    def test_a_drum_solo_in_another_meter_is_the_drummer_alone(self):
        given = arranger.arranged(style=arranger.style_named(ROCK), song=song(template=BALLAD, form=[VERSE, DRUM_SOLO, CHORUS, ENDING], plan=False))
        Setlist.from_data(data=composer.composed(given=given, version=version.VERSION))


class TestPhrasing(unittest.TestCase):

    def test_a_line_ends_early_and_keeps_its_length(self):
        made = phrasing.ended_early(line=LINE, breath=phrasing.SHORT_BREATH)
        self.assertEqual(sum(phrasing.lasts(note) for note in made), LINE_STEPS)
        self.assertEqual(made[-1], {notation.REST: phrasing.SHORT_BREATH})

    def test_the_second_line_is_the_shorter(self):
        longer = phrasing.breathed(line=LINE, grid=EIGHTHS, count=0, dice=random.Random(SEED))
        shorter = phrasing.breathed(line=LINE, grid=EIGHTHS, count=1, dice=random.Random(SEED))
        self.assertGreater(shorter[-1][notation.REST], longer[-1][notation.REST])

    def test_a_note_comes_an_eighth_early(self):
        made = phrasing.pushed(line=LINE, grid=EIGHTHS)
        self.assertEqual(sum(phrasing.lasts(note) for note in made), LINE_STEPS)
        self.assertNotEqual(made, LINE)
        self.assertEqual(LINE[0][notation.STEPS], 2)

    def test_a_bar_not_counted_in_eighths_is_left_alone(self):
        self.assertEqual(phrasing.breathed(line=LINE[:3], grid=6, count=0, dice=random.Random(SEED)), LINE[:3])

    def test_a_planned_song_loads_for_every_subgenre_and_seed(self):
        style = arranger.style_named(ROCK)
        for template in style[arranger.TEMPLATES]:
            for seed in SEEDS:
                with self.subTest(template=template, seed=seed):
                    given = arranger.arranged(style=style, song=song(template=template, seed=seed))
                    Setlist.from_data(data=composer.composed(given=given, version=version.VERSION))
