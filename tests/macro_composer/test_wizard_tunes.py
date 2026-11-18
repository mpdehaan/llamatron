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

"""The song wizard's tunes: one for each kind of section, the wizard's until a person writes its pattern by hand, and the person's own from then on."""

import unittest

from llamatron.composition import naming
from llamatron.composition.file_format import PatternSetting, Row
from llamatron.macro_composer.arranger import NOBODY
from llamatron.macro_composer.riffs import FIRST_TAKE as FIRST_RIFF_TAKE
from llamatron.macro_composer.wizard_choices import FIRST_TUNE_TAKE, KEPT_OWN_RIFFS, LOST_RIFFS, WizardChoices
from llamatron.strings import errors, macro_composer as composer_text, names
from tests.support.ui_testing import fixed_text

A_GENRE = 'rock'
A_SUBGENRE = 'folk rock'
ANOTHER_GENRE = 'blues'
A_KIND = 'verse'
ANOTHER_KIND = 'chorus'
A_KIND_WITH_NO_TUNE = 'intro'
NOT_A_KIND = 'middle bit'
A_SEED = 7
ANOTHER_SEED = 8
A_DEGREE = 7
NOT_A_STEP_COUNT = 'many'


def chosen():
    choices = WizardChoices()
    choices.set_genre(A_GENRE)
    choices.set_subgenre(A_SUBGENRE)
    choices.set_seed(A_SEED)
    return choices


def rewritten(pattern):
    """Return a tune's pattern with every note on one degree, which no tune the wizard writes is."""
    return {**pattern, Row.DEGREE: [None if degree is None else A_DEGREE for degree in pattern[Row.DEGREE]]}


def tunes_played(*, choices, kind):
    """Return the name of the pattern the tune's player plays in each section of a kind, in the set the choices make."""
    setlist, name = choices.made_for_listening()
    player = choices.tune_player()
    scenes = setlist.get_song(name).get_scenes()
    return [scene.get_clip_slot(player).get_pattern_name() for place, scene in enumerate(scenes) if choices.section_kind(place) == kind and scene.has_clip_slot(player)]


class TestWizardTunes(unittest.TestCase):

    def test_a_kind_of_section_the_tunes_player_plays_in_has_a_tune_and_each_is_listed_once_in_the_forms_order(self):
        choices = chosen()
        kinds = choices.tune_kinds()
        self.assertIn(A_KIND, kinds)
        self.assertNotIn(A_KIND_WITH_NO_TUNE, kinds)
        self.assertEqual(len(kinds), len(set(kinds)))
        in_form = choices.section_kinds_in_form()
        self.assertEqual(kinds, sorted(kinds, key=in_form.index))

    def test_until_edited_a_tune_is_the_one_the_choices_write_and_follows_them(self):
        choices = chosen()
        self.assertFalse(choices.tune_is_own(A_KIND))
        first = choices.tune_pattern(A_KIND)
        self.assertIn(choices.tune_pattern_name(A_KIND), tunes_played(choices=choices, kind=A_KIND))
        choices.set_seed(ANOTHER_SEED)
        self.assertNotEqual(choices.tune_pattern(A_KIND), first)

    def test_a_tune_written_by_hand_is_played_by_every_section_of_its_kind_and_by_no_other(self):
        choices = chosen()
        other = next(kind for kind in choices.tune_kinds() if kind != A_KIND)
        before = tunes_played(choices=choices, kind=other)
        own = rewritten(choices.tune_pattern(A_KIND))
        choices.set_tune_pattern(kind=A_KIND, pattern=own)
        self.assertTrue(choices.tune_is_own(A_KIND))
        self.assertEqual(choices.tune_pattern(A_KIND), own)
        played = tunes_played(choices=choices, kind=A_KIND)
        self.assertGreater(len(played), 1)
        self.assertEqual(set(played), {choices.tune_pattern_name(A_KIND)})
        setlist, _ = choices.made_for_listening()
        self.assertEqual(setlist.get_pattern(played[0]).to_data()[Row.DEGREE], own[Row.DEGREE])
        self.assertEqual(tunes_played(choices=choices, kind=other), before)

    def test_what_is_handed_over_and_what_is_handed_back_are_copies(self):
        choices = chosen()
        own = rewritten(choices.tune_pattern(A_KIND))
        choices.set_tune_pattern(kind=A_KIND, pattern=own)
        note = own[Row.DEGREE].index(A_DEGREE)
        own[Row.DEGREE][note] = None
        choices.tune_pattern(A_KIND)[Row.DEGREE][note] = None
        self.assertEqual(choices.tune_pattern(A_KIND)[Row.DEGREE][note], A_DEGREE)

    def test_no_other_choice_writes_over_a_tune_written_by_hand(self):
        choices = chosen()
        own = rewritten(choices.tune_pattern(A_KIND))
        choices.set_tune_pattern(kind=A_KIND, pattern=own)
        choices.set_seed(ANOTHER_SEED)
        self.assertEqual(choices.tune_pattern(A_KIND), own)
        choices.set_genre(ANOTHER_GENRE)
        choices.set_genre(A_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        self.assertEqual(choices.tune_pattern(A_KIND), own)

    def test_none_gives_the_tune_back_to_the_choices(self):
        choices = chosen()
        first = choices.tune_pattern(A_KIND)
        choices.set_tune_pattern(kind=A_KIND, pattern=rewritten(first))
        choices.set_tune_pattern(kind=A_KIND, pattern=None)
        self.assertFalse(choices.tune_is_own(A_KIND))
        self.assertEqual(choices.tune_pattern(A_KIND), first)
        self.assertEqual(choices.to_data(), chosen().to_data())

    def test_a_tune_written_by_hand_is_kept_with_the_choices_and_read_back(self):
        choices = chosen()
        own = rewritten(choices.tune_pattern(A_KIND))
        choices.set_tune_pattern(kind=A_KIND, pattern=own)
        read = WizardChoices.from_data(choices.to_data())
        self.assertTrue(read.tune_is_own(A_KIND))
        self.assertEqual(read.tune_pattern(A_KIND), own)

    def test_a_kind_with_no_tune_and_a_pattern_no_song_can_be_made_with_are_refused_and_nothing_changes(self):
        choices = chosen()
        before = choices.to_data()
        for kind in (A_KIND_WITH_NO_TUNE, NOT_A_KIND):
            with self.assertRaises(ValueError) as refused:
                choices.set_tune_pattern(kind=kind, pattern=choices.tune_pattern(A_KIND))
            self.assertIn(fixed_text(errors.ERR_WIZARD_NO_TUNE_IN), str(refused.exception))
        with self.assertRaises(ValueError) as refused:
            choices.set_tune_pattern(kind=A_KIND, pattern={**choices.tune_pattern(A_KIND), PatternSetting.STEPS: NOT_A_STEP_COUNT})
        self.assertIn(fixed_text(errors.ERR_WIZARD_TUNE_PATTERN), str(refused.exception))
        self.assertEqual(choices.to_data(), before)
        own = rewritten(choices.tune_pattern(A_KIND))
        choices.set_tune_pattern(kind=A_KIND, pattern=own)
        with self.assertRaises(ValueError):
            choices.set_tune_pattern(kind=A_KIND, pattern={**own, PatternSetting.STEPS: NOT_A_STEP_COUNT})
        self.assertEqual(choices.tune_pattern(A_KIND), own)


class TestWizardTuneTakes(unittest.TestCase):

    def test_a_new_take_writes_another_tune_for_its_kind_and_leaves_every_other_pattern_of_the_song(self):
        choices = chosen()
        before, name = choices.made_for_listening()
        first = choices.tune_pattern(A_KIND)
        usual_name = choices.tune_pattern_name(A_KIND)
        choices.new_tune_take(A_KIND)
        self.assertEqual(choices.tune_take(A_KIND), FIRST_TUNE_TAKE + 1)
        taken = choices.tune_pattern(A_KIND)
        self.assertNotEqual(taken[Row.DEGREE], first[Row.DEGREE])
        self.assertEqual(len(taken[Row.DEGREE]), len(first[Row.DEGREE]))
        after, _ = choices.made_for_listening()
        took = choices.tune_pattern_name(A_KIND)
        for pattern in before.get_pattern_names():
            if pattern != usual_name:
                self.assertEqual(after.get_pattern(pattern).to_data(), before.get_pattern(pattern).to_data(), pattern)
        self.assertEqual(set(after.get_pattern_names()) - set(before.get_pattern_names()), {took})
        self.assertEqual(set(tunes_played(choices=choices, kind=A_KIND)), {took})

    def test_each_take_is_another_tune_the_same_take_is_the_same_tune_and_takes_are_kept_with_the_choices(self):
        choices = chosen()
        choices.new_tune_take(A_KIND)
        second = choices.tune_pattern(A_KIND)
        self.assertEqual(WizardChoices.from_data(choices.to_data()).tune_pattern(A_KIND), second)
        choices.new_tune_take(A_KIND)
        self.assertNotEqual(choices.tune_pattern(A_KIND)[Row.DEGREE], second[Row.DEGREE])
        read = WizardChoices.from_data(choices.to_data())
        self.assertEqual(read.tune_take(A_KIND), FIRST_TUNE_TAKE + 2)
        self.assertEqual(read.tune_pattern(A_KIND), choices.tune_pattern(A_KIND))

    def test_a_new_take_gives_up_notes_written_by_hand_and_notes_written_by_hand_win_over_a_take(self):
        choices = chosen()
        own = rewritten(choices.tune_pattern(A_KIND))
        choices.set_tune_pattern(kind=A_KIND, pattern=own)
        choices.new_tune_take(A_KIND)
        self.assertFalse(choices.tune_is_own(A_KIND))
        self.assertNotEqual(choices.tune_pattern(A_KIND), own)
        choices.set_tune_pattern(kind=A_KIND, pattern=own)
        self.assertEqual(choices.tune_pattern(A_KIND), own)
        self.assertEqual(choices.tune_take(A_KIND), FIRST_TUNE_TAKE + 1)

    def test_a_kind_with_no_tune_has_no_take_and_another_genre_starts_from_the_first_take(self):
        choices = chosen()
        with self.assertRaises(ValueError):
            choices.new_tune_take(A_KIND_WITH_NO_TUNE)
        choices.new_tune_take(A_KIND)
        choices.set_genre(ANOTHER_GENRE)
        choices.set_genre(A_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        self.assertEqual(choices.tune_take(A_KIND), FIRST_TUNE_TAKE)


class TestWhoPlaysTheTune(unittest.TestCase):

    def test_the_genres_player_has_the_tune_until_another_is_chosen_and_the_bass_and_the_drums_are_not_offered(self):
        choices = chosen()
        self.assertEqual(choices.tune_played_by(), choices.tune_player())
        offered = choices.tune_players_offered()
        self.assertIn(choices.tune_player(), offered)
        self.assertTrue(set(offered) < set(choices.roles_in()))
        for kind in choices.tune_kinds():
            self.assertIsNone(choices.tune_played_by_in(kind))
            self.assertEqual(choices.tune_player_in(kind), choices.tune_player())

    def test_the_songs_player_plays_every_tune_in_place_of_the_usual_part_and_the_genres_player_rests(self):
        choices = chosen()
        usual = choices.tune_player()
        other = next(role for role in choices.tune_players_offered() if role != usual)
        tune = choices.tune_pattern(A_KIND)
        choices.set_tune_played_by(other)
        setlist, name = choices.made_for_listening()
        for place, scene in enumerate(setlist.get_song(name).get_scenes()):
            if choices.section_kind(place) == A_KIND:
                self.assertFalse(scene.has_clip_slot(usual))
                self.assertEqual(setlist.get_pattern(scene.get_clip_slot(other).get_pattern_name()).to_data()[Row.DEGREE], tune[Row.DEGREE])
        self.assertEqual(choices.tune_pattern(A_KIND)[Row.DEGREE], tune[Row.DEGREE])
        choices.set_tune_played_by(None)
        self.assertEqual(choices.to_data(), chosen().to_data())

    def test_a_kind_of_section_takes_a_player_of_its_own_or_nobody_and_the_other_kinds_go_by_the_song(self):
        choices = chosen()
        usual = choices.tune_player()
        other = next(role for role in choices.tune_players_offered() if role != usual)
        another_kind = next(kind for kind in choices.tune_kinds() if kind != A_KIND)
        choices.set_tune_played_by_in(kind=A_KIND, role=other)
        self.assertEqual(choices.tune_player_in(A_KIND), other)
        self.assertEqual(choices.tune_player_in(another_kind), usual)
        # A last chorus may be written anew, so the kind's tune is one of the tunes its sections play.
        self.assertIn(choices.tune_pattern_name(another_kind), tunes_played(choices=choices, kind=another_kind))
        choices.set_tune_played_by_in(kind=A_KIND, role=NOBODY)
        self.assertIsNone(choices.tune_player_in(A_KIND))
        self.assertIsNone(choices.tune_pattern(A_KIND))
        setlist, name = choices.made_for_listening()
        for place, scene in enumerate(setlist.get_song(name).get_scenes()):
            if choices.section_kind(place) == A_KIND:
                self.assertFalse(scene.has_clip_slot(usual))
        self.assertIn(A_KIND, choices.tune_kinds())
        choices.set_tune_played_by_in(kind=A_KIND, role=None)
        self.assertEqual(choices.to_data(), chosen().to_data())

    def test_what_is_chosen_is_kept_refused_when_no_such_player_and_given_up_with_the_genre_or_the_player(self):
        choices = chosen()
        usual = choices.tune_player()
        other = next(role for role in choices.tune_players_offered() if role != usual)
        for refused in (NOT_A_KIND, next(role for role in choices.roles_in() if role not in choices.tune_players_offered())):
            with self.assertRaises(ValueError):
                choices.set_tune_played_by(refused)
            with self.assertRaises(ValueError):
                choices.set_tune_played_by_in(kind=A_KIND, role=refused)
        with self.assertRaises(ValueError):
            choices.set_tune_played_by_in(kind=A_KIND_WITH_NO_TUNE, role=other)
        choices.set_tune_played_by(other)
        choices.set_tune_played_by_in(kind=A_KIND, role=NOBODY)
        read = WizardChoices.from_data(choices.to_data())
        self.assertEqual(read.tune_played_by(), other)
        self.assertEqual(read.tune_played_by_in(A_KIND), NOBODY)
        choices.set_role_in(role=other, on=False)
        self.assertEqual(choices.tune_played_by(), usual)
        choices.set_genre(ANOTHER_GENRE)
        choices.set_genre(A_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        self.assertIsNone(choices.tune_played_by_in(A_KIND))


class TestRiffsAdded(unittest.TestCase):

    def players_of(self, *, choices, kind):
        """Return the pattern each player plays in the first section of a kind, by player, in the set the choices make."""
        setlist, name = choices.made_for_listening()
        scene = setlist.get_song(name).get_scenes()[choices.riff_place(kind)]
        return {role: scene.get_clip_slot(role).get_pattern_name() for role in choices.roles_in() if scene.has_clip_slot(role)}

    def test_a_riff_is_offered_in_every_kind_of_the_form_to_players_of_figures_but_the_tunes_player(self):
        choices = chosen()
        played = [kind for place, kind in enumerate(choices.section_kinds_in_form()) if not choices.section_is_held(place)]
        self.assertEqual(choices.riff_kinds_offered(), list(dict.fromkeys(played)))
        for kind in choices.riff_kinds_offered():
            free = choices.riff_players_free(kind)
            self.assertTrue(set(free) <= set(choices.section_plays(choices.riff_place(kind))))
            self.assertNotIn(choices.tune_player_in(kind), free)
        self.assertTrue(choices.riff_players_free(A_KIND))
        self.assertEqual(choices.riff_players_free(NOT_A_KIND), [])
        self.assertEqual(choices.added_riffs(), [])

    def test_a_riffs_players_play_it_in_its_kind_in_place_of_their_parts_and_nowhere_else(self):
        choices = chosen()
        one, other = choices.riff_players_free(A_KIND)[:2]
        usual = self.players_of(choices=choices, kind=A_KIND)
        elsewhere = self.players_of(choices=choices, kind=ANOTHER_KIND)
        riff = choices.add_riff(kind=A_KIND, players=[one, other])
        self.assertEqual(riff, naming.new_name(word=names.MSG_NEW_RIFF_WORD, taken=[]))
        self.assertEqual(choices.riffs_in(A_KIND), [riff])
        self.assertEqual(choices.riff_players_of(riff), [one, other])
        played = self.players_of(choices=choices, kind=A_KIND)
        for role in (one, other):
            self.assertEqual(played[role], composer_text.MSG_PART_OF_SECTION.format(role, riff))
        self.assertEqual({role: part for role, part in played.items() if role not in (one, other)}, {role: part for role, part in usual.items() if role not in (one, other)})
        self.assertEqual(self.players_of(choices=choices, kind=ANOTHER_KIND), elsewhere)

    def test_a_player_has_one_riff_in_a_kind_and_may_have_another_in_another_kind(self):
        choices = chosen()
        player = choices.riff_players_free(A_KIND)[0]
        first = choices.add_riff(kind=A_KIND, players=[player])
        self.assertNotIn(player, choices.riff_players_free(A_KIND))
        for refused in ([player], [], [NOT_A_KIND], [choices.tune_player_in(A_KIND)]):
            with self.assertRaises(ValueError):
                choices.add_riff(kind=A_KIND, players=refused)
        second = choices.add_riff(kind=ANOTHER_KIND, players=[player])
        self.assertNotEqual(first, second)
        played = {kind: self.players_of(choices=choices, kind=kind)[player] for kind in (A_KIND, ANOTHER_KIND)}
        self.assertEqual(played, {A_KIND: composer_text.MSG_PART_OF_SECTION.format(player, first), ANOTHER_KIND: composer_text.MSG_PART_OF_SECTION.format(player, second)})
        setlist, _ = choices.made_for_listening()
        self.assertNotEqual(setlist.get_pattern(played[A_KIND]).to_data()[Row.DEGREE], setlist.get_pattern(played[ANOTHER_KIND]).to_data()[Row.DEGREE])
        self.assertEqual(choices.added_riffs(), [first, second])

    def test_a_riff_of_the_song_is_played_again_in_another_kind_by_its_own_players_while_they_are_free_there(self):
        choices = chosen()
        player = choices.riff_players_free(A_KIND)[0]
        riff = choices.add_riff(kind=A_KIND, players=[player])
        self.assertEqual(choices.add_riff(kind=ANOTHER_KIND, riff=riff), riff)
        self.assertEqual(choices.riff_kinds_of(riff), [A_KIND, ANOTHER_KIND])
        self.assertEqual(self.players_of(choices=choices, kind=A_KIND)[player], self.players_of(choices=choices, kind=ANOTHER_KIND)[player])
        for refused in (riff, NOT_A_KIND):
            with self.assertRaises(ValueError):
                choices.add_riff(kind=ANOTHER_KIND, riff=refused)

    def test_a_riff_taken_out_of_its_last_kind_is_gone_and_the_song_is_as_it_was(self):
        choices = chosen()
        usual = chosen().to_data()
        riff = choices.add_riff(kind=A_KIND, players=[choices.riff_players_free(A_KIND)[0]])
        choices.add_riff(kind=ANOTHER_KIND, riff=riff)
        choices.remove_riff(kind=A_KIND, riff=riff)
        self.assertEqual(choices.riff_kinds_of(riff), [ANOTHER_KIND])
        with self.assertRaises(ValueError):
            choices.remove_riff(kind=A_KIND, riff=riff)
        choices.remove_riff(kind=ANOTHER_KIND, riff=riff)
        self.assertEqual(choices.added_riffs(), [])
        self.assertEqual(choices.to_data(), usual)

    def test_a_new_take_writes_other_notes_for_the_riff_alone_and_riffs_are_kept_with_the_choices_until_another_genre(self):
        choices = chosen()
        player = choices.riff_players_free(A_KIND)[0]
        riff = choices.add_riff(kind=A_KIND, players=[player])
        part = composer_text.MSG_PART_OF_SECTION.format(player, riff)
        first = choices.made_for_listening()[0].get_pattern(part).to_data()
        choices.new_riff_take_of(riff)
        self.assertEqual(choices.riff_take_of(riff), FIRST_RIFF_TAKE + 1)
        taken = choices.made_for_listening()[0].get_pattern(part).to_data()
        self.assertNotEqual(taken[Row.DEGREE], first[Row.DEGREE])
        read = WizardChoices.from_data(choices.to_data())
        self.assertEqual(read.riffs_in(A_KIND), [riff])
        self.assertEqual(read.made_for_listening()[0].get_pattern(part).to_data(), taken)
        choices.set_genre(ANOTHER_GENRE)
        choices.set_genre(A_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        self.assertEqual(choices.added_riffs(), [])

    def test_a_riff_written_by_hand_is_played_as_written_by_each_player_in_the_players_own_octave_until_a_new_take(self):
        choices = chosen()
        one, other = choices.riff_players_free(A_KIND)[:2]
        riff = choices.add_riff(kind=A_KIND, players=[one, other])
        self.assertEqual(choices.riff_pattern_name(riff), composer_text.MSG_PART_OF_SECTION.format(one, riff))
        self.assertFalse(choices.added_riff_is_own(riff))
        setlist, _ = choices.made_for_listening()
        apart = [high - low for high, low in zip(setlist.get_pattern(choices.riff_pattern_name(riff)).to_data()[Row.OCTAVE],
                                                 setlist.get_pattern(composer_text.MSG_PART_OF_SECTION.format(other, riff)).to_data()[Row.OCTAVE]) if high is not None]
        own = rewritten(choices.riff_pattern(riff))
        choices.set_riff_pattern(riff=riff, pattern=own)
        self.assertTrue(choices.added_riff_is_own(riff))
        self.assertEqual(choices.riff_pattern(riff), own)
        setlist, _ = choices.made_for_listening()
        second = setlist.get_pattern(composer_text.MSG_PART_OF_SECTION.format(other, riff)).to_data()
        self.assertEqual(second[Row.DEGREE], own[Row.DEGREE])
        self.assertEqual([high - low for high, low in zip(own[Row.OCTAVE], second[Row.OCTAVE]) if high is not None], apart)
        self.assertEqual(WizardChoices.from_data(choices.to_data()).riff_pattern(riff), own)
        choices.new_riff_take_of(riff)
        self.assertFalse(choices.added_riff_is_own(riff))
        self.assertNotEqual(choices.riff_pattern(riff)[Row.DEGREE], own[Row.DEGREE])

    def test_a_blank_riff_has_no_note_and_a_pattern_the_song_cannot_be_made_with_is_refused(self):
        choices = chosen()
        riff = choices.add_riff(kind=A_KIND, players=choices.riff_players_free(A_KIND)[:1])
        written = choices.riff_pattern(riff)
        blank = choices.blank_riff_pattern(riff)
        self.assertEqual(blank[PatternSetting.STEPS], written[PatternSetting.STEPS])
        self.assertNotIn(Row.DEGREE, blank)
        choices.set_riff_pattern(riff=riff, pattern=blank)
        self.assertEqual(choices.riff_pattern(riff), blank)
        with self.assertRaises(ValueError):
            choices.set_riff_pattern(riff=riff, pattern={PatternSetting.STEPS: NOT_A_STEP_COUNT})
        self.assertEqual(choices.riff_pattern(riff), blank)

    def test_a_riff_written_by_hand_is_kept_through_another_genre_and_waits_while_its_player_is_out_of_the_band(self):
        choices = chosen()
        player = choices.riff_players_free(A_KIND)[0]
        riff = choices.add_riff(kind=A_KIND, players=[player])
        made_by_wizard = choices.add_riff(kind=ANOTHER_KIND, players=[player])
        own = rewritten(choices.riff_pattern(riff))
        choices.set_riff_pattern(riff=riff, pattern=own)
        self.assertEqual(choices.lost_with_genre(), ({LOST_RIFFS: 1}, {KEPT_OWN_RIFFS: 1}))
        choices.set_role_in(role=player, on=False)
        self.assertEqual(choices.added_riffs(), [])
        choices.set_role_in(role=player, on=True)
        self.assertEqual(choices.added_riffs(), [riff, made_by_wizard])
        choices.set_genre(ANOTHER_GENRE)
        choices.set_genre(A_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        self.assertEqual(choices.added_riffs(), [riff])
        self.assertEqual(choices.riff_pattern(riff), own)
