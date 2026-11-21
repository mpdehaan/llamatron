# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The tracker's Density, Swell and Articulate: their list pages and editors, the sections on the Scene page and the clip page, and the settings pages' sections that hold them."""

from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import GeneratorKind, RampWay, Section, Shape, shape_setting, ShapePart
from llamatron.tui import keybindings
from llamatron.tui.keys import Key
from llamatron.tui.screens.arrange.clip_page import ClipPage
from llamatron.tui.screens.arrange.scene_page import ScenePage
from llamatron.tui.screens.generators.articulate_editor import ArticulateEditor
from llamatron.tui.screens.generators.density_editor import DensityEditor
from llamatron.tui.screens.generators.swell_editor import SwellEditor
from llamatron.tui.screens.shared.field import Heading
from llamatron.user_strings import labels as labels_text, marks
from tests.support import ui_testing
from tests.support.ui_testing import back_key, forward_key, UITest

# What a test names the generator it adds.
NEW_ONE = 'lift'
# The start each test song's shape generator was given.
THIN_START = 50
FADE_START = 80
CLIPPED_START = 50
FULL = 100
HALF = 50


class TestDensityAdded(UITest):

    async def test_a_new_one_changes_nothing(self):
        name = await self.add_generator(Section.DENSITIES)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.DENSITY, name=name).to_data(), {})


class ShapeEditorTest(UITest):
    """What a shape generator's editor shares: it opens on the test song's one generator of its kind."""

    SECTION = None
    PAGE = None
    KIND = None
    NAME = None

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_generator(section=self.SECTION)
        self.assertIsInstance(self.app.screen, self.PAGE)

    def shape(self):
        return self.document.song().get_generator_settings(kind=self.KIND, name=self.NAME).get_shape()


class TestDensityEditor(ShapeEditorTest):
    """A Density's editor: start and end step within 0 to 100, Bksp leaves one blank, and over and then are chosen."""

    SECTION = Section.DENSITIES
    PAGE = DensityEditor
    KIND = GeneratorKind.DENSITY
    NAME = ui_testing.THIN

    async def test_start_steps_and_clears(self):
        await self.select_field(labels_text.MSG_SHAPE_PART_LABELS[ShapePart.START])
        await self.press(keybindings.DensityEditor.MORE)
        self.assertEqual(self.shape().start, THIN_START + 1)
        await self.press(Key.BACKSPACE)
        self.assertEqual(self.shape().start, FULL)

    async def test_end_stops_at_the_top(self):
        await self.select_field(labels_text.MSG_SHAPE_PART_LABELS[ShapePart.END])
        await self.press(keybindings.DensityEditor.MORE)
        self.assertEqual(self.shape().end, FULL)

    async def test_then_steps_through_hold_repeat_and_bounce(self):
        self.assertEqual(self.shape().then, file_format.SHAPE_THENS[0])
        await self.select_field(labels_text.MSG_SHAPE_PART_LABELS[ShapePart.THEN])
        await self.press(keybindings.DensityEditor.MORE)
        self.assertEqual(self.shape().then, file_format.SHAPE_THENS[1])

    async def test_over_steps_from_the_whole_clip_to_a_length(self):
        self.assertIsNone(self.shape().over)
        await self.select_field(labels_text.MSG_SHAPE_PART_LABELS[ShapePart.OVER])
        await self.press(keybindings.DensityEditor.MORE)
        self.assertIsNotNone(self.shape().over)

    async def test_it_has_no_accent(self):
        self.assertNotIn(labels_text.MSG_ACCENT_LABEL, [field.label for field in self.app.screen.fields()])


class TestSwellEditor(ShapeEditorTest):
    """A Swell's editor has an accent besides, up to its most."""

    SECTION = Section.SWELLS
    PAGE = SwellEditor
    KIND = GeneratorKind.SWELL
    NAME = ui_testing.FADE

    async def test_the_accent_steps_up_to_its_most(self):
        await self.select_field(labels_text.MSG_ACCENT_LABEL)
        await self.press(*[keybindings.SwellEditor.MORE] * (limits.MAX_ACCENT + 1))
        self.assertEqual(self.shape().accent, limits.MAX_ACCENT)


class TestArticulateEditor(ShapeEditorTest):
    """An Articulate's editor: start stops at its least."""

    SECTION = Section.ARTICULATES
    PAGE = ArticulateEditor
    KIND = GeneratorKind.ARTICULATE
    NAME = ui_testing.CLIPPED

    async def test_start_stops_at_its_least(self):
        await self.select_field(labels_text.MSG_SHAPE_PART_LABELS[ShapePart.START])
        await self.press(*[keybindings.ArticulateEditor.LESS] * CLIPPED_START)
        self.assertEqual(self.shape().start, limits.MIN_ARTICULATE)


def heading_text(*, shape, is_open):
    return labels_text.MSG_SECTION_LABEL.format(mark=marks.MSG_SECTION_OPEN_MARK if is_open else marks.MSG_SECTION_CLOSED_MARK, name=labels_text.MSG_SHAPE_NAMES[shape])


class TestShapeSectionsOnTheScenePage(UITest):
    """On the Scene page, each shape is a section, closed until Space or Enter opens it, saying (set) when anything inside holds a value."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.app.screen.show_page(ScenePage(holder=self.app.screen.holder, index=0))
        await self.pilot.pause()
        self.page = self.app.screen

    def labels(self):
        return [field.label for field in self.page.shown_fields()]

    async def test_a_section_opens_and_closes_and_its_fields_show_only_while_open(self):
        start = labels_text.MSG_SHAPE_FIELD_LABELS[ShapePart.START].format(shape=labels_text.MSG_SHAPE_NAMES[Shape.ARTICULATE])
        self.assertIn(heading_text(shape=Shape.ARTICULATE, is_open=False), self.text())
        # How loud a scene plays is its velocity and velocity ramps, so the Scene page has no Swell section.
        self.assertNotIn(labels_text.MSG_SHAPE_NAMES[Shape.SWELL], self.labels())
        self.assertNotIn(start, self.labels())
        await self.select_field(labels_text.MSG_SHAPE_NAMES[Shape.ARTICULATE])
        await self.press(keybindings.FieldPage.TOGGLE)
        self.assertIn(heading_text(shape=Shape.ARTICULATE, is_open=True), self.text())
        self.assertIn(start, self.labels())
        await self.select_field(start)
        await self.press(keybindings.FieldPage.LESS)
        self.assertEqual(self.document.song().get_scenes()[0].get_shape(Shape.ARTICULATE).start, FULL - 1)
        await self.select_field(labels_text.MSG_SHAPE_NAMES[Shape.ARTICULATE])
        await self.press(Key.ENTER)
        self.assertNotIn(start, self.labels())
        self.assertIn(heading_text(shape=Shape.ARTICULATE, is_open=False), self.text())
        self.assertIn(marks.MSG_SECTION_SET, self.text())

    async def test_pgdn_and_pgup_jump_between_the_headings(self):
        down = forward_key(keybindings.FieldPage.SECTION)
        up = back_key(keybindings.FieldPage.SECTION)
        await self.press(down)
        self.assertIsInstance(self.page.field(), Heading)
        self.assertEqual(self.page.field().label, labels_text.MSG_TEMPO_RAMP_SECTIONS[RampWay.IN])
        # Past the two tempo ramps and the two velocity ramps to the shapes.
        await self.press(down, down)
        self.assertEqual(self.page.field().label, labels_text.MSG_VELOCITY_RAMP_SECTIONS[RampWay.IN])
        await self.press(down, down)
        self.assertEqual(self.page.field().label, labels_text.MSG_SHAPE_NAMES[Shape.DENSITY])
        await self.press(down)
        self.assertEqual(self.page.field().label, labels_text.MSG_SHAPE_NAMES[Shape.ARTICULATE])
        await self.press(up)
        self.assertEqual(self.page.field().label, labels_text.MSG_SHAPE_NAMES[Shape.DENSITY])

    async def test_pgdn_stops_at_the_last_heading(self):
        headings = [field.label for field in self.page.fields() if isinstance(field, Heading)]
        await self.press(*[forward_key(keybindings.FieldPage.SECTION)] * (len(headings) + 1))
        self.assertEqual(self.page.field().label, headings[-1])

    async def test_an_open_section_stays_open_on_the_next_scene_page(self):
        await self.select_field(labels_text.MSG_SHAPE_NAMES[Shape.DENSITY])
        await self.press(Key.ENTER, Key.ESCAPE)
        self.app.screen.show_page(ScenePage(holder=self.app.screen.holder, index=0))
        await self.pilot.pause()
        self.assertIn(heading_text(shape=Shape.DENSITY, is_open=True), self.text())


class TestShapeSectionsOnTheClipPage(UITest):
    """On the clip page the same sections set the clip's own, over its scene's."""

    async def test_a_clips_density_is_its_own(self):
        self.app.screen.show_page(ClipPage(holder=self.app.screen.holder, index=0, track=ui_testing.LEAD))
        await self.pilot.pause()
        await self.select_field(labels_text.MSG_SHAPE_NAMES[Shape.DENSITY])
        await self.press(Key.ENTER)
        await self.select_field(labels_text.MSG_SHAPE_FIELD_LABELS[ShapePart.END].format(shape=labels_text.MSG_SHAPE_NAMES[Shape.DENSITY]))
        await self.press(Key.ENTER)
        self.app.screen.value = str(HALF)
        await self.press(Key.ENTER)
        clip_slot = self.document.song().get_scenes()[0].get_clip_slot(ui_testing.LEAD)
        self.assertEqual(clip_slot.get_written(shape_setting(shape=Shape.DENSITY, part=ShapePart.END)), HALF)
        self.assertIsNone(self.document.song().get_scenes()[0].get_shape(Shape.DENSITY))
