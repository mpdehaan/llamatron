# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Velocity field and the velocity ramp sections on the Scene page and the clip page, and their line in Arrange's details view."""

from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.screens.arrange.arrange_details import clip_details, scene_details
from llamatron.interface.tracker.screens.arrange.clip_page import ClipPage
from llamatron.interface.tracker.screens.arrange.scene_page import ScenePage
from llamatron.model.objects import velocity_ramps
from llamatron.model.schema import limits
from llamatron.model.schema.file_format import RampPart, RampWay, VelocitySetting
from llamatron.user_strings import labels as labels_text, marks
from tests.support import ui_testing
from tests.support.ui_testing import UITest

FIRST_SCENE = 0
SCENE_LEVEL = 80
CLIP_LEVEL = 60
RAMP_START = 20
RAMP_BARS = 4
IN_START = labels_text.MSG_VELOCITY_RAMP_LABELS[(RampWay.IN, RampPart.START)]
IN_OVER = labels_text.MSG_VELOCITY_RAMP_LABELS[(RampWay.IN, RampPart.OVER)]
OUT_END = labels_text.MSG_VELOCITY_RAMP_LABELS[(RampWay.OUT, RampPart.END)]


def percent(value):
    return marks.MSG_VELOCITY_PERCENT_SHOWN.format(percent=value)


class VelocityTest(UITest):
    """A page with the velocity fields, shown over the main screen."""

    def scene(self):
        return self.document.song().get_scenes()[FIRST_SCENE]

    def clip_slot(self):
        return self.scene().get_clip_slot(ui_testing.LEAD)

    async def show(self, page):
        self.app.screen.show_page(page)
        await self.pilot.pause()
        self.page = self.app.screen

    def shown(self, label):
        """Return what a field of the page shows as its value."""
        return next(field for field in self.page.fields() if field.label == label).value()

    async def open_section(self, way):
        await self.select_field(labels_text.MSG_VELOCITY_RAMP_SECTIONS[way])
        await self.press(keybindings.FieldPage.TOGGLE)


class TestVelocityOnTheScenePage(VelocityTest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.show(ScenePage(holder=self.app.screen.holder, index=FIRST_SCENE))

    async def test_a_blank_velocity_shows_the_notes_as_written_and_steps_from_there(self):
        self.assertEqual(self.shown(labels_text.MSG_VELOCITY_PERCENT_LABEL), percent(velocity_ramps.AS_WRITTEN))
        await self.select_field(labels_text.MSG_VELOCITY_PERCENT_LABEL)
        await self.press(keybindings.FieldPage.LESS)
        self.assertEqual(self.scene().get_velocity().level, velocity_ramps.AS_WRITTEN - 1)
        self.assertEqual(self.shown(labels_text.MSG_VELOCITY_PERCENT_LABEL), percent(velocity_ramps.AS_WRITTEN - 1))
        await self.press(keybindings.FieldPage.CLEAR)
        self.assertIsNone(self.scene().get_velocity_settings()[VelocitySetting.LEVEL])

    async def test_the_velocity_stops_at_its_limits(self):
        self.document.change_set(self.document.song().get_scene(FIRST_SCENE).set_written, name=VelocitySetting.LEVEL, value=limits.MAX_VELOCITY_PERCENT)
        await self.show(ScenePage(holder=self.app.screen.holder, index=FIRST_SCENE))
        await self.select_field(labels_text.MSG_VELOCITY_PERCENT_LABEL)
        await self.press(keybindings.FieldPage.MORE)
        self.assertEqual(self.scene().get_velocity().level, limits.MAX_VELOCITY_PERCENT)

    async def test_a_ramps_fields_show_only_while_its_section_is_open_and_a_blank_end_shows_the_velocity(self):
        labels = [field.label for field in self.page.shown_fields()]
        self.assertNotIn(IN_START, labels)
        self.document.change_set(self.document.song().get_scene(FIRST_SCENE).set_written, name=VelocitySetting.LEVEL, value=SCENE_LEVEL)
        await self.open_section(RampWay.IN)
        self.assertIn(IN_START, [field.label for field in self.page.shown_fields()])
        self.assertEqual(self.shown(IN_START), marks.MSG_FROM_VELOCITY_SHOWN.format(value=percent(SCENE_LEVEL)))
        self.assertEqual(self.shown(IN_OVER), marks.MSG_NONE_SHOWN)

    async def test_a_ramp_is_made_by_stepping_its_start_and_its_bars_and_the_heading_says_it_is_set(self):
        await self.open_section(RampWay.IN)
        await self.select_field(IN_START)
        await self.press(keybindings.FieldPage.LESS)
        await self.select_field(IN_OVER)
        await self.press(keybindings.FieldPage.MORE)
        ramp = self.scene().get_velocity().ramp_in
        self.assertEqual((ramp.start, ramp.end, ramp.over), (velocity_ramps.AS_WRITTEN - 1, velocity_ramps.AS_WRITTEN, limits.MIN_RAMP_BARS + 1))
        self.assertEqual(self.shown(IN_OVER), marks.MSG_RAMP_BARS_SHOWN.format(bars=limits.MIN_RAMP_BARS + 1))
        await self.open_section(RampWay.IN)
        self.assertIn(marks.MSG_SECTION_SET, self.text())

    async def test_the_ramp_out_is_a_section_of_its_own(self):
        await self.open_section(RampWay.OUT)
        await self.select_field(OUT_END)
        await self.press(keybindings.FieldPage.LESS)
        self.assertEqual(self.scene().get_velocity_settings()[VelocitySetting.OUT_END], velocity_ramps.AS_WRITTEN - 1)
        self.assertIsNone(self.scene().get_velocity().ramp_out)

    async def test_an_edit_is_undone_and_redone(self):
        await self.select_field(labels_text.MSG_VELOCITY_PERCENT_LABEL)
        await self.press(keybindings.FieldPage.LESS)
        await self.press(keybindings.Page.UNDO)
        self.assertIsNone(self.scene().get_velocity_settings()[VelocitySetting.LEVEL])
        await self.press(keybindings.Page.REDO)
        self.assertEqual(self.scene().get_velocity().level, velocity_ramps.AS_WRITTEN - 1)


class TestVelocityOnTheClipPage(VelocityTest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.document.change_set(self.document.song().get_scene(FIRST_SCENE).set_written, name=VelocitySetting.LEVEL, value=SCENE_LEVEL)
        self.document.change_set(self.document.song().get_scene(FIRST_SCENE).set_written, name=VelocitySetting.IN_START, value=RAMP_START)
        self.document.change_set(self.document.song().get_scene(FIRST_SCENE).set_written, name=VelocitySetting.IN_OVER, value=RAMP_BARS)
        await self.show(ClipPage(holder=self.app.screen.holder, index=FIRST_SCENE, track=ui_testing.LEAD))

    async def test_a_blank_field_shows_its_scenes_value_and_says_so(self):
        self.assertEqual(self.shown(labels_text.MSG_VELOCITY_PERCENT_LABEL), marks.MSG_FROM_SCENE_SHOWN.format(value=percent(SCENE_LEVEL)))
        await self.open_section(RampWay.IN)
        self.assertEqual(self.shown(IN_START), marks.MSG_FROM_SCENE_SHOWN.format(value=percent(RAMP_START)))
        self.assertEqual(self.shown(IN_OVER), marks.MSG_FROM_SCENE_SHOWN.format(value=marks.MSG_RAMP_BARS_SHOWN.format(bars=RAMP_BARS)))

    async def test_a_step_starts_from_the_scenes_value_and_the_clips_own_then_wins(self):
        await self.select_field(labels_text.MSG_VELOCITY_PERCENT_LABEL)
        await self.press(keybindings.FieldPage.LESS)
        self.assertEqual(self.clip_slot().get_velocity_settings()[VelocitySetting.LEVEL], SCENE_LEVEL - 1)
        self.assertEqual(self.clip_slot().get_velocity(self.scene()).level, SCENE_LEVEL - 1)
        self.assertEqual(self.scene().get_velocity().level, SCENE_LEVEL)
        await self.press(keybindings.FieldPage.CLEAR)
        self.assertEqual(self.clip_slot().get_velocity(self.scene()).level, SCENE_LEVEL)

    async def test_a_clips_own_bars_make_the_ramp_the_clips(self):
        await self.open_section(RampWay.IN)
        await self.select_field(IN_OVER)
        await self.press(keybindings.FieldPage.MORE)
        ramp = self.clip_slot().get_velocity(self.scene()).ramp_in
        self.assertEqual((ramp.start, ramp.over, ramp.of_clip), (RAMP_START, RAMP_BARS + 1, True))


class TestVelocityInTheDetailsView(VelocityTest):

    def lines(self, details):
        """Return the lines of a cell's details that say something of its own, leaving out the rows that add one."""
        return [line.text.strip() for line in details if line.target is None]

    async def test_a_scene_and_a_clip_show_their_own_velocity_and_a_mark_where_a_ramp_moves_it(self):
        setlist = self.document.get_setlist()
        song = self.document.song()
        self.assertEqual(self.lines(scene_details(song=song, scene=self.scene())), [])
        self.document.change_set(self.document.song().get_scene(FIRST_SCENE).set_written, name=VelocitySetting.LEVEL, value=SCENE_LEVEL)
        self.assertEqual(self.lines(scene_details(song=song, scene=self.scene())), [marks.MSG_DETAILS_VELOCITY.format(percent=SCENE_LEVEL)])
        self.assertEqual(self.lines(clip_details(setlist=setlist, song=song, clip_slot=self.clip_slot())), [])
        self.document.change_set(self.document.clip_slot(index=FIRST_SCENE, track=ui_testing.LEAD).set_written, name=VelocitySetting.LEVEL, value=CLIP_LEVEL)
        self.document.change_set(self.document.clip_slot(index=FIRST_SCENE, track=ui_testing.LEAD).set_written, name=VelocitySetting.OUT_END, value=RAMP_START)
        self.assertEqual(self.lines(clip_details(setlist=setlist, song=song, clip_slot=self.clip_slot())), [marks.MSG_DETAILS_VELOCITY_RAMPS.format(percent=CLIP_LEVEL)])
