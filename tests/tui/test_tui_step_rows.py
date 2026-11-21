# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The tracker's Glide, Shorten, Rush and Drag: their list pages, their editors and their steps pages."""

from llamatron.model.objects import generator_settings
from llamatron.model.vocabulary import limits
from llamatron.model.vocabulary.file_format import GeneratorKind, Section
from llamatron.tui import keybindings
from llamatron.tui.keys import Key
from llamatron.tui.screens.generators import glide_editor
from llamatron.tui.screens.generators.drag_editor import DragEditor
from llamatron.tui.screens.generators.drag_steps_editor import DragStepsEditor
from llamatron.tui.screens.generators.glide_editor import GlideEditor
from llamatron.tui.screens.generators.glide_steps_editor import GlideStepsEditor
from llamatron.tui.screens.generators.rush_editor import RushEditor
from llamatron.tui.screens.generators.rush_steps_editor import RushStepsEditor
from llamatron.tui.screens.generators.shorten_editor import ShortenEditor
from llamatron.tui.screens.generators.shorten_steps_editor import ShortenStepsEditor
from llamatron.user_strings import labels
from tests.support import ui_testing
from tests.support.ui_testing import UITest

NEW_ONE = 'squelch'
MORE_THAN_ENOUGH = 5
SLIDES_STEPS = [True, False, False]


class TestGlideAdded(UITest):

    async def test_a_new_one_has_its_first_step_on(self):
        name = await self.add_generator(Section.GLIDES)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.GLIDE, name=name).get_steps(), generator_settings.NEW_STEP_ROW)


class TestGlideEditor(UITest):

    async def test_the_glide_amount_steps_through_its_lengths(self):
        await self.open_generator(section=Section.GLIDES)
        self.assertIsInstance(self.app.screen, GlideEditor)
        await self.select_field(labels.MSG_GLIDE_AMOUNT_LABEL)
        await self.press(keybindings.GlideEditor.MORE)
        expected = glide_editor.GLIDE_AMOUNTS[glide_editor.GLIDE_AMOUNTS.index(glide_editor.DEFAULT_GLIDE_AMOUNT_WRITTEN) + 1]
        self.assertEqual(str(self.document.song().get_generator_settings(kind=GeneratorKind.GLIDE, name=ui_testing.SLIDES).get_glide_amount()), expected)


class TestShortenEditor(UITest):

    async def test_the_shorten_amount_steps(self):
        await self.open_generator(section=Section.SHORTENS)
        self.assertIsInstance(self.app.screen, ShortenEditor)
        await self.select_field(labels.MSG_SHORTEN_LABEL)
        await self.press(keybindings.ShortenEditor.LESS)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.SHORTEN, name=ui_testing.CLIPS).get_shorten(), generator_settings.DEFAULT_SHORTEN - 1)


class TestRushEditor(UITest):

    async def test_the_rush_amount_stops_at_half_a_step(self):
        await self.open_generator(section=Section.RUSHES)
        self.assertIsInstance(self.app.screen, RushEditor)
        await self.select_field(labels.MSG_RUSH_AMOUNT_LABEL)
        await self.press(*[keybindings.RushEditor.MORE] * (limits.MAX_RUSH_OR_DRAG - generator_settings.DEFAULT_RUSH + MORE_THAN_ENOUGH))
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.RUSH, name=ui_testing.PUSH).get_amount(), limits.MAX_RUSH_OR_DRAG)


class TestDragEditor(UITest):

    async def test_the_drag_amount_steps(self):
        await self.open_generator(section=Section.DRAGS)
        self.assertIsInstance(self.app.screen, DragEditor)
        await self.select_field(labels.MSG_DRAG_AMOUNT_LABEL)
        await self.press(keybindings.DragEditor.MORE)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.DRAG, name=ui_testing.LAZY).get_amount(), generator_settings.DEFAULT_DRAG + 1)


class TestGlideStepsEditor(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_generator(section=Section.GLIDES)
        await self.select_field(labels.MSG_STEPS_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, GlideStepsEditor)

    def steps(self):
        return self.document.song().get_generator_settings(kind=GeneratorKind.GLIDE, name=ui_testing.SLIDES).get_steps()

    async def test_space_turns_a_step_on_and_off(self):
        await self.press(keybindings.GlideStepsEditor.TOGGLE)
        self.assertFalse(self.steps()[0])
        await self.press(keybindings.GlideStepsEditor.TOGGLE)
        self.assertTrue(self.steps()[0])

    async def test_steps_are_inserted_and_removed_within_their_limits(self):
        await self.press(*[keybindings.GlideStepsEditor.INSERT_STEP] * limits.MAX_STEP_ROW)
        self.assertEqual(len(self.steps()), limits.MAX_STEP_ROW)
        await self.press(*[keybindings.GlideStepsEditor.REMOVE_STEP] * limits.MAX_STEP_ROW)
        self.assertEqual(len(self.steps()), 1)

    async def test_the_cursor_stops_at_both_ends(self):
        await self.press(Key.LEFT)
        self.assertEqual(self.app.screen.step, 0)
        await self.press(*[Key.RIGHT] * (len(SLIDES_STEPS) + 1))
        self.assertEqual(self.app.screen.step, len(SLIDES_STEPS) - 1)


class TestShortenStepsEditor(UITest):

    async def test_space_turns_its_first_step_on(self):
        await self.open_generator(section=Section.SHORTENS)
        await self.select_field(labels.MSG_STEPS_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ShortenStepsEditor)
        before = self.document.song().get_generator_settings(kind=GeneratorKind.SHORTEN, name=ui_testing.CLIPS).get_steps()[0]
        await self.press(keybindings.ShortenStepsEditor.TOGGLE)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.SHORTEN, name=ui_testing.CLIPS).get_steps()[0], not before)


class TestRushStepsEditor(UITest):

    async def test_space_turns_its_first_step_on(self):
        await self.open_generator(section=Section.RUSHES)
        await self.select_field(labels.MSG_STEPS_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, RushStepsEditor)
        before = self.document.song().get_generator_settings(kind=GeneratorKind.RUSH, name=ui_testing.PUSH).get_steps()[0]
        await self.press(keybindings.RushStepsEditor.TOGGLE)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.RUSH, name=ui_testing.PUSH).get_steps()[0], not before)


class TestDragStepsEditor(UITest):

    async def test_space_turns_its_first_step_on(self):
        await self.open_generator(section=Section.DRAGS)
        await self.select_field(labels.MSG_STEPS_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, DragStepsEditor)
        before = self.document.song().get_generator_settings(kind=GeneratorKind.DRAG, name=ui_testing.LAZY).get_steps()[0]
        await self.press(keybindings.DragStepsEditor.TOGGLE)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.DRAG, name=ui_testing.LAZY).get_steps()[0], not before)
