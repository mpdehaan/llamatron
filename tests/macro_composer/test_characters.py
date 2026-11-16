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

"""A player's character: a player put together from a style's levels by gauges, and the wizard's choice of each gauge."""

import unittest

from llamatron.macro_composer import arranger, characters, players
from llamatron.macro_composer.wizard_choices import USUAL_BUSY, WizardChoices
from llamatron.strings.errors import ERR_WIZARD_NO_SUCH_PLAYER_GAUGE, ERR_WIZARD_PLAYER_GAUGE
from llamatron.support.version import VERSION

ROCK = 'rock'
SONG_NAME = 'anthem'
NO_SUCH = 'no such'
PLAIN = characters.LEVELS[0]
HIGHEST_LEVEL = characters.LEVELS[-1]
# Two levels a number is blended between, and the number half way.
LOW = 4
HIGH = 10
HALF = 0.5
HALF_WAY = 7
SNARE = 'snare'
KICK = 'kick'
DRAG = 'drag'


def wizard():
    choices = WizardChoices()
    choices.set_genre(ROCK)
    choices.set_subgenre(choices.subgenres()[0])
    return choices


def patterns_of(choices):
    return choices.made_setlist(name=SONG_NAME, version=VERSION).to_data()


class TestCharacters(unittest.TestCase):
    """A character and the player it puts together."""

    def test_each_band_of_a_gauge_is_a_level_and_a_presets_place_is_in_its_levels_band(self):
        self.assertEqual([characters.level_at(place) for place in (characters.LOWEST, 4, 5, 9, 10, 14, 15, characters.HIGHEST)], [1, 1, 2, 2, 3, 3, 4, 4])
        for level in characters.LEVELS:
            self.assertEqual(characters.level_at(characters.PRESET_PLACE[level]), level)
            self.assertEqual(characters.level_of(characters.preset(level)), level)
            self.assertEqual(characters.label_of(characters.preset(level)), level)

    def test_a_level_is_its_preset_and_the_places_of_some_gauges_stand_on_the_plainest_preset(self):
        self.assertEqual(characters.character_of(HIGHEST_LEVEL), characters.preset(HIGHEST_LEVEL))
        moved = characters.character_of({characters.NOTES: characters.HIGHEST})
        self.assertEqual(moved, {**characters.preset(PLAIN), characters.NOTES: characters.HIGHEST})
        self.assertIsNone(characters.level_of(moved))
        self.assertNotIn(characters.label_of(moved), characters.LEVELS)

    def test_every_preset_puts_together_the_level_as_every_style_writes_it(self):
        for name in arranger.style_names():
            style = arranger.style_named(name)
            for instrument, levels in style.get(arranger.PLAYERS, {}).items():
                for level in levels:
                    with self.subTest(style=name, instrument=instrument, level=level):
                        self.assertEqual(arranger.player_of(style=style, instrument=instrument, character=characters.preset(level)), levels[level])

    def test_a_gauge_moved_takes_its_own_fields_from_another_level_and_leaves_the_rest(self):
        levels = arranger.style_named(ROCK)[arranger.PLAYERS][players.DRUMS]
        moved = {**characters.preset(PLAIN), characters.VARIETY: characters.PRESET_PLACE[HIGHEST_LEVEL]}
        player = characters.player_of(levels=levels, character=moved)
        self.assertEqual(player[characters.VARIES], levels[HIGHEST_LEVEL][characters.VARIES])
        self.assertEqual(player[characters.FILL], levels[PLAIN][characters.FILL])
        self.assertEqual(player[characters.FILL_EVERY], levels[PLAIN][characters.FILL_EVERY])
        self.assertEqual(player[characters.UNEVEN], levels[PLAIN][characters.UNEVEN])
        self.assertNotIn(characters.ADDS, player)
        # What a level says of itself is the preset's alone.
        self.assertNotIn(characters.SAYS, player)

    def test_a_number_is_blended_between_the_presets_and_timings_name_by_name(self):
        self.assertEqual(characters.blended(low=LOW, high=HIGH, share=HALF), HALF_WAY)
        self.assertEqual(characters.blended(low=None, high=HIGH, share=HALF), HIGH * HALF)
        self.assertEqual(characters.blended(low={SNARE: {DRAG: LOW}}, high={SNARE: {DRAG: HIGH}, KICK: {DRAG: HIGH}}, share=HALF), {SNARE: {DRAG: HALF_WAY}, KICK: {DRAG: HIGH * HALF}})
        # A number that comes to nothing is left out, and none falls below zero.
        self.assertEqual(characters.blended(low={SNARE: {DRAG: LOW}}, high=None, share=1), {})
        self.assertEqual(characters.blended(low=HIGH, high=LOW, share=HIGH), 0)

    def test_a_blended_field_rises_through_its_gauge_and_is_the_levels_own_at_each_preset(self):
        levels = arranger.style_named(ROCK)[arranger.PLAYERS][players.DRUMS]
        uneven = [characters.blend_at(levels=levels, field=characters.UNEVEN, place=place) for place in range(characters.LOWEST, characters.HIGHEST + 1)]
        self.assertEqual(uneven, sorted(uneven))
        self.assertEqual(uneven[characters.LOWEST], 0)
        self.assertGreater(uneven[characters.HIGHEST], levels[HIGHEST_LEVEL][characters.UNEVEN])
        for level in characters.LEVELS:
            self.assertEqual(uneven[characters.PRESET_PLACE[level]], levels[level][characters.UNEVEN])

    def test_a_section_holds_a_gauge_above_the_level_it_allows_to_that_levels_place(self):
        character = {**characters.preset(HIGHEST_LEVEL), characters.NOTES: characters.LOWEST}
        held = characters.held_to(character=character, allowed=2)
        self.assertEqual(held[characters.NOTES], characters.LOWEST)
        self.assertEqual(held[characters.VARIETY], characters.PRESET_PLACE[2])
        self.assertEqual(characters.held_to(character=character, allowed=None), character)
        self.assertEqual(characters.held_to(character=characters.preset(HIGHEST_LEVEL), allowed=2), characters.preset(2))

    def test_an_instrument_has_the_gauges_its_levels_say_anything_by(self):
        style_players = arranger.style_named(ROCK)[arranger.PLAYERS]
        self.assertEqual(characters.gauges_of(style_players[players.DRUMS]), [characters.NOTES, characters.VARIETY, characters.TOUCH, characters.LOOSE, characters.FILLS])
        self.assertEqual(characters.gauges_of(style_players[players.BASS]), [characters.VARIETY, characters.LOOSE])
        self.assertEqual(characters.gauges_of(style_players[players.RHYTHM]), [characters.VARIETY, characters.STRUMMING])

    def test_no_player_where_the_style_has_no_levels_or_the_song_names_no_player(self):
        self.assertEqual(characters.player_of(levels={}, character=characters.preset(PLAIN)), {})
        self.assertEqual(characters.player_of(levels=arranger.style_named(ROCK)[arranger.PLAYERS][players.DRUMS], character=None), {})


class TestWizardPlayerGauges(unittest.TestCase):
    """The wizard's choice of each gauge of a player."""

    def drums(self, choices):
        return next(role for role in choices.roles() if not choices.has_sound(role))

    def test_each_gauge_stands_at_the_presets_place_until_moved_and_a_moved_gauge_changes_the_song(self):
        choices = wizard()
        drums = self.drums(choices)
        usual = patterns_of(choices)
        self.assertEqual(choices.player_preset(drums), USUAL_BUSY)
        for gauge in choices.player_gauges(drums):
            self.assertEqual(choices.get_player_gauge(role=drums, gauge=gauge), characters.PRESET_PLACE[USUAL_BUSY])
        choices.set_player_gauge(role=drums, gauge=characters.FILLS, place=characters.HIGHEST)
        self.assertEqual(choices.get_player_gauge(role=drums, gauge=characters.FILLS), characters.HIGHEST)
        self.assertIsNone(choices.player_preset(drums))
        self.assertNotEqual(patterns_of(choices), usual)
        # Moved back to the preset's place, the gauge is the preset's again, and so is the song.
        choices.set_player_gauge(role=drums, gauge=characters.FILLS, place=characters.PRESET_PLACE[USUAL_BUSY])
        self.assertEqual(choices.player_preset(drums), USUAL_BUSY)
        self.assertEqual(patterns_of(choices), usual)

    def test_a_preset_chosen_puts_every_gauge_back_and_the_gauges_are_kept_with_the_song(self):
        choices = wizard()
        drums = self.drums(choices)
        choices.set_player_gauge(role=drums, gauge=characters.LOOSE, place=characters.LOWEST)
        choices.set_player_gauge(role=drums, gauge=characters.VARIETY, place=characters.HIGHEST)
        # The song is made first, since making a song gives the choices their seed, which is kept with them.
        made = patterns_of(choices)
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual(again.get_player_gauge(role=drums, gauge=characters.LOOSE), characters.LOWEST)
        self.assertEqual(again.get_player_gauge(role=drums, gauge=characters.VARIETY), characters.HIGHEST)
        self.assertEqual(patterns_of(again), made)
        choices.set_busy(role=drums, level=HIGHEST_LEVEL)
        self.assertEqual(choices.player_preset(drums), HIGHEST_LEVEL)
        self.assertEqual(choices.get_player_gauge(role=drums, gauge=characters.LOOSE), characters.PRESET_PLACE[HIGHEST_LEVEL])
        self.assertNotIn(characters.LOOSE, str(choices.to_data().get(arranger.PLAYERS)))

    def test_what_is_no_gauge_of_the_player_and_no_place_is_refused(self):
        choices = wizard()
        drums = self.drums(choices)
        for gauge in (NO_SUCH, characters.STRUMMING):
            with self.assertRaises(ValueError) as refused:
                choices.set_player_gauge(role=drums, gauge=gauge, place=characters.LOWEST)
            self.assertEqual(str(refused.exception), ERR_WIZARD_NO_SUCH_PLAYER_GAUGE.format(value=gauge))
            with self.assertRaises(ValueError):
                choices.get_player_gauge(role=drums, gauge=gauge)
        for place in (characters.LOWEST - 1, characters.HIGHEST + 1, True, NO_SUCH):
            with self.assertRaises(ValueError) as refused:
                choices.set_player_gauge(role=drums, gauge=characters.NOTES, place=place)
            self.assertEqual(str(refused.exception), ERR_WIZARD_PLAYER_GAUGE.format(low=characters.LOWEST, high=characters.HIGHEST, value=place))
