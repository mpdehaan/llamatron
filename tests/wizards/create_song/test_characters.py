# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A player's character: a player put together from a style's levels by gauges, and the wizard's choice of each gauge."""

import unittest

from llamatron.model.file import version
from llamatron.user_strings import errors
from llamatron.wizards.create_song import arranger, characters, players, wizard_limits, wizard_names
from llamatron.wizards.create_song.wizard_choices import WizardChoices

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
    return choices.made_setlist(name=SONG_NAME, version=version.VERSION).to_data()


class TestCharacters(unittest.TestCase):
    """A character and the player it puts together."""

    def test_each_band_of_a_gauge_is_a_level_and_a_presets_place_is_in_its_levels_band(self):
        self.assertEqual([characters.level_at(place) for place in (wizard_names.CHARACTERS_LOWEST, 4, 5, 9, 10, 14, 15, wizard_names.CHARACTERS_HIGHEST)], [1, 1, 2, 2, 3, 3, 4, 4])
        for level in characters.LEVELS:
            self.assertEqual(characters.level_at(characters.PRESET_PLACE[level]), level)
            self.assertEqual(characters.level_of(characters.preset(level)), level)
            self.assertEqual(characters.label_of(characters.preset(level)), level)

    def test_a_level_is_its_preset_and_the_places_of_some_gauges_stand_on_the_plainest_preset(self):
        self.assertEqual(characters.character_of(HIGHEST_LEVEL), characters.preset(HIGHEST_LEVEL))
        moved = characters.character_of({characters.NOTES: wizard_names.CHARACTERS_HIGHEST})
        self.assertEqual(moved, {**characters.preset(PLAIN), characters.NOTES: wizard_names.CHARACTERS_HIGHEST})
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
        uneven = [characters.blend_at(levels=levels, field=characters.UNEVEN, place=place) for place in range(wizard_names.CHARACTERS_LOWEST, wizard_names.CHARACTERS_HIGHEST + 1)]
        self.assertEqual(uneven, sorted(uneven))
        self.assertEqual(uneven[wizard_names.CHARACTERS_LOWEST], 0)
        self.assertGreater(uneven[wizard_names.CHARACTERS_HIGHEST], levels[HIGHEST_LEVEL][characters.UNEVEN])
        for level in characters.LEVELS:
            self.assertEqual(uneven[characters.PRESET_PLACE[level]], levels[level][characters.UNEVEN])

    def test_a_section_holds_a_gauge_above_the_level_it_allows_to_that_levels_place(self):
        character = {**characters.preset(HIGHEST_LEVEL), characters.NOTES: wizard_names.CHARACTERS_LOWEST}
        held = characters.held_to(character=character, allowed=2)
        self.assertEqual(held[characters.NOTES], wizard_names.CHARACTERS_LOWEST)
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
        return next(role for role in choices.get_band().roles() if not choices.get_sounds().has_sound(role))

    def test_each_gauge_stands_at_the_presets_place_until_moved_and_a_moved_gauge_changes_the_song(self):
        choices = wizard()
        drums = self.drums(choices)
        usual = patterns_of(choices)
        self.assertEqual(choices.player(drums).preset(), wizard_limits.USUAL_BUSY)
        for gauge in choices.player(drums).gauges():
            self.assertEqual(choices.player(drums).get_gauge(gauge=gauge), characters.PRESET_PLACE[wizard_limits.USUAL_BUSY])
        choices.player(drums).set_gauge(gauge=characters.FILLS, place=wizard_names.CHARACTERS_HIGHEST)
        self.assertEqual(choices.player(drums).get_gauge(gauge=characters.FILLS), wizard_names.CHARACTERS_HIGHEST)
        self.assertIsNone(choices.player(drums).preset())
        self.assertNotEqual(patterns_of(choices), usual)
        # Moved back to the preset's place, the gauge is the preset's again, and so is the song.
        choices.player(drums).set_gauge(gauge=characters.FILLS, place=characters.PRESET_PLACE[wizard_limits.USUAL_BUSY])
        self.assertEqual(choices.player(drums).preset(), wizard_limits.USUAL_BUSY)
        self.assertEqual(patterns_of(choices), usual)

    def test_a_preset_chosen_puts_every_gauge_back_and_the_gauges_are_kept_with_the_song(self):
        choices = wizard()
        drums = self.drums(choices)
        choices.player(drums).set_gauge(gauge=characters.LOOSE, place=wizard_names.CHARACTERS_LOWEST)
        choices.player(drums).set_gauge(gauge=characters.VARIETY, place=wizard_names.CHARACTERS_HIGHEST)
        # The song is made first, since making a song gives the choices their seed, which is kept with them.
        made = patterns_of(choices)
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual(again.player(drums).get_gauge(gauge=characters.LOOSE), wizard_names.CHARACTERS_LOWEST)
        self.assertEqual(again.player(drums).get_gauge(gauge=characters.VARIETY), wizard_names.CHARACTERS_HIGHEST)
        self.assertEqual(patterns_of(again), made)
        choices.player(drums).set_busy(level=HIGHEST_LEVEL)
        self.assertEqual(choices.player(drums).preset(), HIGHEST_LEVEL)
        self.assertEqual(choices.player(drums).get_gauge(gauge=characters.LOOSE), characters.PRESET_PLACE[HIGHEST_LEVEL])
        self.assertNotIn(characters.LOOSE, str(choices.to_data().get(arranger.PLAYERS)))

    def test_what_is_no_gauge_of_the_player_and_no_place_is_refused(self):
        choices = wizard()
        drums = self.drums(choices)
        for gauge in (NO_SUCH, characters.STRUMMING):
            with self.assertRaises(ValueError) as refused:
                choices.player(drums).set_gauge(gauge=gauge, place=wizard_names.CHARACTERS_LOWEST)
            self.assertEqual(str(refused.exception), errors.ERR_WIZARD_NO_SUCH_PLAYER_GAUGE.format(value=gauge))
            with self.assertRaises(ValueError):
                choices.player(drums).get_gauge(gauge=gauge)
        for place in (wizard_names.CHARACTERS_LOWEST - 1, wizard_names.CHARACTERS_HIGHEST + 1, True, NO_SUCH):
            with self.assertRaises(ValueError) as refused:
                choices.player(drums).set_gauge(gauge=characters.NOTES, place=place)
            self.assertEqual(str(refused.exception), errors.ERR_WIZARD_PLAYER_GAUGE.format(low=wizard_names.CHARACTERS_LOWEST, high=wizard_names.CHARACTERS_HIGHEST, value=place))
