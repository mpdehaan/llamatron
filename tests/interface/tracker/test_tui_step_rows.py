# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The tracker's Timing generator: its page, a section for each of Rush, Drag, Shorten and Glide, and the steps page of a row."""

from llamatron.engine.generators import timing as timing_plugin
from llamatron.engine.generators.timing import model as timing_model, parts, strings as timing_strings, view as timing_view
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.shared.plugin_editor import PluginEditor
from llamatron.interface.tracker.screens.shared.step_row_editor import StepRowEditor
from llamatron.model.schema import limits
from llamatron.user_strings import marks
from tests.support import ui_testing
from tests.support.ui_testing import UITest


def part_label(*, label, part):
    return label.format(part=timing_view.PART_NAMES[part])


class TestTimingAdded(UITest):

    async def test_a_new_one_changes_nothing(self):
        name = await self.add_generator(timing_plugin.SECTION)
        settings = self.document.get_setlist().get_generator_settings(kind=timing_plugin.NAME, name=name)
        self.assertEqual(settings.to_data(), {})
        for part in parts.PARTS:
            self.assertFalse(settings.step_row(part).is_lit())


class TimingPageTest(UITest):
    """A Timing generator's page, open on the test song's Timing generator, whose Rush and Glide have a step lit."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_generator(section=timing_plugin.SECTION)
        self.assertIsInstance(self.app.screen, PluginEditor)

    def settings(self):
        return self.document.get_setlist().get_generator_settings(kind=timing_plugin.NAME, name=ui_testing.LOOSE)

    async def open_part(self, part):
        await self.select_field(timing_view.PART_NAMES[part])
        await self.press(keybindings.FieldPage.TOGGLE)


class TestTimingPage(TimingPageTest):

    async def test_a_part_with_steps_written_says_it_is_set(self):
        self.assertEqual(self.text().count(marks.MSG_SECTION_SET), 2)

    async def test_the_rush_amount_starts_at_its_default_and_stops_at_half_a_step(self):
        await self.open_part(parts.RUSH)
        await self.select_field(part_label(label=timing_strings.MSG_AMOUNT_LABEL, part=parts.RUSH))
        await self.press(*[keybindings.PluginEditor.MORE] * (limits.MAX_RUSH_OR_DRAG + 1))
        self.assertEqual(self.settings().get_amount(parts.RUSH), limits.MAX_RUSH_OR_DRAG)

    async def test_a_drag_amount_back_at_its_default_is_left_out(self):
        await self.open_part(parts.DRAG)
        await self.select_field(part_label(label=timing_strings.MSG_AMOUNT_LABEL, part=parts.DRAG))
        await self.press(keybindings.PluginEditor.MORE)
        self.assertEqual(self.settings().get_amount(parts.DRAG), timing_model.DEFAULT_DRAG + 1)
        await self.press(keybindings.PluginEditor.LESS)
        self.assertIsNone(self.settings().get_written(parts.amount_of(parts.DRAG)))

    async def test_the_shorten_amount_stops_at_its_least(self):
        await self.open_part(parts.SHORTEN)
        await self.select_field(part_label(label=timing_strings.MSG_AMOUNT_LABEL, part=parts.SHORTEN))
        await self.press(*[keybindings.PluginEditor.LESS] * timing_model.DEFAULT_SHORTEN)
        self.assertEqual(self.settings().get_amount(parts.SHORTEN), limits.MIN_SHORTEN)

    async def test_the_glide_amount_steps_through_its_lengths(self):
        await self.open_part(parts.GLIDE)
        await self.select_field(part_label(label=timing_strings.MSG_AMOUNT_LABEL, part=parts.GLIDE))
        await self.press(keybindings.PluginEditor.MORE)
        after_default = timing_view.GLIDE_AMOUNTS[timing_view.GLIDE_AMOUNTS.index(timing_view.DEFAULT_GLIDE_WRITTEN) + 1]
        self.assertEqual(str(self.settings().get_written(parts.amount_of(parts.GLIDE))), after_default)

    async def test_a_step_is_chosen_and_the_pattern_step_given_back(self):
        await self.open_part(parts.RUSH)
        await self.select_field(part_label(label=timing_strings.MSG_STEP_LABEL, part=parts.RUSH))
        await self.press(keybindings.PluginEditor.MORE)
        self.assertIsNotNone(self.settings().step_row(parts.RUSH).get_step())
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.settings().step_row(parts.RUSH).get_step())


class TestStepRowEditor(TimingPageTest):
    """The steps page of a Timing generator's row: Space turns a step on and off, I and D insert and remove steps within their
    limits, and the cursor stops at both ends."""

    async def open_row(self, part):
        await self.open_part(part)
        await self.select_field(part_label(label=timing_strings.MSG_STEPS_LABEL, part=part))
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, StepRowEditor)

    def steps(self, part):
        return self.settings().step_row(part).get_steps()

    async def test_space_turns_a_step_on_and_off(self):
        await self.open_row(parts.GLIDE)
        await self.press(keybindings.StepRowEditor.TOGGLE)
        self.assertFalse(self.steps(parts.GLIDE)[0])
        await self.press(keybindings.StepRowEditor.TOGGLE)
        self.assertTrue(self.steps(parts.GLIDE)[0])

    async def test_a_part_with_no_row_shows_four_unlit_steps_and_lighting_one_writes_the_row(self):
        await self.open_row(parts.SHORTEN)
        self.assertFalse(self.settings().step_row(parts.SHORTEN).is_lit())
        await self.press(Key.RIGHT, keybindings.StepRowEditor.TOGGLE)
        self.assertEqual(self.steps(parts.SHORTEN), [False, True, False, False])
        self.assertIn(timing_view.PART_NOTES[parts.SHORTEN], self.text())

    async def test_steps_are_inserted_and_removed_within_their_limits(self):
        await self.open_row(parts.GLIDE)
        await self.press(*[keybindings.StepRowEditor.INSERT_STEP] * limits.MAX_STEP_ROW)
        self.assertEqual(len(self.steps(parts.GLIDE)), limits.MAX_STEP_ROW)
        await self.press(*[keybindings.StepRowEditor.REMOVE_STEP] * limits.MAX_STEP_ROW)
        self.assertEqual(len(self.steps(parts.GLIDE)), limits.MIN_STEP_ROW)

    async def test_the_cursor_stops_at_both_ends(self):
        await self.open_row(parts.RUSH)
        await self.press(Key.LEFT)
        self.assertEqual(self.app.screen.step, 0)
        await self.press(*[Key.RIGHT] * (len(ui_testing.LOOSE_RUSH) + 1))
        self.assertEqual(self.app.screen.step, len(ui_testing.LOOSE_RUSH) - 1)
