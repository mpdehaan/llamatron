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

"""Find the rectangle of the screen that a terminal window's cells cover, with no title bar, margin or rounded corner, for recording just that.

The user's design for the batch videos: a video of the tracker alone, starting on the title on
black, with no window around it. Just before a take, the recorder fills every cell of its terminal
with CALIBRATION_COLOUR on the alternate screen (calibration_text), takes a still of the window
(window_still), and asks macOS where the window is on the screen (window_bounds, in points). The
cells are the largest run of rows and columns that hold the colour found at the middle of the still
(cell_area), which leaves the title bar and the margins out whatever their colours, shrunk past any
rounded corner and a pixel more each side, and turned into the screen's points (screen_region), the
rectangle screencapture -R records. The still is taken as a BMP file and read by read_bmp with numpy in a few
operations: a still of a whole terminal on a Retina screen is millions of pixels, and decoding it as a PNG in Python
took about a minute, while the cells stayed filled with the colour and the take seemed frozen (found by the user).
"""

import os
import struct
import subprocess
import tempfile

import numpy

# The colour the cells are filled with for the still: dark, and unlike any terminal's own background, title bar or margin.
CALIBRATION_COLOUR = (40, 0, 56)
ESCAPE = '\x1b'
ALTERNATE_SCREEN_ON = ESCAPE + '[?1049h'
ALTERNATE_SCREEN_OFF = ESCAPE + '[?1049l'
HOME = ESCAPE + '[H'
CLEAR = ESCAPE + '[2J'
RESET = ESCAPE + '[0m'
BACKGROUND = ESCAPE + '[48;2;{red};{green};{blue}m'
NEW_LINE = '\r\n'
SPACE = ' '
# How near a pixel's channels must be to the middle's to count as the colour, since the still is colour-managed, and how much of a row or a column must hold it.
TOLERANCE = 14
HOLDING_SHARE = 0.9
# A pixel more taken off each side, so that nothing of a margin is ever in the video.
SAFETY_PIXELS = 1
SCREENCAPTURE = 'screencapture'
STILL_FLAGS = ('-x', '-o', '-t', 'bmp', '-l')
SWIFT = 'swift'
STILL_NAME = 'still.bmp'
COMMA = ','
# How many numbers macOS answers with for a window's bounds: left, top, width and height.
BOUNDS_NUMBERS = 4
READ_BYTES = 'rb'
SWIFT_SUFFIX = '.swift'
WRITE_TEXT = 'w'
TIMEOUT_SECONDS = 30
# Asking macOS where a window is, in points from the top left of the main screen.
BOUNDS_SWIFT = '''
import CoreGraphics
let id = CGWindowID(CommandLine.arguments[1])!
if let windows = CGWindowListCopyWindowInfo([.optionIncludingWindow], id) as? [[String: Any]],
   let bounds = windows.first?[kCGWindowBounds as String] as? [String: Any] {
    print(bounds["X"]!, bounds["Y"]!, bounds["Width"]!, bounds["Height"]!)
}
'''
# The BMP format as screencapture -t bmp writes it: its signature, where the header's numbers lie, and the masks of a
# 32-bit pixel's channels, which a file with BI_BITFIELDS gives and one with BI_RGB leaves to these, its alpha unused.
BMP_SIGNATURE = b'BM'
PIXELS_AT = '<I'
PIXELS_AT_PLACE = 10
HEADER_SIZE_PLACE = 14
SIZE_LAYOUT = '<ii'
SIZE_PLACE = 18
BITS_LAYOUT = '<H'
BITS_PLACE = 28
COMPRESSION_PLACE = 30
MASKS_LAYOUT = '<III'
MASKS_PLACE = 54
ALPHA_MASK_PLACE = 66
ALPHA_MASK_HEADER_SIZE = 56
THIRTY_TWO_BITS = 32
BI_RGB = 0
BI_BITFIELDS = 3
RGB_MASKS = (0x00FF0000, 0x0000FF00, 0x000000FF)
NO_MASK = 0
FULL = 255
PIXEL_TYPE = '<u4'
ERR_BMP = 'the still is not a 32-bit BMP file this can read: {reason}'


class Region:
    """A rectangle of the screen in points, as screencapture -R takes it."""

    __slots__ = ('left', 'top', 'width', 'height')

    def __init__(self, *, left, top, width, height):
        self.left = left
        self.top = top
        self.width = width
        self.height = height

    def argument(self):
        """Return the rectangle as screencapture -R takes it: left, top, width and height."""
        return COMMA.join(str(number) for number in (self.left, self.top, self.width, self.height))


def calibration_text(*, columns, rows):
    """Return what to write to the terminal to fill every cell with the calibration colour on the alternate screen."""
    red, green, blue = CALIBRATION_COLOUR
    line = SPACE * columns
    return ALTERNATE_SCREEN_ON + BACKGROUND.format(red=red, green=green, blue=blue) + CLEAR + HOME + NEW_LINE.join([line] * rows)


def restoring_text():
    """Return what to write to put the terminal back after the still."""
    return RESET + CLEAR + ALTERNATE_SCREEN_OFF


def read_bmp(path):
    """Return a 32-bit BMP file's pixels as an array of rows by columns by red, green, blue and alpha, alpha full where the file has none."""
    with open(path, READ_BYTES) as file:
        data = file.read()
    if not data.startswith(BMP_SIGNATURE):
        raise ValueError(ERR_BMP.format(reason=path))
    (pixels_at,) = struct.unpack_from(PIXELS_AT, data, PIXELS_AT_PLACE)
    (header_size,) = struct.unpack_from(PIXELS_AT, data, HEADER_SIZE_PLACE)
    width, height = struct.unpack_from(SIZE_LAYOUT, data, SIZE_PLACE)
    (bits,) = struct.unpack_from(BITS_LAYOUT, data, BITS_PLACE)
    (compression,) = struct.unpack_from(PIXELS_AT, data, COMPRESSION_PLACE)
    if bits != THIRTY_TWO_BITS or compression not in (BI_RGB, BI_BITFIELDS):
        raise ValueError(ERR_BMP.format(reason=(bits, compression)))
    masks = struct.unpack_from(MASKS_LAYOUT, data, MASKS_PLACE) if compression == BI_BITFIELDS else RGB_MASKS
    alpha = NO_MASK
    if compression == BI_BITFIELDS and header_size >= ALPHA_MASK_HEADER_SIZE:
        (alpha,) = struct.unpack_from(PIXELS_AT, data, ALPHA_MASK_PLACE)
    rows = abs(height)
    values = numpy.frombuffer(data, dtype=PIXEL_TYPE, count=width * rows, offset=pixels_at).reshape(rows, width)
    channels = [channel(values=values, mask=mask) for mask in masks]
    channels.append(channel(values=values, mask=alpha) if alpha else numpy.full((rows, width), FULL, dtype=numpy.uint8))
    pixels = numpy.stack(channels, axis=2)
    # A positive height means the rows are stored from the bottom up.
    return pixels[::-1] if height > 0 else pixels


def channel(*, values, mask):
    """Return one channel of 32-bit pixels, the bits its mask covers, as bytes."""
    shift = (mask & -mask).bit_length() - 1
    return ((values & mask) >> shift).astype(numpy.uint8)


def holding(*, pixels, colour):
    """Return where the pixels hold a colour, near enough, and are opaque."""
    near = numpy.all(numpy.abs(pixels[:, :, :3].astype(numpy.int32) - numpy.array(colour)) <= TOLERANCE, axis=2)
    return near & (pixels[:, :, 3] > 0)


def longest_run(flags):
    """Return the first and last place of the longest run of true flags, or None."""
    best = None
    start = None
    for place, flag in enumerate(list(flags) + [False]):
        if flag and start is None:
            start = place
        elif not flag and start is not None:
            if best is None or place - start > best[1] - best[0] + 1:
                best = (start, place - 1)
            start = None
    return best


def cell_area(pixels):
    """Return the top, bottom, left and right pixels of the cells in a still of the window filled with the calibration colour, or None: the longest runs of rows and columns that mostly hold the colour found at the middle, shrunk past any rounded corner that doesn't, and a pixel more each side."""
    height, width = pixels.shape[:2]
    colour = pixels[height // 2, width // 2, :3].astype(numpy.int32)
    held = holding(pixels=pixels, colour=colour)
    rows = longest_run(held.mean(axis=1) >= HOLDING_SHARE * held.mean(axis=1).max())
    columns = longest_run(held.mean(axis=0) >= HOLDING_SHARE * held.mean(axis=0).max())
    if rows is None or columns is None:
        return None
    top, bottom = rows
    left, right = columns
    # A rounded corner takes the cells' corners off; the rows are given up from the bottom until both corners hold the colour.
    while bottom > top and not (held[bottom, left] and held[bottom, right]):
        bottom -= 1
    while top < bottom and not (held[top, left] and held[top, right]):
        top += 1
    top += SAFETY_PIXELS
    bottom -= SAFETY_PIXELS
    left += SAFETY_PIXELS
    right -= SAFETY_PIXELS
    if bottom <= top or right <= left:
        return None
    return top, bottom, left, right


def screen_region(*, area, still_width, bounds):
    """Return the screen's rectangle, in whole points kept inside, of a cell area found in a still of a window whose bounds on the screen are given in points."""
    top, bottom, left, right = area
    window_left, window_top, window_width, _ = bounds
    scale = still_width / window_width
    first_column = -(-left // scale) if scale else left
    first_row = -(-top // scale) if scale else top
    last_column = (right + 1) // scale
    last_row = (bottom + 1) // scale
    return Region(left=int(window_left + first_column), top=int(window_top + first_row), width=int(last_column - first_column), height=int(last_row - first_row))


def window_bounds(window):
    """Return a window's place and size on the screen, in points, asking macOS through Swift, or None."""
    with tempfile.NamedTemporaryFile(mode=WRITE_TEXT, suffix=SWIFT_SUFFIX, delete=False) as script:
        script.write(BOUNDS_SWIFT)
    try:
        result = subprocess.run([SWIFT, script.name, str(window)], capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    finally:
        os.unlink(script.name)
    numbers = result.stdout.split()
    if len(numbers) != BOUNDS_NUMBERS:
        return None
    return tuple(float(number) for number in numbers)


def window_still(window):
    """Return the pixels of a still of a window, with no shadow, or None when it can't be taken."""
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, STILL_NAME)
        try:
            subprocess.run([SCREENCAPTURE, *STILL_FLAGS, str(window), path], timeout=TIMEOUT_SECONDS, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if not os.path.exists(path):
            return None
        return read_bmp(path)
