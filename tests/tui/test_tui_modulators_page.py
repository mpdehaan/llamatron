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

"""The Modulators page: a grid of the four modulators by their settings, each column stepped, typed or chosen, the Rate a list of bars
or a number of hertz as Rate in says."""

from llamatron.composition.file_format import ModulatorName, ModulatorSetting, RateIn, WaveShape
from llamatron.strings import labels, marks
from llamatron.tui import keybindings
from llamatron.tui.keys import Key
from llamatron.tui.screens.set.modulators_page import ModulatorsPage
from tests.support.ui_testing import key_of, UITest

# Where each setting stands among a modulator's columns.
SHAPE = 0
RATE = 1
RATE_IN = 2
START = 4
MAXIMUM = 5
INVERT = 6
TYPED_HERTZ = '0.5'
HALF_A_HERTZ = 0.5
NOT_A_NUMBER = 'fast'
ONE_HUNDREDTH_MORE = 1.01


def label(*, name, column):
    return labels.MSG_MODULATOR_FIELD_LABEL.format(name=name, what=labels.MSG_MODULATOR_FIELD_WHATS[column])


class TestModulatorsPage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.MODULATORS)
        self.assertIsInstance(self.app.screen, ModulatorsPage)

    def modulator(self, name):
        return self.document.song().get_modulator(name)

    async def more(self):
        await self.press(key_of(binding=keybindings.ModulatorsPage.MORE, key=Key.RIGHT_BRACKET))

    async def test_the_grid_has_a_row_for_each_modulator_and_a_column_for_each_setting(self):
        shown = self.text()
        for name in (ModulatorName.XMOD, ModulatorName.WMOD, ModulatorName.YMOD, ModulatorName.ZMOD):
            self.assertIn(name, shown)
        for heading in labels.MSG_MODULATOR_COLUMNS:
            self.assertIn(heading, shown)
        self.assertIn(labels.MSG_WAVE_SHAPE_NAMES[WaveShape.SINE], shown)

    async def test_stepping_the_shape_and_the_maximum_and_the_start_held_below_the_maximum(self):
        await self.select_field(label(name=ModulatorName.XMOD, column=SHAPE))
        await self.more()
        self.assertEqual(self.modulator(ModulatorName.XMOD).get_shape(), WaveShape.TRIANGLE)
        await self.select_field(label(name=ModulatorName.XMOD, column=MAXIMUM))
        await self.more()
        self.assertEqual(self.modulator(ModulatorName.XMOD).get_maximum(), 1)
        await self.select_field(label(name=ModulatorName.XMOD, column=START))
        await self.more()
        await self.more()
        self.assertEqual(self.modulator(ModulatorName.XMOD).get_start(), 1)

    async def test_space_switches_invert_and_a_sample_and_hold_shows_it_blocked(self):
        await self.select_field(label(name=ModulatorName.YMOD, column=INVERT))
        await self.press(Key.SPACE)
        self.assertTrue(self.modulator(ModulatorName.YMOD).is_inverted())
        self.document.set_modulator_setting(name=ModulatorName.YMOD, setting=ModulatorSetting.SHAPE, value=WaveShape.SAMPLE_AND_HOLD)
        await self.settle()
        self.assertEqual(self.app.screen.field().value(), marks.MSG_BLOCKED_CELL)

    async def test_the_rate_is_a_list_of_bars_until_rate_in_says_hertz_then_a_number_stepped_and_typed(self):
        await self.select_field(label(name=ModulatorName.ZMOD, column=RATE))
        await self.more()
        self.assertEqual(self.modulator(ModulatorName.ZMOD).get_setting(ModulatorSetting.BARS), '2')
        await self.select_field(label(name=ModulatorName.ZMOD, column=RATE_IN))
        await self.more()
        self.assertEqual(self.modulator(ModulatorName.ZMOD).get_rate_in(), RateIn.HERTZ)
        await self.select_field(label(name=ModulatorName.ZMOD, column=RATE))
        self.assertEqual(self.app.screen.field().value(), marks.MSG_HERTZ.format(1))
        await self.more()
        self.assertEqual(self.modulator(ModulatorName.ZMOD).get_setting(ModulatorSetting.HERTZ), ONE_HUNDREDTH_MORE)
        await self.press(keybindings.ModulatorsPage.ENTER)
        self.app.screen.value = TYPED_HERTZ
        await self.press(Key.ENTER)
        self.assertEqual(self.modulator(ModulatorName.ZMOD).get_setting(ModulatorSetting.HERTZ), HALF_A_HERTZ)
        await self.press(keybindings.ModulatorsPage.ENTER)
        self.app.screen.value = NOT_A_NUMBER
        await self.press(Key.ENTER)
        self.assertIn(NOT_A_NUMBER, self.text())
        self.assertEqual(self.modulator(ModulatorName.ZMOD).get_setting(ModulatorSetting.HERTZ), HALF_A_HERTZ)
