# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The visualizer on Arrange: its key with Real Time on, its frame over the clip area with the names kept, Esc bringing the clips back, and none with Real Time off."""

import time
import unittest

from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.drawing import Style
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.arrange import arrange_drawing, arrange_page
from llamatron.interface.tracker.screens.arrange.arrange_page import ArrangePage
from llamatron.interface.visualizers import modes, pixels
from tests.support.ui_testing import UITest

SYNTH = 'synth'
WIDTH = 80
HEIGHT = 20
A_MOMENT = 1.0


class TestArrangeVisualizer(UITest):

    async def open_arrange(self, *, real_time=True):
        if real_time:
            self.document.add_instrument(SYNTH)
        await self.press(keybindings.MainPage.ARRANGE)
        self.assertIsInstance(self.app.screen, ArrangePage)
        return self.app.screen

    async def test_with_real_time_off_there_is_no_visualizer_key(self):
        page = await self.open_arrange(real_time=False)
        await self.press(keybindings.ArrangePage.VISUALIZER)
        self.assertIsNone(page.visualizer)

    async def test_the_key_shows_the_first_mode_over_the_clip_area_and_keeps_the_names(self):
        page = await self.open_arrange()
        await self.press(keybindings.ArrangePage.VISUALIZER)
        self.assertIsInstance(page.visualizer, modes.MODES[0])
        lines = page.body(width=WIDTH, height=HEIGHT)
        self.assertEqual(len(lines), HEIGHT)
        self.assertTrue(all(line.plain[arrange_drawing.CLIP_AREA_LEFT] == pixels.FULL_BLOCK for line in lines[arrange_drawing.HEADER_LINES:]))
        for track in self.document.track_names():
            self.assertIn(track, lines[1].plain)
        self.assertIn(self.document.song().get_scenes()[0].get_name(), self.text())

    async def test_the_key_after_the_last_mode_and_esc_both_bring_the_clips_back_and_stay_on_the_page(self):
        page = await self.open_arrange()
        await self.press(*[keybindings.ArrangePage.VISUALIZER] * (len(modes.MODES) + 1))
        self.assertIsNone(page.visualizer)
        await self.press(keybindings.ArrangePage.VISUALIZER, Key.ESCAPE)
        self.assertIsNone(page.visualizer)
        self.assertIs(self.app.screen, page)

    async def test_while_it_shows_only_its_own_keys_and_esc_work(self):
        page = await self.open_arrange()
        await self.press(keybindings.ArrangePage.VISUALIZER)
        bound = [binding.binding for binding in page.keys()]
        self.assertEqual(bound, [keybindings.ArrangePage.TO_CLIPS, keybindings.ArrangePage.STEP_VISUALIZER, keybindings.ArrangePage.VISUALIZER])

    async def test_a_modes_name_shows_in_reverse_video_for_a_while_when_it_changes_and_then_goes(self):
        page = await self.open_arrange()
        await self.press(keybindings.ArrangePage.VISUALIZER)
        changed = time.monotonic()
        self.assertEqual(page.name_to_show(changed), modes.MODES[0].NAME)
        self.assertEqual(page.name_to_show(changed + arrange_page.NAME_SECONDS / 2), modes.MODES[0].NAME)
        self.assertIsNone(page.name_to_show(changed + arrange_page.NAME_SECONDS + A_MOMENT))
        lines = page.drawing.with_name(lines=page.body(width=WIDTH, height=HEIGHT), name=modes.MODES[0].NAME)
        named = lines[HEIGHT - 1 - arrange_drawing.NAME_ROWS_UP]
        self.assertIn(modes.MODES[0].NAME, named.plain)
        self.assertTrue(any(span.style == Style.REVERSE for span in named.spans))


if __name__ == '__main__':
    unittest.main()
