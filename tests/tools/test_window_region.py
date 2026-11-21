# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""internal_tools/window_region.py, one quick check of its main path: the cells leave out the title bar the margins and the rounded corners. A tool fails loudly when it is run, so one check is enough (.claude/TESTING.md)."""

import numpy
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'internal_tools'))

import window_region  # noqa: E402
from window_region import cell_area  # noqa: E402

TITLE_BAR = (60, 60, 64)
MARGIN = (20, 20, 20)
WIDTH = 60
HEIGHT = 40
TITLE_ROWS = 8
MARGIN_PIXELS = 3
CORNER_ROWS = 2
OPAQUE = 255


def still():
    """Return a still like screencapture's: a title bar, a margin, the cells in the calibration colour, and the bottom corners rounded away."""
    pixels = numpy.zeros((HEIGHT, WIDTH, 4), dtype=numpy.uint8)
    pixels[:, :, 3] = OPAQUE
    pixels[:, :, :3] = MARGIN
    pixels[:TITLE_ROWS, :, :3] = TITLE_BAR
    pixels[TITLE_ROWS + MARGIN_PIXELS:HEIGHT - MARGIN_PIXELS, MARGIN_PIXELS:WIDTH - MARGIN_PIXELS, :3] = window_region.CALIBRATION_COLOUR
    for row in range(HEIGHT - CORNER_ROWS, HEIGHT):
        pixels[row, :MARGIN_PIXELS + CORNER_ROWS, 3] = 0
        pixels[row, WIDTH - MARGIN_PIXELS - CORNER_ROWS:, 3] = 0
    pixels[HEIGHT - MARGIN_PIXELS - 1, MARGIN_PIXELS, 3] = 0
    return pixels


class TestCellArea(unittest.TestCase):

    def test_the_cells_leave_out_the_title_bar_the_margins_and_the_rounded_corners(self):
        top, bottom, left, right = cell_area(still())
        self.assertEqual(top, TITLE_ROWS + MARGIN_PIXELS + window_region.SAFETY_PIXELS)
        self.assertEqual(left, MARGIN_PIXELS + window_region.SAFETY_PIXELS)
        self.assertEqual(right, WIDTH - MARGIN_PIXELS - 1 - window_region.SAFETY_PIXELS)
        self.assertLess(bottom, HEIGHT - MARGIN_PIXELS - 1 - window_region.SAFETY_PIXELS)

if __name__ == '__main__':
    unittest.main()
