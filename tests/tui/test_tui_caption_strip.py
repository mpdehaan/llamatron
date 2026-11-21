# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests of the caption strip, the video tutorial's captions at the foot of the screen, and of the SubRip file made from them."""

import unittest

from llamatron.tui import caption_strip
from llamatron.tui.caption_strip import CaptionStrip, parts
from llamatron.tutorial.subtitles import subtitle_time, subtitles
from tests.support.ui_testing import UITest

SENTENCE = 'First we open a demo that ships with llamatron, which runs here from a git checkout.'
NARROW = 40
WIDE = 120
HALF_A_SECOND = 0.5
LONG_AGO = 3723.25
OFFSET = 6


class TestCaptionStrip(unittest.TestCase):

    def test_two_lines_the_caption_centred_in_bold_black_on_white_then_a_white_line(self):
        strip = CaptionStrip()
        strip.show(SENTENCE)
        first, second = strip.lines(WIDE)
        self.assertEqual(len(first.plain), WIDE)
        self.assertEqual(first.plain.strip(), SENTENCE)
        self.assertEqual(first.plain.index(SENTENCE), (WIDE - len(SENTENCE)) // 2)
        self.assertEqual(first.style, caption_strip.CAPTION_STYLE)
        self.assertEqual(second.plain.strip(), '')
        self.assertEqual(second.style, caption_strip.CAPTION_STYLE)

    def test_a_long_sentence_is_shown_a_part_at_a_time_broken_between_words(self):
        shown = parts(text=SENTENCE, width=NARROW)
        self.assertGreater(len(shown), 1)
        self.assertEqual(' '.join(shown), SENTENCE)
        self.assertTrue(all(len(part) <= NARROW for part in shown))

    def test_subrip_times_and_cues(self):
        self.assertEqual(subtitle_time(LONG_AGO), '01:02:03,250')
        text = subtitles(said=[(0, SENTENCE), (HALF_A_SECOND, 'Next')], ended=1, offset=OFFSET)
        self.assertEqual(text.splitlines()[:4], ['1', '00:00:06,000 --> 00:00:06,500', SENTENCE, ''])
        self.assertIn('00:00:06,500 --> 00:00:07,000', text)


class TestCaptionStripOnAPage(UITest):

    async def test_the_page_moves_up_to_make_room_and_keeps_its_legend(self):
        before = self.text().splitlines()
        strip = CaptionStrip()
        strip.show(SENTENCE)
        self.app.show_caption_strip(strip)
        await self.settle()
        after = self.text().splitlines()
        self.assertEqual(len(after), len(before))
        self.assertIn(SENTENCE, after[-caption_strip.CAPTION_LINES])
        self.assertEqual(after[-caption_strip.CAPTION_LINES - 1], before[-1])
