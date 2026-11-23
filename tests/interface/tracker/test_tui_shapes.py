# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The tracker's Density, Swell and Articulate: the Shapes generator's page, the sections on the Scene page and the clip page, and the settings pages' sections that hold them."""

from llamatron.engine.generators import shapes as shapes_plugin
from llamatron.engine.generators.shapes import model as shapes_model, strings as shapes_strings
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.arrange.clip_page import ClipPage
from llamatron.interface.tracker.screens.arrange.scene_page import ScenePage
from llamatron.interface.tracker.screens.shared.plugin_editor import PluginEditor
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import Shape, shape_setting, ShapePart
from llamatron.user_strings import labels as labels_text, marks
from tests.support import ui_testing
from tests.support.ui_testing import UITest

FULL = 100
HALF = 50


def part_label(*, shape, part):
    return labels_text.MSG_SHAPE_FIELD_LABELS[part].format(shape=labels_text.MSG_SHAPE_NAMES[shape])


class TestShapesAdded(UITest):

    async def test_a_new_one_changes_nothing(self):
        name = await self.add_generator(shapes_plugin.SECTION)
        self.assertEqual(self.document.get_setlist().get_generator_settings(kind=shapes_plugin.NAME, name=name).to_data(), {})


class TestShapesPage(UITest):
    """A Shapes generator's page: Density, Swell and Articulate, each a section closed until opened, with its start, end, over and
    then; a Swell accent; and Restart. It opens on the test song's Shapes generator, whose Density and Swell start are set."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_generator(section=shapes_plugin.SECTION)
        self.assertIsInstance(self.app.screen, PluginEditor)

    def settings(self):
        return self.document.get_setlist().get_generator_settings(kind=shapes_plugin.NAME, name=ui_testing.SHAPED)

    async def open_section(self, shape):
        await self.select_field(labels_text.MSG_SHAPE_NAMES[shape])
        await self.press(keybindings.FieldPage.TOGGLE)

    async def test_every_shape_is_a_section_saying_whether_it_is_set(self):
        text = self.text()
        for shape in file_format.SHAPES:
            self.assertIn(heading_text(shape=shape, is_open=False), text)
        self.assertEqual(text.count(marks.MSG_SECTION_SET), 2)

    async def test_density_start_steps_and_clears(self):
        await self.open_section(Shape.DENSITY)
        await self.select_field(part_label(shape=Shape.DENSITY, part=ShapePart.START))
        await self.press(keybindings.PluginEditor.MORE)
        self.assertEqual(self.settings().get_shape(Shape.DENSITY).start, ui_testing.SHAPED_DENSITY_START + 1)
        await self.press(Key.BACKSPACE)
        # With its start and end both blank, the Density is no longer in force.
        self.assertIsNone(self.settings().get_shape(Shape.DENSITY))

    async def test_density_end_stops_at_the_top(self):
        await self.open_section(Shape.DENSITY)
        await self.select_field(part_label(shape=Shape.DENSITY, part=ShapePart.END))
        await self.press(keybindings.PluginEditor.MORE)
        self.assertEqual(self.settings().get_shape(Shape.DENSITY).end, FULL)

    async def test_then_steps_and_over_steps_from_the_whole_span_to_a_length(self):
        await self.open_section(Shape.SWELL)
        await self.select_field(part_label(shape=Shape.SWELL, part=ShapePart.THEN))
        await self.press(keybindings.PluginEditor.MORE)
        self.assertEqual(self.settings().get_shape(Shape.SWELL).then, file_format.SHAPE_THENS[1])
        await self.select_field(part_label(shape=Shape.SWELL, part=ShapePart.OVER))
        await self.press(keybindings.PluginEditor.MORE)
        self.assertIsNotNone(self.settings().get_shape(Shape.SWELL).over)

    async def test_the_swell_accent_steps_up_to_its_most(self):
        await self.select_field(shapes_strings.MSG_SWELL_ACCENT_LABEL)
        await self.press(*[keybindings.PluginEditor.MORE] * (limits.MAX_ACCENT + 1))
        self.assertEqual(self.settings().get_written(shapes_model.SWELL_ACCENT), limits.MAX_ACCENT)
        self.assertEqual(self.settings().get_shape(Shape.SWELL).accent, limits.MAX_ACCENT)

    async def test_articulate_start_stops_at_its_least(self):
        await self.open_section(Shape.ARTICULATE)
        await self.select_field(part_label(shape=Shape.ARTICULATE, part=ShapePart.START))
        await self.press(Key.ENTER)
        self.app.screen.value = str(limits.MIN_ARTICULATE)
        await self.press(Key.ENTER, keybindings.PluginEditor.LESS)
        self.assertEqual(self.settings().get_shape(Shape.ARTICULATE).start, limits.MIN_ARTICULATE)
        self.assertEqual(self.settings().get_shape(Shape.ARTICULATE).end, FULL)

    async def test_restart_is_chosen(self):
        await self.select_field(labels_text.MSG_RESTART_LABEL)
        await self.press(keybindings.PluginEditor.MORE)
        self.assertIsNotNone(self.settings().get_written(file_format.GENERATOR_RESTART))


def heading_text(*, shape, is_open):
    return labels_text.MSG_SECTION_LABEL.format(mark=marks.MSG_SECTION_OPEN_MARK if is_open else marks.MSG_SECTION_CLOSED_MARK, name=labels_text.MSG_SHAPE_NAMES[shape])


class TestShapesOnTheScenePage(UITest):
    """On the Scene page, the Shapes tab holds Density and Articulate, each a column; a scene has no Swell, its velocity and
    velocity ramps saying how loud it plays."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.app.screen.show_page(ScenePage(holder=self.app.screen.holder, index=0))
        await self.pilot.pause()
        self.page = self.app.screen

    async def test_the_shapes_tab_steps_the_scenes_own_articulate(self):
        start = labels_text.MSG_SHAPE_FIELD_LABELS[ShapePart.START].format(shape=labels_text.MSG_SHAPE_NAMES[Shape.ARTICULATE])
        shapes = next(tab for tab in self.page.tab_box().tabs if tab.label == labels_text.MSG_SHAPES_TAB)
        self.assertEqual([column.heading for column in shapes.columns], [labels_text.MSG_SHAPE_NAMES[shape] for shape in file_format.PLACED_SHAPES])
        await self.select_field(start)
        await self.press(keybindings.FieldPage.LESS)
        self.assertEqual(self.document.song().get_scenes()[0].get_shape(Shape.ARTICULATE).start, FULL - 1)


class TestShapeSectionsOnTheClipPage(UITest):
    """On the clip page the same sections set the clip's own, over its scene's."""

    async def test_a_clips_density_is_its_own(self):
        self.app.screen.show_page(ClipPage(holder=self.app.screen.holder, index=0, track=ui_testing.LEAD))
        await self.pilot.pause()
        await self.select_field(labels_text.MSG_SHAPE_FIELD_LABELS[ShapePart.END].format(shape=labels_text.MSG_SHAPE_NAMES[Shape.DENSITY]))
        await self.press(Key.ENTER)
        self.app.screen.value = str(HALF)
        await self.press(Key.ENTER)
        clip_slot = self.document.song().get_scenes()[0].get_clip_slot(ui_testing.LEAD)
        self.assertEqual(clip_slot.get_written(shape_setting(shape=Shape.DENSITY, part=ShapePart.END)), HALF)
        self.assertIsNone(self.document.song().get_scenes()[0].get_shape(Shape.DENSITY))
        # Once set, it shows as a percentage, and a part left blank shows none.
        self.assertEqual(self.app.screen.field().value(), marks.MSG_SHAPE_PERCENT_SHOWN.format(percent=HALF))
        await self.select_field(labels_text.MSG_SHAPE_FIELD_LABELS[ShapePart.START].format(shape=labels_text.MSG_SHAPE_NAMES[Shape.DENSITY]))
        self.assertEqual(self.app.screen.field().value(), marks.MSG_NONE_SHOWN)
