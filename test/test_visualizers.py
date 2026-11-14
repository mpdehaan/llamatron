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
"""The visualizer's modes on their own: a frame fills the area it is given and no more, starts again when the area changes, and is drawn as big square pixels of colour.

The look is tuned by eye, so these tests hold what doesn't change with the tuning: the shapes,
the sizes, the averaging down and the drawing.
"""

import random
import unittest

import numpy

from llamatron.visualizers.heard import Heard, HeardNote
from llamatron.visualizers.lava_lamp import LavaLamp, derezzed
from llamatron.visualizers.visualizer import Visualizer
from llamatron.visualizers.modes import MODES, mode_called, mode_options
from llamatron.visualizers.cycle import CYCLE_ORDER, CYCLE_SECONDS, CYCLED, Cycle, shuffled
from llamatron.visualizers.llamas import ENERGY_RISE_PER_SECOND, SIZE_HOLD_SECONDS, Llamas, mirrored
from llamatron.visualizers.spectrum import CAP_HANG_SECONDS, Spectrum
from llamatron.visualizers.pixels import FULL_BLOCK, PIXEL_COLUMNS, PixelPainter, pixel_size

WIDTH = 56
SHUFFLES_TRIED = 10
HEIGHT = 16
WIDER = 90
TALLER = 30
ODD_WIDTH = 57
A_MOMENT = 0.5
RED = (255, 0, 0)
BLUE = (0, 0, 255)
CHANNELS = 3
NO_SUCH = 'no_such_mode'
TRACKS = 8
MOST_TRACKS = 64
FRAMES = 40
FRAME_SECONDS = 0.05
BEAT_SECONDS = 0.5
BURST_FRAME = 10
NOTE_EVERY = 8
MIDDLE_C = 60
OCTAVE = 12
FULL_VELOCITY = 127
# The darkest a picture with nothing playing stays under, the dark ground with the rounding of its colour steps.
DARK = 24
# The most the mean brightness may move from one frame to the next, out of 255: a gentle swell, never a flash.
MOST_CHANGE_PER_FRAME = 6.0
# No channel of any mode passes this, short of white, the brightest modes' own ceilings being under it.
CEILING = 240
# The modes drawn in big pixels, each of which answers pixels(); the others draw their own text.
PIXEL_MODES = [mode for mode in MODES if mode.pixels is not Visualizer.pixels]
LOW_PITCH = 36
HIGH_PITCH = 90
SPACE = ' '
TRACKS_PLAYING = 3
TOLERANCE = 1e-9
# A bar and its gap, in columns, so that the test reads one column of each bar.
BAR_STRIDE = 3


class TestModes(unittest.TestCase):

    def test_every_mode_has_a_name_on_screen_and_on_the_command_line_and_is_found_by_it(self):
        self.assertTrue(MODES)
        for mode in MODES:
            self.assertTrue(mode.NAME)
            self.assertIs(mode_called(mode.OPTION), mode)
        self.assertEqual(mode_options(), [mode.OPTION for mode in MODES])
        self.assertIsNone(mode_called(NO_SUCH))


class TestFrames(unittest.TestCase):

    def test_a_frame_fills_the_area_it_is_given_line_for_line(self):
        for mode in MODES:
            lines = mode().frame(width=WIDTH, height=HEIGHT, now=A_MOMENT)
            self.assertEqual(len(lines), HEIGHT)
            self.assertTrue(all(line.cell_len == WIDTH for line in lines))

    def test_a_frame_follows_the_area_when_it_changes(self):
        mode = LavaLamp()
        mode.frame(width=WIDTH, height=HEIGHT, now=A_MOMENT)
        lines = mode.frame(width=WIDER, height=TALLER, now=A_MOMENT)
        self.assertEqual((len(lines), lines[0].cell_len), (TALLER, WIDER))

    def test_an_odd_width_leaves_its_last_column_blank_and_an_empty_area_draws_nothing(self):
        lines = LavaLamp().frame(width=ODD_WIDTH, height=HEIGHT, now=A_MOMENT)
        self.assertEqual(lines[0].cell_len, ODD_WIDTH)
        self.assertEqual(LavaLamp().frame(width=0, height=HEIGHT, now=A_MOMENT), [])



class TestPixelModes(unittest.TestCase):
    """Every mode drawn in big pixels: dark in silence, alight where a track plays, moving, and never a flash, even when every track hits at once."""

    def frames(self, *, mode, notes_at, count):
        """Return the big pixels of count frames of a mode, a frame apart, each hearing the notes notes_at gives for its number."""
        visualizer = mode()
        visualizer.resized(columns=WIDTH // 2, rows=HEIGHT)
        pictures = []
        for number in range(count):
            heard = Heard(notes=notes_at(number), seconds_per_beat=BEAT_SECONDS, beats=number * FRAME_SECONDS / BEAT_SECONDS)
            pictures.append(visualizer.pixels(now=number * FRAME_SECONDS, heard=heard))
        return pictures

    def test_in_silence_each_that_goes_dark_stays_dark(self):
        for mode in [mode for mode in PIXEL_MODES if mode.DARK_IN_SILENCE]:
            with self.subTest(mode=mode.OPTION):
                pictures = self.frames(mode=mode, notes_at=lambda number: (), count=FRAMES)
                self.assertLessEqual(int(pictures[-1].max()), DARK)

    def test_a_track_that_plays_lights_each_up_and_it_moves(self):
        for mode in PIXEL_MODES:
            with self.subTest(mode=mode.OPTION):
                pictures = self.frames(mode=mode, notes_at=lambda number: (HeardNote(0, MIDDLE_C, FULL_VELOCITY, number % NOTE_EVERY == 0, False),), count=FRAMES)
                self.assertGreater(int(pictures[-1].max()), DARK)
                self.assertFalse(numpy.array_equal(pictures[-1], pictures[-2]))

    def test_nothing_passes_the_ceiling_and_the_brightness_never_jumps_even_when_every_track_hits_at_once(self):
        def burst(number):
            return tuple(HeardNote(track, MIDDLE_C + track % OCTAVE, FULL_VELOCITY, number == BURST_FRAME, track % OCTAVE == 0) for track in range(MOST_TRACKS))
        for mode in PIXEL_MODES:
            with self.subTest(mode=mode.OPTION):
                pictures = self.frames(mode=mode, notes_at=burst, count=FRAMES)
                self.assertLessEqual(max(int(picture.max()) for picture in pictures), CEILING)
                means = [float(picture.mean()) for picture in pictures]
                self.assertLessEqual(max(abs(later - earlier) for earlier, later in zip(means, means[1:])), MOST_CHANGE_PER_FRAME)


class TestSpectrum(unittest.TestCase):
    """The spectrum: a note lifts the band of its pitch, low at the left and high at the right, the band falls after, and its cap hangs a moment."""

    def heights(self, spectrum, *, notes=(), now):
        """Return how many cells of each bar's column are drawn, from the frame at a moment hearing the notes given."""
        lines = spectrum.frame(width=WIDTH, height=HEIGHT, now=now, heard=Heard(notes=notes, seconds_per_beat=BEAT_SECONDS, beats=0.0))
        return [sum(1 for line in lines if line.plain[column] != SPACE) for column in range(0, WIDTH, BAR_STRIDE)]

    def started(self):
        """Return a spectrum that has drawn its first frame, which counts no time, so that the next can rise."""
        spectrum = Spectrum()
        spectrum.frame(width=WIDTH, height=HEIGHT, now=0.0)
        return spectrum

    def test_a_low_note_lifts_a_bar_at_the_left_and_a_high_one_at_the_right(self):
        low = self.heights(self.started(), notes=(HeardNote(0, LOW_PITCH, FULL_VELOCITY, True, False),), now=FRAME_SECONDS)
        high = self.heights(self.started(), notes=(HeardNote(0, HIGH_PITCH, FULL_VELOCITY, True, False),), now=FRAME_SECONDS)
        self.assertLess(low.index(max(low)), high.index(max(high)))

    def test_a_bar_falls_after_its_note_and_its_cap_hangs_above_it_a_moment(self):
        spectrum = self.started()
        lifted = self.heights(spectrum, notes=(HeardNote(0, MIDDLE_C, FULL_VELOCITY, True, False),), now=FRAME_SECONDS)
        later = self.heights(spectrum, now=FRAME_SECONDS + CAP_HANG_SECONDS / 2)
        self.assertLess(sum(later), sum(lifted))
        self.assertTrue(any(later))

    def test_in_silence_no_bar_is_drawn(self):
        self.assertEqual(sum(self.heights(Spectrum(), now=FRAME_SECONDS)), 0)


class TestLlamas(unittest.TestCase):
    """The llamas: none in silence, one for each track that plays, facing the way it strolls, growing no more often than its hold, and brightening only gently."""

    def played(self, *, tracks, frames, velocity=FULL_VELOCITY):
        """Return the llamas after frames frames of tracks each starting a note every NOTE_EVERY frames, and the last frame's lines."""
        llamas = Llamas()
        lines = []
        for number in range(frames):
            notes = tuple(HeardNote(track, MIDDLE_C, velocity, number % NOTE_EVERY == 0, False) for track in range(tracks))
            lines = llamas.frame(width=WIDTH, height=HEIGHT, now=number * FRAME_SECONDS, heard=Heard(notes=notes, seconds_per_beat=BEAT_SECONDS, beats=0.0))
        return llamas, lines

    def test_in_silence_there_are_no_llamas(self):
        _, lines = self.played(tracks=0, frames=FRAMES)
        self.assertTrue(all(not line.plain.strip() for line in lines))

    def test_each_track_that_plays_has_a_llama(self):
        llamas, lines = self.played(tracks=TRACKS_PLAYING, frames=FRAMES)
        self.assertEqual(llamas.llama_count(), TRACKS_PLAYING)
        self.assertTrue(any(line.plain.strip() for line in lines))

    def test_a_drawing_mirrored_faces_the_other_way(self):
        drawing = ('(o',)
        self.assertEqual(mirrored(drawing), ('o)',))

    def test_a_llama_that_plays_on_grows_but_never_twice_within_its_hold(self):
        llamas, _ = self.played(tracks=1, frames=int(SIZE_HOLD_SECONDS / FRAME_SECONDS * 2.5))
        llama = llamas.llama_of(0)
        self.assertGreater(llama.size, 0)
        self.assertLess(llama.since_resize, SIZE_HOLD_SECONDS * 2)

    def test_a_note_raises_a_llamas_energy_only_gently(self):
        llamas, _ = self.played(tracks=1, frames=2)
        self.assertLessEqual(llamas.llama_of(0).energy, ENERGY_RISE_PER_SECOND * FRAME_SECONDS + TOLERANCE)


class TestCycle(unittest.TestCase):
    """Cycle: each of the other modes in the order shuffled as the program starts, fresh, moving on every CYCLE_SECONDS, saying which shows."""

    def test_it_moves_on_to_the_next_mode_every_cycle_in_the_programs_order_and_says_which(self):
        cycle = Cycle()
        names = []
        for number in range(len(CYCLED) + 1):
            cycle.frame(width=WIDTH, height=HEIGHT, now=number * CYCLE_SECONDS)
            names.append(cycle.shown_name())
        self.assertEqual(names, [mode.NAME for mode in CYCLE_ORDER] + [CYCLE_ORDER[0].NAME])
        self.assertIsInstance(cycle.showing(), CYCLE_ORDER[0])

    def test_the_programs_order_holds_every_mode_once(self):
        self.assertEqual(sorted(mode.NAME for mode in CYCLE_ORDER), sorted(mode.NAME for mode in CYCLED))

    def test_every_cycle_of_one_run_keeps_the_same_order(self):
        first = Cycle()
        second = Cycle()
        self.assertIs(type(first.showing()), type(second.showing()))

    def test_a_shuffle_gives_orders_of_their_own_from_different_seeds(self):
        orders = {shuffled(modes=CYCLED, chooser=random.Random(seed)) for seed in range(SHUFFLES_TRIED)}
        self.assertGreater(len(orders), 1)
        for order in orders:
            self.assertEqual(sorted(mode.NAME for mode in order), sorted(mode.NAME for mode in CYCLED))

    def test_within_a_cycle_it_stays_on_the_same_mode(self):
        cycle = Cycle()
        cycle.frame(width=WIDTH, height=HEIGHT, now=0.0)
        showing = cycle.showing()
        cycle.frame(width=WIDTH, height=HEIGHT, now=CYCLE_SECONDS / 2)
        self.assertIs(cycle.showing(), showing)


class TestPixels(unittest.TestCase):

    def test_a_big_pixel_is_two_columns_of_one_row_and_a_run_of_one_colour_is_one_piece(self):
        pixels = numpy.array([[RED, RED, BLUE]])
        line = PixelPainter().lines(pixels=pixels, width=len(pixels[0]) * PIXEL_COLUMNS, height=1)[0]
        self.assertEqual(line.plain, FULL_BLOCK * (len(pixels[0]) * PIXEL_COLUMNS))
        self.assertEqual(len(line.spans), 2)

    def test_the_area_holds_whole_pixels(self):
        self.assertEqual(pixel_size(width=ODD_WIDTH, height=HEIGHT), (ODD_WIDTH // PIXEL_COLUMNS, HEIGHT))

    def test_derezzing_averages_each_block_of_fine_pixels(self):
        fine = numpy.zeros((2, 2, CHANNELS), dtype=numpy.int32)
        fine[0, 0] = RED
        fine[1, 1] = RED
        self.assertEqual(derezzed(fine=fine, factor=2).tolist(), [[[RED[0] // 2, 0, 0]]])


if __name__ == '__main__':
    unittest.main()
