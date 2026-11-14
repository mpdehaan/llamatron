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

"""Tests internal_tools/window_region.py, which finds the rectangle a terminal window's cells cover, on stills made in memory: the BMP reading, rows stored either way and channels by masks or by default, the cells found inside a title bar, margins and rounded corners, and the screen's points."""

import os
import struct
import sys
import tempfile
import unittest

import numpy

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'internal_tools'))

import window_region  # noqa: E402
from window_region import CALIBRATION_COLOUR, SAFETY_PIXELS, cell_area, read_bmp, screen_region  # noqa: E402

TITLE_BAR = (60, 60, 64)
MARGIN = (20, 20, 20)
WIDTH = 60
HEIGHT = 40
TITLE_ROWS = 8
MARGIN_PIXELS = 3
CORNER_ROWS = 2
SCALE = 2
WINDOW_LEFT = 100
WINDOW_TOP = 50
OPAQUE = 255
BMP_NAME = 'still.bmp'
WRITE_BYTES = 'wb'
NOT_A_PICTURE = b'not a picture'
# A BMP file's header as screencapture writes it: the file header, then a version 5 header of 124 bytes.
FILE_HEADER = '<2sIHHI'
FILE_HEADER_BYTES = 14
INFO_HEADER = '<IiiHHIIiiII'
V5_HEADER_BYTES = 124
PLANES = 1
PIXELS_PER_METRE = 2835
ALPHA_MASK = 0xFF000000
# A pixel stored with its bytes in this order, which the masks below say: blue, green, red, alpha.
STORED_ORDER = [2, 1, 0, 3]
SHUFFLED_MASKS = (0x000000FF, 0x0000FF00, 0x00FF0000)
SHUFFLED_ORDER = [0, 1, 2, 3]


def still():
    """Return a still like screencapture's: a title bar, a margin, the cells in the calibration colour, and the bottom corners rounded away."""
    pixels = numpy.zeros((HEIGHT, WIDTH, 4), dtype=numpy.uint8)
    pixels[:, :, 3] = OPAQUE
    pixels[:, :, :3] = MARGIN
    pixels[:TITLE_ROWS, :, :3] = TITLE_BAR
    pixels[TITLE_ROWS + MARGIN_PIXELS:HEIGHT - MARGIN_PIXELS, MARGIN_PIXELS:WIDTH - MARGIN_PIXELS, :3] = CALIBRATION_COLOUR
    for row in range(HEIGHT - CORNER_ROWS, HEIGHT):
        pixels[row, :MARGIN_PIXELS + CORNER_ROWS, 3] = 0
        pixels[row, WIDTH - MARGIN_PIXELS - CORNER_ROWS:, 3] = 0
    pixels[HEIGHT - MARGIN_PIXELS - 1, MARGIN_PIXELS, 3] = 0
    return pixels


def bmp_bytes(*, pixels, top_down=True, masks=window_region.RGB_MASKS, order=None, bitfields=True):
    """Return a 32-bit BMP file of RGBA pixels as screencapture writes one: a version 5 header, the channels' masks, and the rows top down or bottom up."""
    height, width = pixels.shape[:2]
    stored = pixels[:, :, STORED_ORDER if order is None else order]
    rows = stored if top_down else stored[::-1]
    body = rows.tobytes()
    compression = window_region.BI_BITFIELDS if bitfields else window_region.BI_RGB
    info = struct.pack(INFO_HEADER, V5_HEADER_BYTES, width, -height if top_down else height, PLANES, window_region.THIRTY_TWO_BITS,
                       compression, len(body), PIXELS_PER_METRE, PIXELS_PER_METRE, 0, 0)
    info += struct.pack(window_region.MASKS_LAYOUT, *masks) + struct.pack(window_region.PIXELS_AT, ALPHA_MASK)
    info = info.ljust(V5_HEADER_BYTES, bytes(1))
    offset = FILE_HEADER_BYTES + len(info)
    return struct.pack(FILE_HEADER, window_region.BMP_SIGNATURE, offset + len(body), 0, 0, offset) + info + body


def read_back(data):
    """Write a BMP file's bytes and read them back as pixels."""
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, BMP_NAME)
        with open(path, WRITE_BYTES) as file:
            file.write(data)
        return read_bmp(path)


def coloured_still():
    """Return the still with a red that changes along each row, so that a row or a channel out of place shows."""
    pixels = still()
    pixels[:, :, 0] = numpy.arange(WIDTH, dtype=numpy.uint8)[None, :] * 3
    return pixels


class TestReadBmp(unittest.TestCase):

    def test_rows_stored_top_down_or_bottom_up_read_back_the_pixels_written(self):
        pixels = coloured_still()
        self.assertTrue((read_back(bmp_bytes(pixels=pixels)) == pixels).all())
        self.assertTrue((read_back(bmp_bytes(pixels=pixels, top_down=False)) == pixels).all())

    def test_the_masks_say_where_each_channel_is(self):
        pixels = coloured_still()
        self.assertTrue((read_back(bmp_bytes(pixels=pixels, masks=SHUFFLED_MASKS, order=SHUFFLED_ORDER)) == pixels).all())

    def test_a_file_with_no_masks_takes_the_usual_order_and_is_opaque(self):
        pixels = coloured_still()
        read = read_back(bmp_bytes(pixels=pixels, bitfields=False))
        self.assertTrue((read[:, :, :3] == pixels[:, :, :3]).all())
        self.assertTrue((read[:, :, 3] == window_region.FULL).all())

    def test_a_file_that_is_not_a_bmp_is_refused(self):
        with self.assertRaises(ValueError):
            read_back(NOT_A_PICTURE)


class TestCellArea(unittest.TestCase):

    def test_the_cells_leave_out_the_title_bar_the_margins_and_the_rounded_corners(self):
        top, bottom, left, right = cell_area(still())
        self.assertEqual(top, TITLE_ROWS + MARGIN_PIXELS + SAFETY_PIXELS)
        self.assertEqual(left, MARGIN_PIXELS + SAFETY_PIXELS)
        self.assertEqual(right, WIDTH - MARGIN_PIXELS - 1 - SAFETY_PIXELS)
        self.assertLess(bottom, HEIGHT - MARGIN_PIXELS - 1 - SAFETY_PIXELS)

    def test_a_still_with_no_cells_finds_nothing(self):
        pixels = numpy.zeros((HEIGHT, WIDTH, 4), dtype=numpy.uint8)
        self.assertIsNone(cell_area(pixels))


class TestScreenRegion(unittest.TestCase):

    def test_pixels_become_whole_points_kept_inside_from_the_windows_place(self):
        area = (TITLE_ROWS * SCALE + 1, 59, 3, 101)
        region = screen_region(area=area, still_width=WIDTH * SCALE, bounds=(WINDOW_LEFT, WINDOW_TOP, WIDTH, HEIGHT))
        self.assertEqual((region.left, region.top), (WINDOW_LEFT + 2, WINDOW_TOP + TITLE_ROWS + 1))
        self.assertEqual(region.width, 51 - 2)
        self.assertEqual(region.height, 30 - TITLE_ROWS - 1)
        self.assertEqual(region.argument(), window_region.COMMA.join(str(number) for number in (region.left, region.top, region.width, region.height)))


if __name__ == '__main__':
    unittest.main()
