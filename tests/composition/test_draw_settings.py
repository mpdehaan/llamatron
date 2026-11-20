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

"""A draw in a set file and through its setters: its defaults, what a file refuses, and its range holding every slot."""

import unittest

from llamatron.composition import defaults, file_format, limits
from llamatron.composition.checks import listed
from llamatron.composition.draw import Draw
from llamatron.composition.file_format import DrawDirection, DrawName, DrawSetting, SceneSetting, Section
from llamatron.composition.song_file_error import SongFileError
from llamatron.strings import errors
from tests.support.rendering import as_setlist, setlist_from_data
from tests.support.song_testing import with_parts

SLOTS = [3, None, -2]
NOT_A_DIRECTION = 'sideways'
NOT_A_DRAW = 'ED'


def song_of(**parts):
    """Return the one song of a set made of parts."""
    return setlist_from_data(as_setlist(with_parts(**parts))).get_songs()[0]


class TestDrawSettings(unittest.TestCase):

    def test_a_draw_the_file_leaves_out_has_blank_slots_moving_forward_in_the_widest_range(self):
        draw = song_of().get_draw(DrawName.AD)
        self.assertEqual(draw.get_slots(), [None] * defaults.DEFAULT_DRAW_SLOT_COUNT)
        self.assertEqual((draw.get_direction(), draw.get_value_min(), draw.get_value_max()), (file_format.FORWARD, limits.MIN_DRAW_VALUE, limits.MAX_DRAW_VALUE))
        self.assertFalse(draw.redraws_in_conditions())
        self.assertTrue(draw.is_default())

    def test_a_draw_is_read_and_written_back_as_the_file_had_it(self):
        settings = {DrawSetting.DIRECTION: DrawDirection.SERIAL, DrawSetting.SLOTS: SLOTS, DrawSetting.CONDITIONS_REDRAW: True}
        setlist = setlist_from_data(as_setlist(with_parts(**{Section.DRAWS: {DrawName.BD: settings}})))
        written = next(iter(setlist.to_data()[Section.SONGS].values()))[Section.DRAWS]
        self.assertEqual(written, {DrawName.BD: settings})
        self.assertEqual(setlist.get_songs()[0].get_draw(DrawName.BD).filled_places(), [0, 2])

    def test_a_file_refuses_a_wrong_draw(self):
        for draws in (
            {NOT_A_DRAW: {}}, {DrawName.AD: {DrawSetting.DIRECTION: NOT_A_DIRECTION}}, {DrawName.AD: {DrawSetting.SLOTS: []}},
            {DrawName.AD: {DrawSetting.SLOTS: [0] * (limits.MAX_DRAW_SLOTS + 1)}}, {DrawName.AD: {DrawSetting.SLOTS: [limits.MAX_DRAW_VALUE + 1]}},
            {DrawName.AD: {DrawSetting.VALUE_MIN: 5, DrawSetting.VALUE_MAX: 4}}, {DrawName.AD: {DrawSetting.VALUE_MAX: 1, DrawSetting.SLOTS: [2]}},
            {DrawName.AD: {DrawSetting.CONDITIONS_REDRAW: 1}},
        ):
            with self.subTest(draws=draws), self.assertRaises(SongFileError):
                song_of(**{Section.DRAWS: draws})

    def test_a_scene_refuses_to_reset_a_draw_the_song_has_not(self):
        with self.assertRaises(SongFileError) as refused:
            song_of(scenes=[{SceneSetting.RESET_DRAWS: [NOT_A_DRAW], SceneSetting.TRACKS: {}}])
        self.assertIn(errors.ERR_BAD_RESET_DRAWS.format(names=listed(file_format.DRAW_NAMES), value=[NOT_A_DRAW]), str(refused.exception))

    def test_moving_an_end_of_the_range_moves_every_slot_past_it(self):
        song = song_of(**{Section.DRAWS: {DrawName.AD: {DrawSetting.SLOTS: [-5, 0, 9]}}})
        song.set_draw_setting(name=DrawName.AD, setting=DrawSetting.VALUE_MAX, value=4)
        song.set_draw_setting(name=DrawName.AD, setting=DrawSetting.VALUE_MIN, value=-1)
        self.assertEqual(song.get_draw(DrawName.AD).get_slots(), [-1, 0, 4])

    def test_a_value_typed_past_an_end_is_held_at_it_and_a_blank_is_kept(self):
        draw = Draw(**{DrawSetting.VALUE_MAX: 3})
        draw.set_slot(place=0, value=10)
        draw.set_slot(place=1, value=None)
        self.assertEqual(draw.get_slots()[:2], [3, None])

    def test_more_slots_are_blank_and_fewer_drop_the_last(self):
        song = song_of(**{Section.DRAWS: {DrawName.AD: {DrawSetting.SLOTS: [1, 2, 3]}}})
        song.set_draw_slot_count(name=DrawName.AD, count=5)
        self.assertEqual(song.get_draw(DrawName.AD).get_slots(), [1, 2, 3, None, None])
        song.set_draw_slot_count(name=DrawName.AD, count=2)
        self.assertEqual(song.get_draw(DrawName.AD).get_slots(), [1, 2])

    def test_a_draw_at_its_defaults_is_left_out_of_the_file(self):
        song = song_of(**{Section.DRAWS: {DrawName.AD: {DrawSetting.SLOTS: [1]}}})
        song.set_draw_setting(name=DrawName.AD, setting=DrawSetting.SLOTS, value=None)
        self.assertNotIn(Section.DRAWS, song.to_data())


if __name__ == '__main__':
    unittest.main()
