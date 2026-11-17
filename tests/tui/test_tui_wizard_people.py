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

"""Tests of a player as a person on the song wizard's player panels, and in the choices underneath: where the player comes in, where the player lays out, and how strongly the player answers to Energy."""

from llamatron.composition.file_format import Section
from llamatron.macro_composer.song_plan import HIGHEST_ENERGY, LOWEST_ENERGY, USUAL_CONTRAST
from llamatron.macro_composer.wizard_choices import AFTER_FIRST_VERSE, AFTER_THE_INTRO, FROM_THE_START, IN_BREAKDOWNS, NEVER_LAYS_OUT, WHEN_QUIET
from llamatron.strings.labels import MSG_WIZARD_COMES_IN_LABEL, MSG_WIZARD_LAYS_OUT_LABEL, MSG_WIZARD_OWN_START, MSG_WIZARD_REACTS_LABEL, MSG_WIZARD_REACTS_SAID
from llamatron.support.version import VERSION
from llamatron.tui import keybindings
from llamatron.tui.keys import Key
from tests.support.ui_testing import key_of
from tests.tui.test_tui_wizard import WizardTest

A_NAME = 'made'
A_GENRE = 'rock'
A_SUBGENRE = 'arena rock'
A_POP_GENRE = 'sixties_pop'
A_SEED = 11
THE_BASS = 'bass'
THE_DRUMS = 'drums'
THE_VERSE = 1
THE_BRIDGE = 'bridge'
NOT_A_WAY = 'sideways'


class TestWizardPeople(WizardTest):
    """Comes in, Lays out and Reacts."""

    def chosen(self, *, genre=A_GENRE):
        choices = self.choices()
        choices.set_genre(genre)
        choices.set_subgenre(A_SUBGENRE if genre == A_GENRE else choices.subgenres()[0])
        choices.set_seed(A_SEED)
        return choices

    def plays(self, *, choices, role):
        return [role in choices.section_plays(place) for place in range(len(choices.section_labels()))]

    def patterns(self, choices):
        return choices.made_setlist(name=A_NAME, version=VERSION).to_data()[Section.PATTERNS]

    def more(self):
        return key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET)

    async def to_player(self, role):
        choices = self.chosen()
        await self.press(Key.DOWN, Key.UP)
        await self.go_to_named_branch(choices.role_title(role))
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        return choices

    async def test_a_player_comes_in_where_asked_and_sits_out_every_section_before(self):
        choices = self.chosen()
        self.assertEqual(choices.get_comes_in(THE_BASS), FROM_THE_START)
        self.assertEqual(choices.comes_in_offered(THE_BASS)[0], FROM_THE_START)
        usual = self.patterns(choices)
        choices.set_comes_in(role=THE_BASS, way=AFTER_FIRST_VERSE)
        self.assertEqual(choices.get_comes_in(THE_BASS), AFTER_FIRST_VERSE)
        played = self.plays(choices=choices, role=THE_BASS)
        self.assertEqual(played[:THE_VERSE + 2], [False] * (THE_VERSE + 1) + [True])
        self.assertNotEqual(self.patterns(choices), usual)
        choices.set_comes_in(role=THE_BASS, way=AFTER_THE_INTRO)
        self.assertEqual(self.plays(choices=choices, role=THE_BASS)[:2], [False, True])
        again = type(choices).from_data(choices.to_data())
        self.assertEqual(again.get_comes_in(THE_BASS), AFTER_THE_INTRO)

    async def test_a_player_lays_out_never_in_the_breakdowns_or_whenever_it_is_quiet(self):
        choices = self.chosen()
        self.assertEqual(choices.lays_out_offered(THE_BASS), [NEVER_LAYS_OUT, IN_BREAKDOWNS, WHEN_QUIET])
        bridge = choices.section_kinds_in_form().index(THE_BRIDGE)
        choices.set_lays_out(role=THE_BASS, way=IN_BREAKDOWNS)
        self.assertEqual(choices.get_lays_out(THE_BASS), IN_BREAKDOWNS)
        self.assertFalse(self.plays(choices=choices, role=THE_BASS)[bridge])
        choices.set_lays_out(role=THE_BASS, way=WHEN_QUIET)
        quiet = [place for place, energy in enumerate(choices.energies()) if energy <= 4 and place]
        self.assertTrue(quiet)
        self.assertFalse(any(self.plays(choices=choices, role=THE_BASS)[place] for place in quiet))
        choices.set_lays_out(role=THE_BASS, way=NEVER_LAYS_OUT)
        self.assertTrue(self.plays(choices=choices, role=THE_BASS)[bridge])
        # A song with no plan has no quiet sections to name.
        choices.set_song_plan(False)
        self.assertNotIn(WHEN_QUIET, choices.lays_out_offered(THE_BASS))

    async def test_sections_changed_one_by_one_read_as_the_person_s_own_and_what_is_no_way_is_refused(self):
        choices = self.chosen()
        choices.set_section_plays(place=THE_VERSE + 1, role=THE_BASS, on=False)
        self.assertIsNone(choices.get_lays_out(THE_BASS))
        for setter in (choices.set_comes_in, choices.set_lays_out):
            with self.assertRaises(ValueError):
                setter(role=THE_BASS, way=NOT_A_WAY)
        for reacts in (LOWEST_ENERGY - 1, HIGHEST_ENERGY + 1, True):
            with self.assertRaises(ValueError):
                choices.set_reacts(role=THE_BASS, reacts=reacts)

    async def test_a_dramatic_player_and_an_even_one_play_a_planned_song_differently(self):
        choices = self.chosen()
        self.assertEqual(choices.get_reacts(THE_DRUMS), USUAL_CONTRAST)
        made = {}
        for reacts in (LOWEST_ENERGY, USUAL_CONTRAST, HIGHEST_ENERGY):
            choices.set_reacts(role=THE_DRUMS, reacts=reacts)
            self.assertEqual(choices.get_reacts(THE_DRUMS), reacts)
            made[reacts] = self.patterns(choices)
        self.assertNotEqual(made[LOWEST_ENERGY], made[HIGHEST_ENERGY])
        self.assertNotEqual(made[USUAL_CONTRAST], made[HIGHEST_ENERGY])
        self.assertFalse(self.chosen(genre=A_POP_GENRE).reacts(THE_DRUMS))

    async def test_the_player_s_panel_shows_the_three_and_steps_them(self):
        choices = await self.to_player(THE_BASS)
        shown = self.text()
        for said in (MSG_WIZARD_COMES_IN_LABEL, MSG_WIZARD_LAYS_OUT_LABEL, MSG_WIZARD_REACTS_LABEL, FROM_THE_START, NEVER_LAYS_OUT, MSG_WIZARD_REACTS_SAID[USUAL_CONTRAST]):
            self.assertIn(said, shown)
        await self.select_field(MSG_WIZARD_COMES_IN_LABEL)
        await self.press(self.more())
        self.assertEqual(choices.get_comes_in(THE_BASS), choices.comes_in_offered(THE_BASS)[1])
        await self.select_field(MSG_WIZARD_LAYS_OUT_LABEL)
        await self.press(self.more())
        self.assertEqual(choices.get_lays_out(THE_BASS), IN_BREAKDOWNS)
        await self.select_field(MSG_WIZARD_REACTS_LABEL)
        await self.press(self.more())
        self.assertEqual(choices.get_reacts(THE_BASS), USUAL_CONTRAST + 1)
        self.assertTrue(self.wizard().has_choices_to_lose())
        choices.set_section_plays(place=len(choices.section_labels()) - 2, role=THE_BASS, on=False)
        await self.press(Key.DOWN, Key.UP)
        self.assertIn(MSG_WIZARD_OWN_START, self.text())
