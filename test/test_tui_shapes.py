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
"""The tracker's Density, Swell and Articulate: their list pages and editors, the sections on the Scene page and the clip page, and the settings pages' sections that hold them."""

from ui_testing import CLIPPED, FADE, LEAD, THIN, UITest, back_key, forward_key
from llamatron.composition.file_format import Section, GeneratorKind, SHAPE_THENS, Shape, ShapePart, shape_setting
from llamatron.composition.limits import MAX_ACCENT, MIN_ARTICULATE
from llamatron.strings.labels import MSG_ACCENT_LABEL, MSG_SHAPE_FIELD_LABELS, MSG_SHAPE_NAMES, MSG_SHAPE_PART_LABELS, MSG_SECTION_LABEL
from llamatron.strings.marks import MSG_SECTION_CLOSED_MARK, MSG_SECTION_OPEN_MARK, MSG_SECTION_SET
from llamatron.tui.keys import Key
from llamatron.tui.screens.articulate_editor import ArticulateEditor
from llamatron.tui.screens.clip_page import ClipPage
from llamatron.tui.screens.density_editor import DensityEditor
from llamatron.tui.screens.field import Heading
from llamatron.tui.screens.scene_page import ScenePage
from llamatron.tui.screens.swell_editor import SwellEditor
from llamatron.tui import keybindings

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
    NAME = THIN

    async def test_start_steps_and_clears(self):
        await self.select_field(MSG_SHAPE_PART_LABELS[ShapePart.START])
        await self.press(keybindings.DensityEditor.MORE)
        self.assertEqual(self.shape().start, THIN_START + 1)
        await self.press(Key.BACKSPACE)
        self.assertEqual(self.shape().start, FULL)

    async def test_end_stops_at_the_top(self):
        await self.select_field(MSG_SHAPE_PART_LABELS[ShapePart.END])
        await self.press(keybindings.DensityEditor.MORE)
        self.assertEqual(self.shape().end, FULL)

    async def test_then_steps_through_hold_repeat_and_bounce(self):
        self.assertEqual(self.shape().then, SHAPE_THENS[0])
        await self.select_field(MSG_SHAPE_PART_LABELS[ShapePart.THEN])
        await self.press(keybindings.DensityEditor.MORE)
        self.assertEqual(self.shape().then, SHAPE_THENS[1])

    async def test_over_steps_from_the_whole_clip_to_a_length(self):
        self.assertIsNone(self.shape().over)
        await self.select_field(MSG_SHAPE_PART_LABELS[ShapePart.OVER])
        await self.press(keybindings.DensityEditor.MORE)
        self.assertIsNotNone(self.shape().over)

    async def test_it_has_no_accent(self):
        self.assertNotIn(MSG_ACCENT_LABEL, [field.label for field in self.app.screen.fields()])


class TestSwellEditor(ShapeEditorTest):
    """A Swell's editor has an accent besides, up to its most."""

    SECTION = Section.SWELLS
    PAGE = SwellEditor
    KIND = GeneratorKind.SWELL
    NAME = FADE

    async def test_the_accent_steps_up_to_its_most(self):
        await self.select_field(MSG_ACCENT_LABEL)
        await self.press(*[keybindings.SwellEditor.MORE] * (MAX_ACCENT + 1))
        self.assertEqual(self.shape().accent, MAX_ACCENT)


class TestArticulateEditor(ShapeEditorTest):
    """An Articulate's editor: start stops at its least."""

    SECTION = Section.ARTICULATES
    PAGE = ArticulateEditor
    KIND = GeneratorKind.ARTICULATE
    NAME = CLIPPED

    async def test_start_stops_at_its_least(self):
        await self.select_field(MSG_SHAPE_PART_LABELS[ShapePart.START])
        await self.press(*[keybindings.ArticulateEditor.LESS] * CLIPPED_START)
        self.assertEqual(self.shape().start, MIN_ARTICULATE)


def heading_text(*, shape, is_open):
    return MSG_SECTION_LABEL.format(mark=MSG_SECTION_OPEN_MARK if is_open else MSG_SECTION_CLOSED_MARK, name=MSG_SHAPE_NAMES[shape])


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
        start = MSG_SHAPE_FIELD_LABELS[ShapePart.START].format(shape=MSG_SHAPE_NAMES[Shape.SWELL])
        self.assertIn(heading_text(shape=Shape.SWELL, is_open=False), self.text())
        self.assertNotIn(start, self.labels())
        await self.select_field(MSG_SHAPE_NAMES[Shape.SWELL])
        await self.press(keybindings.FieldPage.TOGGLE)
        self.assertIn(heading_text(shape=Shape.SWELL, is_open=True), self.text())
        self.assertIn(start, self.labels())
        await self.select_field(start)
        await self.press(keybindings.FieldPage.LESS)
        self.assertEqual(self.document.song().get_scenes()[0].get_shape(Shape.SWELL).start, FULL - 1)
        await self.select_field(MSG_SHAPE_NAMES[Shape.SWELL])
        await self.press(Key.ENTER)
        self.assertNotIn(start, self.labels())
        self.assertIn(heading_text(shape=Shape.SWELL, is_open=False), self.text())
        self.assertIn(MSG_SECTION_SET, self.text())

    async def test_pgdn_and_pgup_jump_between_the_headings(self):
        down = forward_key(keybindings.FieldPage.SECTION)
        up = back_key(keybindings.FieldPage.SECTION)
        await self.press(down)
        self.assertIsInstance(self.page.field(), Heading)
        self.assertEqual(self.page.field().label, MSG_SHAPE_NAMES[Shape.DENSITY])
        await self.press(down, down, down)
        self.assertEqual(self.page.field().label, MSG_SHAPE_NAMES[Shape.ARTICULATE])
        await self.press(up)
        self.assertEqual(self.page.field().label, MSG_SHAPE_NAMES[Shape.SWELL])

    async def test_an_open_section_stays_open_on_the_next_scene_page(self):
        await self.select_field(MSG_SHAPE_NAMES[Shape.DENSITY])
        await self.press(Key.ENTER, Key.ESCAPE)
        self.app.screen.show_page(ScenePage(holder=self.app.screen.holder, index=0))
        await self.pilot.pause()
        self.assertIn(heading_text(shape=Shape.DENSITY, is_open=True), self.text())


class TestShapeSectionsOnTheClipPage(UITest):
    """On the clip page the same sections set the clip's own, over its scene's."""

    async def test_a_clips_density_is_its_own(self):
        self.app.screen.show_page(ClipPage(holder=self.app.screen.holder, index=0, track=LEAD))
        await self.pilot.pause()
        await self.select_field(MSG_SHAPE_NAMES[Shape.DENSITY])
        await self.press(Key.ENTER)
        await self.select_field(MSG_SHAPE_FIELD_LABELS[ShapePart.END].format(shape=MSG_SHAPE_NAMES[Shape.DENSITY]))
        await self.press(Key.ENTER)
        self.app.screen.value = str(HALF)
        await self.press(Key.ENTER)
        clip_slot = self.document.song().get_scenes()[0].get_clip_slot(LEAD)
        self.assertEqual(clip_slot.get_setting(shape_setting(shape=Shape.DENSITY, part=ShapePart.END)), HALF)
        self.assertIsNone(self.document.song().get_scenes()[0].get_shape(Shape.DENSITY))
