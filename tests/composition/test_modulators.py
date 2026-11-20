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

"""A modulator: its settings, what a file refuses, the values its wave takes from Start, upright and inverted, in every shape, and the
four modulators a song keeps and writes."""

from fractions import Fraction
import unittest
import yaml

from llamatron.composition import file_format, limits
from llamatron.composition.file_format import ModulatorName, ModulatorSetting, RateIn, Section, WaveShape
from llamatron.composition.file_layout import as_object_layout
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.modulator import Modulator
from llamatron.composition.setlist_writer import dump_setlist
from llamatron.composition.song_file_error import SongFileError
from llamatron.strings import errors
from tests.support.rendering import setlist_from_data, song_from_data
from tests.support.song_testing import with_parts

EIGHT = 8
TWELVE = 12
HALFWAY = 4
SIXTEENTHS = 16
EIGHTHS = 8
SEED = 5
TWO_BARS = '2'
HALF_A_HERTZ = 0.5
TOO_FINE = 0.005
TOO_FAST = 21
NOT_A_SHAPE = 'wobble'
OUT_OF_RANGE = limits.MAX_REGISTER_VALUE + 1


def wave(modulator, *, parts):
    """Return a modulator's values over one cycle and back to its start, at a number of equal parts of the cycle."""
    return [modulator.value_at(cycles=Fraction(part, parts)) for part in range(parts + 1)]


class TestWaves(unittest.TestCase):

    def test_a_triangle_rises_from_start_to_maximum_falls_to_minimum_and_comes_back(self):
        self.assertEqual(wave(Modulator(shape=WaveShape.TRIANGLE, maximum=EIGHT), parts=SIXTEENTHS), [*range(EIGHT + 1), *range(EIGHT - 1, -1, -1)])
        from_middle = wave(Modulator(shape=WaveShape.TRIANGLE, start=HALFWAY, maximum=EIGHT), parts=SIXTEENTHS)
        self.assertEqual(from_middle[:5], [4, 5, 6, 7, 8])
        self.assertEqual((from_middle[12], from_middle[-1]), (0, HALFWAY))

    def test_inverted_a_wave_falls_from_start_first(self):
        falling = wave(Modulator(shape=WaveShape.TRIANGLE, start=HALFWAY, maximum=EIGHT, invert=True), parts=SIXTEENTHS)
        self.assertEqual(falling[:5], [4, 3, 2, 1, 0])

    def test_a_sine_moves_smoothly_through_its_swing(self):
        values = wave(Modulator(shape=WaveShape.SINE, maximum=TWELVE), parts=SIXTEENTHS)
        self.assertEqual((values[0], values[8], values[-1]), (0, TWELVE, 0))
        self.assertTrue(all(abs(later - earlier) <= 2 for earlier, later in zip(values, values[1:])))

    def test_a_square_holds_its_maximum_for_the_first_half_and_inverted_its_minimum(self):
        self.assertEqual(wave(Modulator(shape=WaveShape.SQUARE, maximum=1), parts=EIGHTHS), [1, 1, 1, 1, 0, 0, 0, 0, 1])
        self.assertEqual(wave(Modulator(shape=WaveShape.SQUARE, maximum=1, invert=True), parts=EIGHTHS), [0, 0, 0, 0, 1, 1, 1, 1, 0])

    def test_a_saw_rises_and_drops_and_a_reverse_saw_falls_and_jumps(self):
        self.assertEqual(wave(Modulator(shape=WaveShape.SAW, maximum=EIGHT), parts=EIGHTHS), [0, 1, 2, 3, 4, 5, 6, 7, 0])
        self.assertEqual(wave(Modulator(shape=WaveShape.REVERSE_SAW, start=EIGHT, maximum=EIGHT), parts=EIGHTHS), [8, 7, 6, 5, 4, 3, 2, 1, 8])

    def test_a_sample_and_hold_holds_start_then_a_drawn_value_each_cycle_the_same_for_one_seed(self):
        modulator = Modulator(shape=WaveShape.SAMPLE_AND_HOLD, start=HALFWAY, maximum=EIGHT)
        drawn = [modulator.value_at(cycles=Fraction(half, 2), seed=SEED, name=ModulatorName.XMOD, origin=0) for half in range(EIGHTHS)]
        self.assertEqual(drawn[:2], [HALFWAY, HALFWAY])
        self.assertTrue(all(drawn[place] == drawn[place + 1] for place in range(0, EIGHTHS, 2)))
        self.assertTrue(all(0 <= value <= EIGHT for value in drawn))
        self.assertEqual(drawn, [modulator.value_at(cycles=Fraction(half, 2), seed=SEED, name=ModulatorName.XMOD, origin=0) for half in range(EIGHTHS)])

    def test_a_modulator_with_no_swing_stays_at_its_minimum(self):
        self.assertEqual(set(wave(Modulator(), parts=EIGHTHS)), {0})

    def test_a_cycle_lasts_its_bars_or_one_over_its_hertz(self):
        self.assertEqual(Modulator(bars=TWO_BARS).cycle_length(), 2)
        self.assertEqual(Modulator(rate_in=RateIn.HERTZ, hertz=HALF_A_HERTZ).cycle_length(), 2)
        self.assertTrue(Modulator().counts_bars())


class TestSettings(unittest.TestCase):

    def test_what_a_modulator_refuses(self):
        for settings in ({ModulatorSetting.SHAPE: NOT_A_SHAPE}, {ModulatorSetting.HERTZ: TOO_FINE}, {ModulatorSetting.HERTZ: TOO_FAST},
                         {ModulatorSetting.MAXIMUM: OUT_OF_RANGE}, {ModulatorSetting.MINIMUM: 1, ModulatorSetting.START: 0, ModulatorSetting.MAXIMUM: 2},
                         {ModulatorSetting.INVERT: NOT_A_SHAPE}):
            with self.subTest(settings=settings):
                with self.assertRaises(SongFileError):
                    Modulator.from_data(data=settings, where=ModulatorName.XMOD)

    def test_setting_holds_start_between_the_minimum_and_maximum(self):
        modulator = Modulator(maximum=EIGHT)
        modulator.set_setting(name=ModulatorSetting.START, value=HALFWAY)
        self.assertEqual(modulator.get_start(), HALFWAY)
        with self.assertRaises(InvalidValue):
            modulator.set_setting(name=ModulatorSetting.START, value=EIGHT + 1)
        with self.assertRaises(InvalidValue):
            modulator.set_setting(name=NOT_A_SHAPE, value=1)


class TestASongsModulators(unittest.TestCase):

    def test_a_song_has_four_modulators_and_writes_only_those_it_changed(self):
        song = song_from_data(with_parts())
        self.assertTrue(song.get_modulator(ModulatorName.ZMOD).is_default())
        song.set_modulator_setting(name=ModulatorName.XMOD, setting=ModulatorSetting.MAXIMUM, value=TWELVE)
        self.assertEqual(list(song.to_data()[Section.MODULATORS]), [ModulatorName.XMOD])
        song.set_modulator_setting(name=ModulatorName.XMOD, setting=ModulatorSetting.MAXIMUM, value=None)
        self.assertNotIn(Section.MODULATORS, song.to_data())
        with self.assertRaises(InvalidValue):
            song.set_modulator_setting(name=NOT_A_SHAPE, setting=ModulatorSetting.MAXIMUM, value=1)

    def test_a_songs_modulators_are_written_by_name_and_read_back(self):
        setlist = setlist_from_data(with_parts())
        song = setlist.get_song(setlist.get_song_names()[0])
        song.set_modulator_setting(name=ModulatorName.WMOD, setting=ModulatorSetting.SHAPE, value=WaveShape.SAW)
        song.set_modulator_setting(name=ModulatorName.WMOD, setting=ModulatorSetting.MAXIMUM, value=EIGHT)
        read = setlist_from_data(as_object_layout(yaml.safe_load(dump_setlist(setlist.to_data()))))
        self.assertEqual(read.get_song(setlist.get_song_names()[0]).get_modulator(ModulatorName.WMOD).get_shape(), WaveShape.SAW)

    def test_a_file_names_only_the_four_modulators(self):
        with self.assertRaises(SongFileError) as refused:
            song_from_data(with_parts(modulators={NOT_A_SHAPE: {}}))
        self.assertIn(errors.ERR_MODULATORS_NOT_NAMED.format(names=', '.join(file_format.MODULATOR_NAMES)), str(refused.exception))


if __name__ == '__main__':
    unittest.main()
