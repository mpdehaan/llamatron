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

"""Interplay: what the player beside the tune plays, section by section, and the wizard's choice of who answers and how."""

import unittest

from llamatron.macro_composer import arranger, interplay
from llamatron.macro_composer.melody import GRID
from llamatron.macro_composer.notation import LINES, REST, STEPS
from llamatron.macro_composer.wizard_choices import BESIDE_KEPT, BY, WizardChoices
from llamatron.strings.errors import ERR_NO_SUCH_WAY_BESIDE, ERR_WIZARD_FILLS_BUSY, ERR_WIZARD_NO_SUCH_ANSWERER, ERR_WIZARD_NO_SUCH_WAY_BESIDE, ERR_WIZARD_SECTION_HAS_NO_ROLE
from llamatron.strings.macro_composer import MSG_PART_BESIDE
from llamatron.support.version import VERSION

ROCK = 'rock'
BLUES = 'blues'
ELECTRONIC = 'electronic'
ARENA_ROCK = 'arena rock'
HARD_ROCK = 'hard rock'
PUNK = 'punk'
SONG_NAME = 'anthem'
NO_SUCH = 'no such'
VERSE = 'verse'
CHORUS = 'chorus'
BRIDGE = 'bridge'
SOLO = 'solo'
A_SEED = 7
A_GRID = 8
# A line of two bars the tune sings: its last note three steps long, and a rest of one step after.
LAST_NOTE = 3
A_LINE = [{REST: 1}, {'degree': 3, STEPS: 2}, {'degree': 2, STEPS: 9}, {'degree': 1, STEPS: LAST_NOTE}, {REST: 1}]
SILENT = [{REST: A_GRID * 2}]


def steps_in(line):
    return sum(note.get(REST, note.get(STEPS, 0)) for note in line)


def sounds_in(line):
    return [note for note in line if REST not in note]


def starts_of(line):
    """The step each sound of a line starts on."""
    at = 0
    starts = []
    for note in line:
        if REST not in note:
            starts.append(at)
        at += note.get(REST, note.get(STEPS, 0))
    return starts


def wizard(*, genre=ROCK, subgenre=ARENA_ROCK):
    choices = WizardChoices()
    choices.set_genre(genre)
    choices.set_subgenre(subgenre)
    choices.draw_seed()
    return choices


def made(choices):
    return arranger.arranged(style=arranger.style_named(choices.get_genre()), song=choices.song_picks(SONG_NAME))


def place_of(*, choices, kind, which=0):
    """The place in the form of a section of a kind: the first, or a later one."""
    return [place for place, label in enumerate(choices.section_labels()) if label.split('-')[0] == kind][which]


class TestRoomInALine(unittest.TestCase):
    """The room a tune's line leaves at its end."""

    def test_the_room_is_the_rests_at_the_end_and_the_last_note_but_for_the_step_it_lands_on(self):
        self.assertEqual(interplay.room_in(A_LINE), 1 + LAST_NOTE - 1)
        self.assertEqual(interplay.room_in(SILENT), A_GRID * 2)
        self.assertEqual(interplay.room_in([{'degree': 1, STEPS: 1}]), 0)

    def test_a_fills_notes_are_more_and_shorter_the_busier_and_fill_the_room(self):
        counts = []
        for busy in range(interplay.LEAST_BUSY, interplay.MOST_BUSY + 1):
            lengths = interplay.lengths_of(steps=A_GRID, unit=1, busy=busy)
            self.assertEqual(sum(lengths), A_GRID)
            counts.append(len(lengths))
        self.assertEqual(counts, sorted(counts))
        self.assertEqual((counts[0], counts[-1]), (1, A_GRID))


class TestUnderLead(unittest.TestCase):
    """The lines a player plays beside a tune's lines."""

    def setUp(self):
        style = arranger.style_named(ROCK)
        self.habits = style[arranger.MELODY]['4/4']
        self.chords = [{'degree': 1}, {'degree': 4}, {'degree': 5}, {'degree': 1}]
        self.tune = [[dict(note) for note in A_LINE] for _ in range(4)]

    def under(self, *, busy):
        return interplay.UnderLead(busy=busy, habits=self.habits, grid=self.habits[GRID], scale_type='major', seed=A_SEED)

    def lines(self, way, *, busy=interplay.USUAL_BUSY, tune=None):
        return self.under(busy=busy).lines(way=way, tune=tune or self.tune, chords=self.chords, section=VERSE)

    def test_every_way_gives_lines_as_long_as_the_tunes(self):
        for way in (interplay.FILLS, interplay.ANSWERS, interplay.DOUBLES, interplay.RIFF):
            lines = self.lines(way)
            self.assertEqual([steps_in(line) for line in lines], [steps_in(line) for line in self.tune], way)

    def test_a_fill_starts_once_the_tunes_last_note_has_landed_and_comes_at_the_end_of_every_second_line(self):
        lines = self.lines(interplay.FILLS)
        landed = steps_in(A_LINE) - interplay.room_in(A_LINE)
        self.assertEqual([bool(sounds_in(line)) for line in lines], [False, True, False, True])
        for line in lines:
            for start in starts_of(line):
                self.assertGreaterEqual(start, landed)

    def test_an_answer_comes_after_every_line_and_takes_all_the_room_of_a_line_the_tune_is_silent_through(self):
        lines = self.lines(interplay.ANSWERS)
        self.assertTrue(all(sounds_in(line) for line in lines))
        answered = self.lines(interplay.ANSWERS, tune=[A_LINE, SILENT], busy=interplay.MOST_BUSY)
        self.assertEqual(starts_of(answered[1])[0], 0)
        # A fill, in the same room, lasts no more than half a bar.
        filled = self.lines(interplay.FILLS, tune=[A_LINE, SILENT], busy=interplay.MOST_BUSY)
        self.assertEqual(starts_of(filled[1])[0], steps_in(SILENT) - self.habits[GRID] // interplay.FILL_SHARE_OF_BAR)

    def test_a_line_with_no_room_is_left_silent(self):
        full = [{'degree': 1, STEPS: 1}] * (A_GRID * 2)
        self.assertEqual(self.lines(interplay.ANSWERS, tune=[full]), [[{REST: A_GRID * 2}]])

    def test_playing_the_hook_with_the_tune_is_the_tunes_own_lines_sharing_no_note(self):
        lines = self.lines(interplay.DOUBLES)
        self.assertEqual(lines, self.tune)
        self.assertIsNot(lines[0][1], self.tune[0][1])

    def test_a_riff_is_one_bar_played_under_every_bar_starting_on_the_beat(self):
        lines = self.lines(interplay.RIFF)
        for line in lines:
            starts = starts_of(line)
            self.assertIn(0, starts)
            self.assertIn(self.habits[GRID], starts)
            bar = [start for start in starts if start < self.habits[GRID]]
            self.assertEqual([start - self.habits[GRID] for start in starts if start >= self.habits[GRID]], bar)

    def test_how_busy_changes_the_fills_and_the_riff(self):
        for way in (interplay.ANSWERS, interplay.RIFF):
            self.assertNotEqual(self.lines(way, busy=interplay.LEAST_BUSY), self.lines(way, busy=interplay.MOST_BUSY), way)


class TestArrangedBesideTheTune(unittest.TestCase):
    """A song whose answering player has something to do in each section."""

    def parts_of(self, *, choices, way):
        song = made(choices)
        return {scene[arranger.SCENE]: scene[arranger.PLAY].get(SOLO, {}).get(arranger.PART) for scene in song[arranger.FORM]}, song

    def test_each_section_plays_what_the_plan_says_and_the_solo_is_the_players_own(self):
        choices = wizard()
        parts, song = self.parts_of(choices=choices, way=None)
        self.assertEqual(parts[VERSE], MSG_PART_BESIDE.format(VERSE, SOLO, interplay.FILLS))
        self.assertEqual(parts[CHORUS], MSG_PART_BESIDE.format(CHORUS, SOLO, interplay.DOUBLES))
        self.assertEqual(parts[BRIDGE], MSG_PART_BESIDE.format(BRIDGE, SOLO, interplay.ANSWERS))
        self.assertNotIn(interplay.FILLS, parts[SOLO])
        # Playing the hook with the tune is the singer's own line, on the player's own track.
        self.assertEqual(song[arranger.PARTS][parts[CHORUS]][LINES], song[arranger.PARTS][arranger.MSG_PART_OF_SECTION.format(CHORUS, 'lead')][LINES])

    def test_a_player_who_waits_everywhere_makes_the_song_made_before_answering_could_be_chosen(self):
        choices = wizard()
        choices.set_role_plan(interplay.WAITS)
        waiting = made(choices)
        song = choices.song_picks(SONG_NAME)
        del song[arranger.BESIDE]
        self.assertEqual(waiting, arranger.arranged(style=arranger.style_named(ROCK), song=song))
        choices.set_answered_by(None)
        self.assertEqual(made(choices), waiting)

    def test_a_blues_chorus_answered_every_line_is_played_as_the_genre_writes_it_and_a_player_who_waits_is_silent_there(self):
        choices = wizard(genre=BLUES, subgenre='shuffle')
        answering = choices.answered_by()
        song = choices.song_picks(SONG_NAME)
        as_planned = made(choices)
        del song[arranger.BESIDE]
        self.assertEqual(as_planned, arranger.arranged(style=arranger.style_named(BLUES), song=song))
        choices.set_role_plan(interplay.WAITS)
        waiting = made(choices)
        chorus = next(scene for scene in waiting[arranger.FORM] if scene[arranger.SCENE] == CHORUS)
        self.assertNotIn(answering, chorus[arranger.PLAY])
        choices.set_role_plan(interplay.FILLS)
        chorus = next(scene for scene in made(choices)[arranger.FORM] if scene[arranger.SCENE] == CHORUS)
        self.assertEqual(chorus[arranger.PLAY][answering][arranger.PART], MSG_PART_BESIDE.format(CHORUS, answering, interplay.FILLS))

    def test_a_way_that_is_none_is_refused(self):
        choices = wizard()
        song = choices.song_picks(SONG_NAME)
        song[arranger.BESIDE][arranger.BESIDE_WAYS] = [NO_SUCH] * len(song[arranger.BESIDE][arranger.BESIDE_WAYS])
        with self.assertRaises(ValueError) as refused:
            arranger.arranged(style=arranger.style_named(ROCK), song=song)
        self.assertEqual(str(refused.exception), ERR_NO_SUCH_WAY_BESIDE.format(NO_SUCH))


class TestWizardInterplayChoices(unittest.TestCase):
    """Who answers the tune, the plan, a section's own role and how busy, as the wizard keeps them."""

    def test_a_new_song_is_answered_by_the_genres_player_going_by_the_subgenres_plan(self):
        choices = wizard()
        self.assertEqual(choices.tune_player(), 'lead')
        self.assertEqual((choices.answerers(), choices.answered_by()), ([SOLO], SOLO))
        self.assertIsNone(choices.get_role_plan())
        self.assertEqual(choices.section_role(place_of(choices=choices, kind=VERSE)), interplay.FILLS)
        self.assertEqual(choices.section_role(place_of(choices=choices, kind=CHORUS)), interplay.DOUBLES)
        hard = wizard(subgenre=HARD_ROCK)
        self.assertEqual(hard.section_role(place_of(choices=hard, kind=VERSE)), interplay.RIFF)
        # A kind the plan leaves out is waited through, and a section nobody has the tune in has no role.
        self.assertFalse(choices.section_has_role(place_of(choices=choices, kind=SOLO)))
        with self.assertRaises(ValueError) as refused:
            choices.section_role(place_of(choices=choices, kind=SOLO))
        self.assertEqual(str(refused.exception), ERR_WIZARD_SECTION_HAS_NO_ROLE.format(value=place_of(choices=choices, kind=SOLO)))

    def test_nobody_answers_where_the_genre_has_no_answering_player_or_the_subgenre_gives_the_player_no_way(self):
        for genre, subgenre in ((ELECTRONIC, 'house'), (ROCK, PUNK)):
            choices = wizard(genre=genre, subgenre=subgenre)
            self.assertEqual((choices.answerers(), choices.answered_by()), ([], None))
            self.assertFalse(choices.has_fills_busy())
            self.assertNotIn(arranger.BESIDE, choices.song_picks(SONG_NAME))
            with self.assertRaises(ValueError):
                choices.set_role_plan(interplay.FILLS)

    def test_one_role_for_every_section_a_sections_own_and_the_plan_again(self):
        choices = wizard()
        verse = place_of(choices=choices, kind=VERSE)
        chorus = place_of(choices=choices, kind=CHORUS)
        usual = made(choices)
        choices.set_section_role(place=verse, way=interplay.RIFF)
        self.assertTrue(choices.section_role_is_own(verse))
        self.assertEqual((choices.section_role(verse), choices.section_role(chorus)), (interplay.RIFF, interplay.DOUBLES))
        # Only that verse changed: the second verse still goes by the plan.
        self.assertEqual(choices.section_role(place_of(choices=choices, kind=VERSE, which=1)), interplay.FILLS)
        self.assertNotEqual(made(choices), usual)
        choices.set_section_role(place=verse, way=None)
        self.assertFalse(choices.section_role_is_own(verse))
        self.assertEqual(choices.section_role(verse), interplay.FILLS)
        choices.set_section_role(place=verse, way=interplay.RIFF)
        choices.set_role_plan(interplay.ANSWERS)
        self.assertEqual({choices.section_role(place) for place in (verse, chorus)}, {interplay.ANSWERS})
        self.assertFalse(choices.section_role_is_own(verse))
        choices.set_role_plan(None)
        self.assertEqual(choices.section_role(chorus), interplay.DOUBLES)

    def test_what_is_chosen_is_kept_with_the_song_and_a_song_kept_before_keeps_to_what_was_made_then(self):
        choices = wizard()
        verse = place_of(choices=choices, kind=VERSE)
        choices.set_section_role(place=verse, way=interplay.ANSWERS)
        choices.set_fills_busy(interplay.MOST_BUSY)
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual((again.section_role(verse), again.get_fills_busy(), again.answered_by()), (interplay.ANSWERS, interplay.MOST_BUSY, SOLO))
        self.assertEqual(made(again), made(choices))
        choices.set_answered_by(None)
        again = WizardChoices.from_data(choices.to_data())
        self.assertIsNone(again.answered_by())
        self.assertEqual(again.to_data()[BESIDE_KEPT][BY], None)
        before = {field: value for field, value in choices.to_data().items() if field != BESIDE_KEPT}
        old = WizardChoices.from_data(before)
        self.assertEqual((old.answerers(), old.answered_by()), ([], None))
        self.assertNotIn(arranger.BESIDE, old.song_picks(SONG_NAME))

    def test_what_is_no_player_no_way_and_no_place_of_the_gauge_is_refused(self):
        choices = wizard()
        verse = place_of(choices=choices, kind=VERSE)
        with self.assertRaises(ValueError) as refused:
            choices.set_answered_by(NO_SUCH)
        self.assertEqual(str(refused.exception), ERR_WIZARD_NO_SUCH_ANSWERER.format(value=NO_SUCH))
        for setter in (choices.set_role_plan, lambda way: choices.set_section_role(place=verse, way=way)):
            with self.assertRaises(ValueError) as refused:
                setter(NO_SUCH)
            self.assertEqual(str(refused.exception), ERR_WIZARD_NO_SUCH_WAY_BESIDE.format(value=NO_SUCH))
        for busy in (interplay.LEAST_BUSY - 1, interplay.MOST_BUSY + 1, True, NO_SUCH):
            with self.assertRaises(ValueError) as refused:
                choices.set_fills_busy(busy)
            self.assertEqual(str(refused.exception), ERR_WIZARD_FILLS_BUSY.format(low=interplay.LEAST_BUSY, high=interplay.MOST_BUSY, value=busy))

    def test_every_place_of_fills_busy_makes_a_song_of_its_own(self):
        choices = wizard()
        songs = []
        for busy in range(interplay.LEAST_BUSY, interplay.MOST_BUSY + 1):
            choices.set_fills_busy(busy)
            song = choices.made_setlist(name=SONG_NAME, version=VERSION).to_data()
            self.assertNotIn(song, songs, busy)
            songs.append(song)
