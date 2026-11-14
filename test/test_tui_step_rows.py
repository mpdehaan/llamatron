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
"""The tracker's Glide, Shorten, Rush and Drag: their list pages, their editors and their steps pages."""

from ui_testing import CLIPS, LAZY, PUSH, SLIDES, UITest
from llamatron.composition.file_format import Section, GeneratorKind
from llamatron.composition.generator_settings import DEFAULT_DRAG, DEFAULT_RUSH, DEFAULT_SHORTEN, NEW_STEP_ROW
from llamatron.composition.limits import MAX_RUSH_OR_DRAG, MAX_STEP_ROW
from llamatron.strings.labels import MSG_DRAG_AMOUNT_LABEL, MSG_GLIDE_AMOUNT_LABEL, MSG_RUSH_AMOUNT_LABEL, MSG_SHORTEN_LABEL, MSG_STEPS_LABEL
from llamatron.tui.keys import Key
from llamatron.tui.screens.drag_editor import DragEditor
from llamatron.tui.screens.glide_editor import DEFAULT_GLIDE_AMOUNT_WRITTEN, GLIDE_AMOUNTS, GlideEditor
from llamatron.tui.screens.glide_steps_editor import GlideStepsEditor
from llamatron.tui.screens.rush_editor import RushEditor
from llamatron.tui.screens.shorten_editor import ShortenEditor
from llamatron.tui.screens.shorten_steps_editor import ShortenStepsEditor
from llamatron.tui.screens.rush_steps_editor import RushStepsEditor
from llamatron.tui.screens.drag_steps_editor import DragStepsEditor
from llamatron.tui import keybindings

NEW_ONE = 'squelch'
MORE_THAN_ENOUGH = 5
SLIDES_STEPS = [True, False, False]


class TestGlideAdded(UITest):

    async def test_a_new_one_has_its_first_step_on(self):
        name = await self.add_generator(Section.GLIDES)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.GLIDE, name=name).get_steps(), NEW_STEP_ROW)


class TestGlideEditor(UITest):

    async def test_the_glide_amount_steps_through_its_lengths(self):
        await self.open_generator(section=Section.GLIDES)
        self.assertIsInstance(self.app.screen, GlideEditor)
        await self.select_field(MSG_GLIDE_AMOUNT_LABEL)
        await self.press(keybindings.GlideEditor.MORE)
        expected = GLIDE_AMOUNTS[GLIDE_AMOUNTS.index(DEFAULT_GLIDE_AMOUNT_WRITTEN) + 1]
        self.assertEqual(str(self.document.song().get_generator_settings(kind=GeneratorKind.GLIDE, name=SLIDES).get_glide_amount()), expected)


class TestShortenEditor(UITest):

    async def test_the_shorten_amount_steps(self):
        await self.open_generator(section=Section.SHORTENS)
        self.assertIsInstance(self.app.screen, ShortenEditor)
        await self.select_field(MSG_SHORTEN_LABEL)
        await self.press(keybindings.ShortenEditor.LESS)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.SHORTEN, name=CLIPS).get_shorten(), DEFAULT_SHORTEN - 1)


class TestRushEditor(UITest):

    async def test_the_rush_amount_stops_at_half_a_step(self):
        await self.open_generator(section=Section.RUSHES)
        self.assertIsInstance(self.app.screen, RushEditor)
        await self.select_field(MSG_RUSH_AMOUNT_LABEL)
        await self.press(*[keybindings.RushEditor.MORE] * (MAX_RUSH_OR_DRAG - DEFAULT_RUSH + MORE_THAN_ENOUGH))
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.RUSH, name=PUSH).get_amount(), MAX_RUSH_OR_DRAG)


class TestDragEditor(UITest):

    async def test_the_drag_amount_steps(self):
        await self.open_generator(section=Section.DRAGS)
        self.assertIsInstance(self.app.screen, DragEditor)
        await self.select_field(MSG_DRAG_AMOUNT_LABEL)
        await self.press(keybindings.DragEditor.MORE)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.DRAG, name=LAZY).get_amount(), DEFAULT_DRAG + 1)


class TestGlideStepsEditor(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_generator(section=Section.GLIDES)
        await self.select_field(MSG_STEPS_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, GlideStepsEditor)

    def steps(self):
        return self.document.song().get_generator_settings(kind=GeneratorKind.GLIDE, name=SLIDES).get_steps()

    async def test_space_turns_a_step_on_and_off(self):
        await self.press(keybindings.GlideStepsEditor.TOGGLE)
        self.assertFalse(self.steps()[0])
        await self.press(keybindings.GlideStepsEditor.TOGGLE)
        self.assertTrue(self.steps()[0])

    async def test_steps_are_inserted_and_removed_within_their_limits(self):
        await self.press(*[keybindings.GlideStepsEditor.INSERT_STEP] * MAX_STEP_ROW)
        self.assertEqual(len(self.steps()), MAX_STEP_ROW)
        await self.press(*[keybindings.GlideStepsEditor.REMOVE_STEP] * MAX_STEP_ROW)
        self.assertEqual(len(self.steps()), 1)

    async def test_the_cursor_stops_at_both_ends(self):
        await self.press(Key.LEFT)
        self.assertEqual(self.app.screen.step, 0)
        await self.press(*[Key.RIGHT] * (len(SLIDES_STEPS) + 1))
        self.assertEqual(self.app.screen.step, len(SLIDES_STEPS) - 1)


class TestShortenStepsEditor(UITest):

    async def test_space_turns_its_first_step_on(self):
        await self.open_generator(section=Section.SHORTENS)
        await self.select_field(MSG_STEPS_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ShortenStepsEditor)
        before = self.document.song().get_generator_settings(kind=GeneratorKind.SHORTEN, name=CLIPS).get_steps()[0]
        await self.press(keybindings.ShortenStepsEditor.TOGGLE)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.SHORTEN, name=CLIPS).get_steps()[0], not before)


class TestRushStepsEditor(UITest):

    async def test_space_turns_its_first_step_on(self):
        await self.open_generator(section=Section.RUSHES)
        await self.select_field(MSG_STEPS_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, RushStepsEditor)
        before = self.document.song().get_generator_settings(kind=GeneratorKind.RUSH, name=PUSH).get_steps()[0]
        await self.press(keybindings.RushStepsEditor.TOGGLE)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.RUSH, name=PUSH).get_steps()[0], not before)


class TestDragStepsEditor(UITest):

    async def test_space_turns_its_first_step_on(self):
        await self.open_generator(section=Section.DRAGS)
        await self.select_field(MSG_STEPS_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, DragStepsEditor)
        before = self.document.song().get_generator_settings(kind=GeneratorKind.DRAG, name=LAZY).get_steps()[0]
        await self.press(keybindings.DragStepsEditor.TOGGLE)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.DRAG, name=LAZY).get_steps()[0], not before)
