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
"""How loud a player is: the four named levels, a player's dynamics, a style's lean on each beat, and the wizard's choices of them."""

from fractions import Fraction
import unittest

from llamatron.composition.file_format import Section
from llamatron.macro_composer import arranger, loudness, notation
from llamatron.macro_composer.notation import drum_rows, tune_rows
from llamatron.macro_composer.wizard_choices import WizardChoices
from llamatron.strings import errors
from llamatron.support import version
from tests.support.ui_testing import fixed_text

A_NAME = 'a_song'
A_SEED = 3
ROCK = 'rock'
HARD_ROCK = 'hard rock'
SOUL_FUNK = 'soul_funk'
FUNK = 'funk'
DISCO = 'disco'
THE_DRUMS = 'drums'
THE_BASS = 'bass'
THE_LEAD = 'lead'
NOT_A_PLAYER = 'kazoo'
NOT_A_LEVEL = 'loudest'
A_KICK = 'kick'
A_SNARE = 'snare'
A_SIXTEENTH = '1/16'
A_QUARTER = '1/4'
COMMON_TIME = '4/4'
AN_OCTAVE = 4
A_VELOCITY = 100
AN_ACCENT = 120
A_SOFT = 80
A_GHOST = 30
A_LEAN = 10
QUIET = 60
LOUDER = 110
TOO_LOUD = notation.HIGHEST_VELOCITY + 1
TOO_WIDE = loudness.MOST_DYNAMICS + 1
A_SNARE_BAR = 'verse'


def chosen(*, genre=ROCK, subgenre=HARD_ROCK):
    choices = WizardChoices()
    choices.set_genre(genre)
    choices.set_subgenre(subgenre)
    choices.set_seed(A_SEED)
    return choices


def patterns(choices):
    return choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()[Section.PATTERNS]


def sounded(pattern):
    return [velocity for velocity in pattern[notation.VELOCITY] if velocity is not None]


class TestLevels(unittest.TestCase):
    """The four levels of a drum and of a player of notes, a song's own, and a player's dynamics."""

    __slots__ = ()

    def test_a_drums_levels_follow_from_its_normal_stroke_or_are_each_said(self):
        levels = loudness.drum_levels(A_VELOCITY)
        self.assertEqual(levels[loudness.NORMAL], A_VELOCITY)
        self.assertEqual(levels[notation.SOFT], int(A_VELOCITY * loudness.SOFT_SHARE))
        self.assertEqual(levels[notation.GHOST], int(A_VELOCITY * loudness.GHOST_SHARE))
        self.assertEqual(levels[notation.ACCENT], A_VELOCITY + loudness.ACCENT_ABOVE)
        self.assertEqual(loudness.drum_levels({loudness.NORMAL: A_VELOCITY, notation.GHOST: A_GHOST})[notation.GHOST], A_GHOST)
        self.assertEqual(loudness.drum_levels(notation.HIGHEST_VELOCITY)[notation.ACCENT], notation.HIGHEST_VELOCITY)
        self.assertEqual(list(levels), list(loudness.LEVELS))

    def test_a_note_players_levels_lie_at_set_distances_from_the_players_velocity(self):
        levels = loudness.note_levels(A_VELOCITY)
        self.assertEqual([levels[level] - A_VELOCITY for level in loudness.LEVELS], [-loudness.GHOST_BELOW, -loudness.SOFT_BELOW, 0, loudness.ACCENT_ABOVE])

    def test_a_songs_own_normal_level_carries_the_others_but_for_those_it_also_gives(self):
        levels = loudness.note_levels(A_VELOCITY)
        moved = loudness.with_own(levels=levels, own={loudness.NORMAL: QUIET})
        self.assertEqual([moved[level] - QUIET for level in loudness.LEVELS], [levels[level] - A_VELOCITY for level in loudness.LEVELS])
        both = loudness.with_own(levels=levels, own={loudness.NORMAL: QUIET, notation.ACCENT: AN_ACCENT, NOT_A_LEVEL: A_GHOST})
        self.assertEqual(both[notation.ACCENT], AN_ACCENT)
        self.assertNotIn(NOT_A_LEVEL, both)
        self.assertEqual(loudness.with_own(levels=levels, own=None), levels)

    def test_dynamics_move_every_level_toward_or_away_from_the_normal_one(self):
        levels = loudness.note_levels(A_VELOCITY)
        self.assertEqual(loudness.spread(levels=levels, dynamics=loudness.USUAL_DYNAMICS), levels)
        self.assertEqual(set(loudness.spread(levels=levels, dynamics=loudness.LEAST_DYNAMICS).values()), {A_VELOCITY})
        wide = loudness.spread(levels=levels, dynamics=loudness.MOST_DYNAMICS)
        self.assertEqual(wide[notation.SOFT], A_VELOCITY - 2 * loudness.SOFT_BELOW)
        self.assertEqual(wide[notation.ACCENT], A_VELOCITY + 2 * loudness.ACCENT_ABOVE)
        self.assertEqual(loudness.spread(levels={loudness.NORMAL: A_VELOCITY, notation.ACCENT: notation.HIGHEST_VELOCITY}, dynamics=loudness.MOST_DYNAMICS)[notation.ACCENT], notation.HIGHEST_VELOCITY)

    def test_a_piece_of_the_kit_follows_the_kits_levels_in_proportion(self):
        kit = loudness.drum_levels(A_VELOCITY)
        piece = loudness.drum_levels(QUIET)
        self.assertEqual(loudness.in_proportion(levels=piece, kit=kit, chosen=kit), piece)
        halved = loudness.in_proportion(levels=piece, kit=kit, chosen={**kit, loudness.NORMAL: A_VELOCITY // 2})
        self.assertEqual(halved[loudness.NORMAL], QUIET // 2)
        self.assertEqual(halved[notation.SOFT], piece[notation.SOFT])


class TestLevelsInAPart(unittest.TestCase):
    """A drum's bar and a tune's notes at the named levels."""

    __slots__ = ()

    def test_a_drums_bar_plays_each_stroke_at_its_level(self):
        hits = [notation.ACCENT, notation.LOUD, notation.SOFT, notation.GHOST, notation.NONE]
        rows = drum_rows(drum=A_SNARE, hits=hits, loud=A_VELOCITY, soft=A_SOFT, step_size=A_SIXTEENTH, accent=AN_ACCENT, ghost=A_GHOST)
        self.assertEqual(rows[notation.VELOCITY], [AN_ACCENT, A_VELOCITY, A_SOFT, A_GHOST, None])
        self.assertEqual(rows[notation.DEGREE][-1], None)

    def test_an_accent_with_no_velocity_is_a_loud_stroke_and_a_ghost_note_a_soft_one(self):
        rows = drum_rows(drum=A_SNARE, hits=[notation.ACCENT, notation.GHOST], loud=A_VELOCITY, soft=A_SOFT, step_size=A_SIXTEENTH)
        self.assertEqual(rows[notation.VELOCITY], [A_VELOCITY, A_SOFT])

    def test_a_tunes_stresses_reach_for_the_parts_own_accent_and_soft_note(self):
        line = [{notation.DEGREE: 1, notation.STEPS: 1, notation.STRESS: notation.PEAK}, {notation.DEGREE: 2, notation.STEPS: 1, notation.STRESS: notation.PICKUP}, {notation.DEGREE: 3, notation.STEPS: 1}]
        usual = tune_rows(lines=[line], octave=AN_OCTAVE, velocity=A_VELOCITY, step_size=A_SIXTEENTH)
        own = tune_rows(lines=[line], octave=AN_OCTAVE, velocity=A_VELOCITY, step_size=A_SIXTEENTH, levels={notation.ACCENT: AN_ACCENT, notation.SOFT: A_SOFT})
        flat = tune_rows(lines=[line], octave=AN_OCTAVE, velocity=A_VELOCITY, step_size=A_SIXTEENTH, levels={notation.ACCENT: A_VELOCITY, notation.SOFT: A_VELOCITY})
        self.assertEqual(usual[notation.VELOCITY], [A_VELOCITY + 12, A_VELOCITY - 8, A_VELOCITY])
        self.assertEqual(own[notation.VELOCITY], [AN_ACCENT, A_SOFT, A_VELOCITY])
        self.assertEqual(flat[notation.VELOCITY], [A_VELOCITY] * 3)

    def test_a_note_says_the_level_it_is_played_at(self):
        line = [{notation.DEGREE: 1, notation.STEPS: 1, notation.LEVEL: notation.GHOST}, {notation.DEGREE: 1, notation.STEPS: 1, notation.LEVEL: notation.ACCENT}, {notation.DEGREE: 1, notation.STEPS: 1, notation.LEVEL: notation.SOFT}]
        rows = tune_rows(lines=[line], octave=AN_OCTAVE, velocity=A_VELOCITY, step_size=A_SIXTEENTH, levels={notation.ACCENT: AN_ACCENT, notation.SOFT: A_SOFT, notation.GHOST: A_GHOST})
        self.assertEqual(rows[notation.VELOCITY], [A_GHOST, AN_ACCENT, A_SOFT])


class TestLean(unittest.TestCase):
    """A style's lean on each beat of the bar, on the drums."""

    __slots__ = ()

    def pattern(self):
        return {notation.STEPS: 16, notation.STEP_SIZE: A_SIXTEENTH, notation.VELOCITY: [A_VELOCITY, None, A_VELOCITY, None] * 4}

    def test_the_strokes_on_a_beat_move_by_the_lean_on_that_beat_and_the_others_stay(self):
        leant = arranger.leaning(pattern=self.pattern(), profile=[A_LEAN, 0, -A_LEAN, 0], meter=COMMON_TIME, dynamics=loudness.USUAL_DYNAMICS)
        self.assertEqual(leant[notation.VELOCITY][0::4], [A_VELOCITY + A_LEAN, A_VELOCITY, A_VELOCITY - A_LEAN, A_VELOCITY])
        self.assertEqual(leant[notation.VELOCITY][2::4], [A_VELOCITY] * 4)
        self.assertEqual(leant[notation.VELOCITY][1::2], [None] * 8)

    def test_the_lean_goes_as_far_as_the_drummers_dynamics(self):
        flat = arranger.leaning(pattern=self.pattern(), profile=[A_LEAN, 0, 0, 0], meter=COMMON_TIME, dynamics=loudness.LEAST_DYNAMICS)
        wide = arranger.leaning(pattern=self.pattern(), profile=[A_LEAN, 0, 0, 0], meter=COMMON_TIME, dynamics=loudness.MOST_DYNAMICS)
        self.assertEqual(flat[notation.VELOCITY], self.pattern()[notation.VELOCITY])
        self.assertEqual(wide[notation.VELOCITY][0], A_VELOCITY + 2 * A_LEAN)

    def test_a_pattern_of_two_bars_leans_in_each_bar(self):
        two_bars = {notation.STEPS: 8, notation.STEP_SIZE: A_QUARTER, notation.VELOCITY: [A_VELOCITY] * 8}
        leant = arranger.leaning(pattern=two_bars, profile=[A_LEAN, 0, 0, 0], meter=COMMON_TIME, dynamics=loudness.USUAL_DYNAMICS)
        self.assertEqual(leant[notation.VELOCITY], [A_VELOCITY + A_LEAN, A_VELOCITY, A_VELOCITY, A_VELOCITY] * 2)

    def test_funk_lands_on_the_one_and_disco_does_not(self):
        funk = arranger.style_in(style=arranger.style_named(SOUL_FUNK), template=FUNK)
        disco = arranger.style_in(style=arranger.style_named(SOUL_FUNK), template=DISCO)
        self.assertGreater(funk[arranger.BEAT_LOUDNESS][0], 0)
        self.assertNotIn(arranger.BEAT_LOUDNESS, disco)
        kick = next(pattern for name, pattern in patterns(chosen(genre=SOUL_FUNK, subgenre=FUNK)).items() if name.startswith(A_KICK))
        size = Fraction(kick[notation.STEP_SIZE])
        on_one = [velocity for place, velocity in enumerate(kick[notation.VELOCITY]) if velocity is not None and (place * size) % 1 == 0]
        elsewhere = [velocity for place, velocity in enumerate(kick[notation.VELOCITY]) if velocity is not None and (place * size) % 1 != 0]
        self.assertGreater(min(on_one), max(elsewhere))


class TestWizardLoudness(unittest.TestCase):
    """The wizard's choices of a player's dynamics and levels."""

    __slots__ = ()

    def test_a_player_has_the_genres_levels_until_the_song_gives_its_own_and_takes_them_back(self):
        choices = chosen()
        usual = choices.player(THE_BASS).loudness_levels()
        self.assertEqual(list(usual), list(loudness.LEVELS))
        self.assertFalse(choices.player(THE_BASS).loudness_level_is_own(level=loudness.NORMAL))
        choices.player(THE_BASS).set_loudness_level(level=loudness.NORMAL, number=QUIET)
        self.assertTrue(choices.player(THE_BASS).loudness_level_is_own(level=loudness.NORMAL))
        self.assertEqual(choices.player(THE_BASS).loudness_levels()[loudness.NORMAL], QUIET)
        self.assertEqual(choices.player(THE_BASS).loudness_levels()[notation.ACCENT] - QUIET, usual[notation.ACCENT] - usual[loudness.NORMAL])
        choices.player(THE_BASS).set_loudness_level(level=loudness.NORMAL, number=None)
        self.assertEqual(choices.player(THE_BASS).loudness_levels(), usual)
        self.assertEqual(choices.to_data(), chosen().to_data())
        # The genre's own number chosen is no level of the song's own.
        choices.player(THE_BASS).set_loudness_level(level=loudness.NORMAL, number=usual[loudness.NORMAL])
        self.assertFalse(choices.player(THE_BASS).loudness_level_is_own(level=loudness.NORMAL))

    def test_a_quieter_player_is_quieter_in_the_song_and_the_others_are_as_they_were(self):
        plain = patterns(chosen())
        choices = chosen()
        choices.player(THE_BASS).set_loudness_level(level=loudness.NORMAL, number=QUIET)
        made = patterns(choices)
        changed = [name for name in plain if plain[name] != made[name]]
        self.assertTrue(changed)
        for name in changed:
            self.assertIn(THE_BASS, name)
            self.assertLess(max(sounded(made[name])), max(sounded(plain[name])))

    def test_the_drummers_levels_are_the_whole_kits(self):
        plain = patterns(chosen())
        choices = chosen()
        choices.player(THE_DRUMS).set_loudness_level(level=loudness.NORMAL, number=QUIET)
        made = patterns(choices)
        for piece in (A_KICK, A_SNARE):
            name = next(name for name in plain if name.startswith(piece))
            self.assertLess(max(sounded(made[name])), max(sounded(plain[name])))

    def test_only_the_levels_a_player_plays_are_offered(self):
        choices = chosen()
        # The bass under the kind's riff plays its accents and its short quiet roots; with no riff the bass plays one level.
        self.assertLessEqual({notation.GHOST, loudness.NORMAL, notation.ACCENT}, set(choices.player(THE_BASS).loudness_levels_offered()))
        for riff in choices.get_riffs().riff_names():
            choices.get_riffs().delete_riff(riff)
        self.assertEqual(choices.player(THE_BASS).loudness_levels_offered(), [loudness.NORMAL])
        self.assertIn(notation.ACCENT, choices.player(THE_LEAD).loudness_levels_offered())
        self.assertNotIn(notation.GHOST, choices.player(THE_DRUMS).loudness_levels_offered())
        self.assertIn(notation.GHOST, chosen(genre=SOUL_FUNK, subgenre=FUNK).player(THE_DRUMS).loudness_levels_offered())
        self.assertEqual(choices.player(NOT_A_PLAYER).loudness_levels_offered(), [])

    def test_the_snares_ghost_notes_are_far_quieter_than_its_backbeat_and_go_with_the_quiet_notes(self):
        choices = chosen(genre=SOUL_FUNK, subgenre=FUNK)
        snare = next(pattern for name, pattern in patterns(choices).items() if name.startswith(A_SNARE) and A_SNARE_BAR in name)
        self.assertLess(min(sounded(snare)), max(sounded(snare)) // 2)
        choices.get_kit().set_quiet_notes(False)
        without = next(pattern for name, pattern in patterns(choices).items() if name.startswith(A_SNARE) and A_SNARE_BAR in name)
        self.assertGreater(min(sounded(without)), max(sounded(without)) // 2)

    def test_dynamics_at_the_least_make_a_players_notes_alike_and_at_the_most_spread_them(self):
        spans = {}
        for dynamics in (loudness.LEAST_DYNAMICS, loudness.USUAL_DYNAMICS, loudness.MOST_DYNAMICS):
            choices = chosen()
            choices.player(THE_LEAD).set_dynamics(dynamics=dynamics)
            self.assertEqual(choices.player(THE_LEAD).get_dynamics(), dynamics)
            lead = [velocity for name, pattern in patterns(choices).items() if THE_LEAD in name for velocity in sounded(pattern)]
            spans[dynamics] = max(lead) - min(lead)
        self.assertEqual(spans[loudness.LEAST_DYNAMICS], 0)
        self.assertLess(spans[loudness.USUAL_DYNAMICS], spans[loudness.MOST_DYNAMICS])
        self.assertTrue(chosen().player(THE_LEAD).has_dynamics())
        self.assertFalse(chosen().player(NOT_A_PLAYER).has_dynamics())

    def test_the_usual_dynamics_are_no_choice_of_the_songs_own(self):
        choices = chosen()
        choices.player(THE_DRUMS).set_dynamics(dynamics=loudness.MOST_DYNAMICS)
        self.assertNotEqual(choices.to_data(), chosen().to_data())
        choices.player(THE_DRUMS).set_dynamics(dynamics=loudness.USUAL_DYNAMICS)
        self.assertEqual(choices.to_data(), chosen().to_data())

    def test_the_choices_are_kept_with_the_song_and_make_the_same_song_again(self):
        choices = chosen()
        choices.player(THE_DRUMS).set_dynamics(dynamics=loudness.MOST_DYNAMICS)
        choices.player(THE_LEAD).set_loudness_level(level=notation.ACCENT, number=LOUDER)
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual(again.player(THE_DRUMS).get_dynamics(), loudness.MOST_DYNAMICS)
        self.assertEqual(again.player(THE_LEAD).loudness_levels()[notation.ACCENT], LOUDER)
        self.assertEqual(patterns(again), patterns(choices))
        self.assertNotEqual(patterns(again), patterns(chosen()))

    def test_another_genre_forgets_a_players_loudness(self):
        choices = chosen()
        choices.player(THE_DRUMS).set_dynamics(dynamics=loudness.MOST_DYNAMICS)
        choices.player(THE_BASS).set_loudness_level(level=loudness.NORMAL, number=QUIET)
        choices.set_genre(SOUL_FUNK)
        choices.set_subgenre(FUNK)
        self.assertEqual(choices.player(THE_DRUMS).get_dynamics(), loudness.USUAL_DYNAMICS)
        self.assertFalse(choices.player(THE_BASS).loudness_level_is_own(level=loudness.NORMAL))

    def test_what_is_no_level_no_velocity_or_no_player_is_refused(self):
        choices = chosen()
        refused = fixed_text(errors.ERR_WIZARD_LOUDNESS)
        for role, level, number in ((NOT_A_PLAYER, loudness.NORMAL, QUIET), (THE_BASS, NOT_A_LEVEL, QUIET), (THE_BASS, loudness.NORMAL, TOO_LOUD), (THE_BASS, loudness.NORMAL, notation.LOWEST_VELOCITY - 1), (THE_BASS, loudness.NORMAL, True)):
            with self.assertRaisesRegex(ValueError, refused):
                choices.player(role).set_loudness_level(level=level, number=number)
        for role, dynamics in ((NOT_A_PLAYER, loudness.USUAL_DYNAMICS), (THE_BASS, TOO_WIDE), (THE_BASS, loudness.LEAST_DYNAMICS - 1), (THE_BASS, True)):
            with self.assertRaisesRegex(ValueError, fixed_text(errors.ERR_WIZARD_DYNAMICS)):
                choices.player(role).set_dynamics(dynamics=dynamics)
        self.assertEqual(choices.to_data(), chosen().to_data())


if __name__ == '__main__':
    unittest.main()
