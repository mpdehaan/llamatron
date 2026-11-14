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
"""The drawing components the pages share: the Canvas lines are laid out on, the length bars and the frame."""

import unittest

from llamatron.tui.components.frame import Frame
from llamatron.tui.components.length_bar import FULL_BLOCK, HATCHING, LengthBar, PARTIAL_BLOCKS
from llamatron.tui.drawing import Box, Canvas, SPACE, Style
from llamatron.support.rational import Rational


WIDTH = 8
HALF_BAR = '▌'
THREE_EIGHTHS = '▍'
HELLO = 'hello'
WORLD = 'world'


class TestCanvas(unittest.TestCase):

    def test_starts_blank_and_takes_text_where_it_is_written(self):
        canvas = Canvas(WIDTH)
        self.assertEqual(canvas.text().plain, SPACE * WIDTH)
        canvas.write(column=1, text=HELLO)
        self.assertEqual(canvas.text().plain, SPACE + HELLO + SPACE * 2)

    def test_later_writes_cover_earlier_ones_and_the_edges_cut(self):
        canvas = Canvas(WIDTH)
        canvas.write(column=0, text=HELLO)
        canvas.write(column=3, text=WORLD)
        self.assertEqual(canvas.text().plain, 'helworld')
        canvas.write(column=-2, text=WORLD)
        self.assertEqual(canvas.text().plain, 'rldworld')
        canvas.write(column=WIDTH + 1, text=WORLD)
        self.assertEqual(canvas.text().plain, 'rldworld')

    def test_each_run_of_one_style_is_one_span(self):
        canvas = Canvas(WIDTH)
        canvas.write(column=0, text=HELLO, style=Style.BOLD)
        canvas.write(column=5, text=SPACE * 3, style=Style.DIM)
        text = canvas.text()
        self.assertEqual([(span.start, span.end, span.style) for span in text.spans], [(0, 5, Style.BOLD), (5, 8, Style.DIM)])


class TestLengthBar(unittest.TestCase):

    def test_a_whole_fills_the_width_and_nothing_leaves_it_hatched(self):
        bar = LengthBar(width=WIDTH, hatched=True)
        self.assertEqual(bar.draw(amount=3, total=3), FULL_BLOCK * WIDTH)
        self.assertEqual(bar.draw(amount=0, total=3), HATCHING * WIDTH)
        self.assertEqual(bar.full(), FULL_BLOCK * WIDTH)

    def test_parts_of_a_cell_are_drawn_in_eighths(self):
        bar = LengthBar(width=WIDTH, hatched=False)
        self.assertEqual(bar.draw(amount=Rational(1, 2), total=1), FULL_BLOCK * 4 + SPACE * 4)
        self.assertEqual(bar.draw(amount=Rational(9, 16), total=1), FULL_BLOCK * 4 + HALF_BAR + SPACE * 3)
        self.assertEqual(bar.draw(amount=Rational(3, 64), total=1), THREE_EIGHTHS + SPACE * 7)
        self.assertEqual(len(PARTIAL_BLOCKS), 7)

    def test_more_than_the_total_fills_and_unknowns_draw_nothing(self):
        bar = LengthBar(width=WIDTH, hatched=True)
        self.assertEqual(bar.draw(amount=5, total=3), FULL_BLOCK * WIDTH)
        self.assertEqual(bar.draw(amount=None, total=3), SPACE * WIDTH)
        self.assertEqual(bar.draw(amount=3, total=None), SPACE * WIDTH)
        self.assertEqual(bar.draw(amount=3, total=0), SPACE * WIDTH)
        self.assertEqual(bar.blank(), SPACE * WIDTH)
        self.assertEqual(bar.width(), WIDTH)


class TestFrame(unittest.TestCase):

    def test_the_edges_go_between_the_columns_in_bold(self):
        frame = Frame(left=1, right=5)
        top, middle, bottom = Canvas(WIDTH), Canvas(WIDTH), Canvas(WIDTH)
        frame.top(top)
        frame.sides(middle)
        frame.bottom(bottom)
        self.assertEqual(top.text().plain, SPACE + Box.DOUBLE_TOP_LEFT + Box.DOUBLE_RULE * 3 + Box.DOUBLE_TOP_RIGHT + SPACE * 2)
        self.assertEqual(middle.text().plain, SPACE + Box.DOUBLE_BAR + SPACE * 3 + Box.DOUBLE_BAR + SPACE * 2)
        self.assertEqual(bottom.text().plain, SPACE + Box.DOUBLE_BOTTOM_LEFT + Box.DOUBLE_RULE * 3 + Box.DOUBLE_BOTTOM_RIGHT + SPACE * 2)
        self.assertEqual(frame.inner_width(), 3)
        self.assertEqual([span.style for span in top.text().spans if span.style], [Style.BOLD])


if __name__ == '__main__':
    unittest.main()
