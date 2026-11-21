# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The tracker's Strum: the Strums page and editor, and the + Strum sections of the track editor and the clip page."""

from llamatron.composition.file_format import GeneratorKind, Section, StrumDirection, StrumPart, StrumSpread
from llamatron.tui import keybindings
from llamatron.tui.keys import Key
from llamatron.tui.screens.arrange.clip_page import ClipPage
from llamatron.tui.screens.arrange.track_editor import TrackEditor
from llamatron.tui.screens.generators.strum_editor import StrumEditor
from llamatron.tui.screens.generators.strum_fields import spread_name
from llamatron.user_strings import labels, marks
from tests.support import ui_testing
from tests.support.ui_testing import UITest

NEW_ONE = 'ukulele'


class TestStrumAdded(UITest):

    async def test_a_new_one_strums_by_the_beat(self):
        name = await self.add_generator(Section.STRUMS)
        self.assertIsInstance(self.app.screen, StrumEditor)
        strum = self.document.song().get_generator_settings(kind=GeneratorKind.STRUM, name=name)
        self.assertEqual(strum.get_strum().direction, StrumDirection.BY_THE_BEAT)


class TestStrumEditor(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_generator(section=Section.STRUMS)
        self.assertIsInstance(self.app.screen, StrumEditor)

    def strum(self):
        return self.document.song().get_generator_settings(kind=GeneratorKind.STRUM, name=ui_testing.FOLK)

    async def test_the_spread_steps_through_its_choices_and_shows_milliseconds(self):
        self.assertIn(spread_name(StrumSpread.NORMAL), self.text())
        await self.select_field(labels.MSG_STRUM_PART_LABELS[StrumPart.SPREAD])
        await self.press(keybindings.StrumEditor.MORE)
        self.assertEqual(self.strum().get_strum_setting(StrumPart.SPREAD), StrumSpread.LOOSE)

    async def test_fade_steps_up_and_bksp_clears_it(self):
        await self.select_field(labels.MSG_STRUM_PART_LABELS[StrumPart.FADE])
        await self.press(keybindings.StrumEditor.MORE)
        self.assertEqual(self.strum().get_strum().fade, 1)
        await self.press(Key.BACKSPACE)
        self.assertEqual(self.strum().get_strum().fade, 0)


class TestStrumSections(UITest):
    """The track editor's + Strum section, and the clip page's, whose (track) takes the track's."""

    async def test_the_track_strums_and_the_clip_takes_it_until_set(self):
        self.app.screen.show_page(TrackEditor(holder=self.app.screen.holder, name=ui_testing.LEAD))
        await self.pilot.pause()
        await self.select_field(labels.MSG_STRUM_LABEL)
        await self.press(Key.ENTER)
        await self.select_field(labels.MSG_STRUM_FIELD_LABELS[StrumPart.DIRECTION])
        await self.press(keybindings.FieldPage.MORE)
        self.assertEqual(self.document.song().get_track(ui_testing.LEAD).get_strum().direction, StrumDirection.BY_THE_BEAT)
        self.app.screen.show_page(ClipPage(holder=self.app.screen.holder, index=0, track=ui_testing.LEAD))
        await self.pilot.pause()
        # The clip shows the track's direction it takes, and where it comes from.
        self.assertIn(marks.MSG_FROM_TRACK_SHOWN.format(value=labels.MSG_STRUM_WORDS[StrumDirection.BY_THE_BEAT]), self.text())
        await self.select_field(labels.MSG_STRUM_FIELD_LABELS[StrumPart.DIRECTION])
        await self.press(*[keybindings.FieldPage.MORE] * 2)
        self.assertEqual(self.document.song().get_scenes()[0].get_clip_slot(ui_testing.LEAD).get_strum().direction, StrumDirection.DOWN)
