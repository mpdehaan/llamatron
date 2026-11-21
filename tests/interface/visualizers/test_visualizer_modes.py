# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The visualizer's later modes, each on its own: the fireworks' sparks, WarpZone's balls and rings, the pipes, the maze, Mystify's polygons and the laser llama's beams.

The shared tests of every mode, the sizes of frames and never flashing, are in test_visualizers.py;
these hold what each mode alone promises.
"""

import math
import numpy
import random
import unittest

from llamatron.interface.visualizers import cells, fireworks as fireworks_values, life as life_values, mystify as mystify_values, piano_roll, pipes as pipes_values, warpzone
from llamatron.interface.visualizers.digital_rain import DigitalRain
from llamatron.interface.visualizers.fireworks import brightest_of_blocks, Fireworks
from llamatron.interface.visualizers.heard import FrameHearing, HeardNote
from llamatron.interface.visualizers.laser_llama import LaserLlama, mirrored_drawing
from llamatron.interface.visualizers.life import Life, stepped
from llamatron.interface.visualizers.mandelbrot import escape_times
from llamatron.interface.visualizers.maze import carved, inside, Maze
from llamatron.interface.visualizers.mystify import Mystify
from llamatron.interface.visualizers.piano_roll import drum_lane, nth_colour, PianoRollVisualizer
from llamatron.interface.visualizers.pipes import Pipes
from llamatron.interface.visualizers.warpzone import WarpZone
from llamatron.user_strings import visualizers

WIDTH = 40
HEIGHT = 12
FRAME_SECONDS = 0.05
BEAT_SECONDS = 0.5
MIDDLE_C = 60
OCTAVE = 12
# Frames drawn unevenly, long and short by turns, and how many frames the palette is given to ease, two seconds.
UNEVEN_FRAMES = 40
UNEVEN_SHORT = 0.6
UNEVEN_LONG = 1.4
EASED_FRAMES = 40
FULL_VELOCITY = 127
TRACKS = 4
MOST_TRACKS = 64
SEED = 3
TOLERANCE = 0.01
SPACE = ' '
NO_CHARACTERS = ''
# How far apart two rockets' colours are at least, as the distance between their red, green and blue.
FAR_APART = 100


def heard(notes):
    return FrameHearing(notes=tuple(notes), seconds_per_beat=BEAT_SECONDS, beats=0.0)


def every_track_starting(*, tracks, number, every=4):
    return [HeardNote(track, MIDDLE_C + track, FULL_VELOCITY, number % every == 0, False) for track in range(tracks)]


class TestFireworks(unittest.TestCase):

    def test_the_sparks_never_pass_their_most_however_many_notes(self):
        fireworks = Fireworks()
        fireworks.resized(columns=WIDTH // 2, rows=HEIGHT)
        for number in range(60):
            fireworks.pixels(now=number * FRAME_SECONDS, heard=heard(every_track_starting(tracks=MOST_TRACKS, number=number, every=1)))
            self.assertLessEqual(fireworks.spark_count(), fireworks_values.MOST_SPARKS)
        self.assertGreater(fireworks.spark_count(), 0)

    def test_the_rockets_colours_are_far_apart_from_one_another(self):
        for place, colour in enumerate(fireworks_values.ROCKET_COLOURS):
            for other in fireworks_values.ROCKET_COLOURS[place + 1:]:
                self.assertGreater(math.dist(colour, other), FAR_APART)

    def test_the_rockets_take_their_colours_in_equal_shares(self):
        fireworks = Fireworks()
        rounds = 3
        taken = [fireworks.next_colour() for _ in range(rounds * len(fireworks_values.ROCKET_COLOURS))]
        for colour in fireworks_values.ROCKET_COLOURS:
            self.assertEqual(taken.count(colour), rounds)

    def test_a_spark_stays_one_crisp_big_pixel_when_the_picture_is_taken_down(self):
        fine = numpy.zeros((fireworks_values.SUPERSAMPLE * 2, fireworks_values.SUPERSAMPLE * 2, 3), dtype=numpy.int32)
        fine[0, 0] = fireworks_values.ROCKET_COLOURS[0]
        small = brightest_of_blocks(fine=fine, factor=fireworks_values.SUPERSAMPLE)
        self.assertEqual(tuple(small[0, 0]), fireworks_values.ROCKET_COLOURS[0])
        self.assertEqual(int(small[1:, :].sum() + small[:, 1:].sum()), 0)


class TestWarpZone(unittest.TestCase):

    def test_every_ball_stays_inside_and_moves_at_the_tempos_speed(self):
        zone = WarpZone()
        zone.frame(width=WIDTH, height=HEIGHT, now=0.0, heard=heard(every_track_starting(tracks=TRACKS, number=0)))
        for number in range(1, 100):
            before = {track: ball.place.copy() for track, ball in zone.balls().items()}
            zone.frame(width=WIDTH, height=HEIGHT, now=number * FRAME_SECONDS, heard=heard(every_track_starting(tracks=TRACKS, number=number)))
            for track, ball in zone.balls().items():
                self.assertTrue(0 <= ball.place[0] <= HEIGHT * cells.BRAILLE_ROWS - 1 and 0 <= ball.place[1] <= WIDTH * cells.BRAILLE_COLUMNS - 1)
                self.assertAlmostEqual(math.hypot(*ball.heading), 1.0, delta=TOLERANCE)
                moved = math.hypot(*(ball.place - before[track]))
                self.assertLessEqual(moved, warpzone.BALL_SPEED * HEIGHT * cells.BRAILLE_ROWS * FRAME_SECONDS + 2 * warpzone.BALL_RADIUS + TOLERANCE)


class TestPipes(unittest.TestCase):

    def test_pipes_grow_in_box_characters_as_notes_play(self):
        pipes = Pipes()
        lines = []
        for number in range(40):
            lines = pipes.frame(width=WIDTH, height=HEIGHT, now=number * FRAME_SECONDS, heard=heard(every_track_starting(tracks=TRACKS, number=number)))
        drawn = {character for line in lines for character in line.plain if character != SPACE}
        self.assertTrue(drawn)
        self.assertTrue(drawn & set(pipes_values.JOINS.values()))

    def test_a_full_area_fades_and_starts_again_empty(self):
        pipes = Pipes()
        number = 0
        while not pipes.is_fading() and number < 4000:
            pipes.frame(width=WIDTH, height=HEIGHT, now=number * FRAME_SECONDS, heard=heard(every_track_starting(tracks=TRACKS, number=number, every=1)))
            number += 1
        self.assertTrue(pipes.is_fading())
        for step in range(int(pipes_values.FADE_SECONDS / FRAME_SECONDS) + 2):
            lines = pipes.frame(width=WIDTH, height=HEIGHT, now=(number + step) * FRAME_SECONDS, heard=heard([]))
        self.assertFalse(pipes.is_fading())
        self.assertTrue(all(not line.plain.strip() for line in lines))


class TestMaze(unittest.TestCase):

    def test_every_corridor_of_a_carved_maze_can_be_reached_from_the_first(self):
        walls = carved(rows=HEIGHT, columns=WIDTH, chooser=random.Random(SEED))
        corridors = inside(rows=HEIGHT, columns=WIDTH) & ~walls
        start = tuple(numpy.argwhere(corridors)[0])
        reached = {start}
        waiting = [start]
        while waiting:
            row, column = waiting.pop()
            for down, across in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                place = (row + down, column + across)
                if 0 <= place[0] < HEIGHT and 0 <= place[1] < WIDTH and corridors[place] and place not in reached:
                    reached.add(place)
                    waiting.append(place)
        self.assertEqual(len(reached), numpy.count_nonzero(corridors))

    def test_a_walker_appears_for_each_track_and_walks(self):
        maze = Maze()
        for number in range(20):
            lines = maze.frame(width=WIDTH, height=HEIGHT, now=number * FRAME_SECONDS, heard=heard(every_track_starting(tracks=TRACKS, number=number)))
        self.assertEqual(maze.walker_count(), TRACKS)
        self.assertTrue(any('●' in line.plain for line in lines))


class TestMystify(unittest.TestCase):

    def test_a_polygons_corners_follow_how_many_notes_its_track_holds(self):
        mystify = Mystify()
        chord = [HeardNote(0, MIDDLE_C + step, FULL_VELOCITY, True, False) for step in (0, 4, 7)]
        mystify.frame(width=WIDTH, height=HEIGHT, now=0.0, heard=heard(chord))
        self.assertEqual(mystify.corners_of(0), mystify_values.FEWEST_CORNERS + len(chord) - 1)
        mystify.frame(width=WIDTH, height=HEIGHT, now=FRAME_SECONDS, heard=heard(chord[:1]))
        self.assertEqual(mystify.corners_of(0), mystify_values.FEWEST_CORNERS)


# A drawing of two lines that lean, and the same drawing facing the other way.
LEANING = ('(/ ', ' \\)')
LEANING_TURNED = (' \\)', '(/ ')


class TestLaserLlama(unittest.TestCase):

    def test_a_drawing_turned_round_leans_the_other_way_and_turned_twice_is_itself(self):
        self.assertEqual(mirrored_drawing(LEANING), LEANING_TURNED)
        self.assertEqual(mirrored_drawing(mirrored_drawing(LEANING)), LEANING)

    def test_each_note_that_starts_fires_a_beam_which_fades_away(self):
        llama = LaserLlama()
        llama.frame(width=WIDTH, height=HEIGHT, now=0.0, heard=heard(every_track_starting(tracks=TRACKS, number=0)))
        self.assertEqual(llama.beam_count(), TRACKS)
        llama.frame(width=WIDTH, height=HEIGHT, now=10.0, heard=heard([]))
        self.assertEqual(llama.beam_count(), 0)


class TestMandelbrot(unittest.TestCase):

    def test_a_point_in_the_set_never_escapes_and_one_far_outside_escapes_at_once(self):
        escapes = escape_times(numpy.array([[0j, 2 + 2j]]))
        self.assertEqual(escapes[0, 0], -1.0)
        self.assertLess(escapes[0, 1], 2)


class TestLife(unittest.TestCase):

    def test_a_blinker_turns_and_a_block_stays_by_conways_rules(self):
        blinker = numpy.zeros((5, 5), dtype=bool)
        blinker[2, 1:4] = True
        turned = stepped(blinker)
        self.assertEqual([tuple(place) for place in numpy.argwhere(turned)], [(1, 2), (2, 2), (3, 2)])
        self.assertTrue((stepped(turned) == blinker).all())
        block = numpy.zeros((4, 4), dtype=bool)
        block[1:3, 1:3] = True
        self.assertTrue((stepped(block) == block).all())

    def test_a_note_brings_cells_to_life_and_an_empty_grid_is_seeded_afresh(self):
        life = Life()
        life.frame(width=WIDTH, height=HEIGHT, now=0.0, heard=heard([]))
        self.assertEqual(life.alive().shape, (HEIGHT // life_values.CELL_ROWS, WIDTH // life_values.CELL_COLUMNS))
        before = int(life.alive().sum())
        life.frame(width=WIDTH, height=HEIGHT, now=FRAME_SECONDS, heard=heard(every_track_starting(tracks=TRACKS, number=0)))
        self.assertGreaterEqual(int(life.alive().sum()), before)
        for number in range(2, 200):
            life.frame(width=WIDTH, height=HEIGHT, now=number * BEAT_SECONDS, heard=FrameHearing(notes=(), seconds_per_beat=BEAT_SECONDS, beats=float(number)))
            self.assertTrue(life.alive().any())

    def test_every_line_is_as_wide_as_the_area(self):
        lines = Life().frame(width=WIDTH, height=HEIGHT, now=0.0, heard=heard([]))
        self.assertEqual(len(lines), HEIGHT)
        for line in lines:
            self.assertEqual(len(line.plain), WIDTH)



ROLL_WIDTH = 60
ROLL_HEIGHT = 30
KICK = 36
LEAD_TRACK = 0
DRUM_TRACK = 1
HIGH_NOTE = 84
# Two notes further apart than the roll's rows, a few seconds of frames, and a few rows of the roll, far less than the way between the notes.
FAR_LOW_NOTE = 30
FAR_HIGH_NOTE = 100
FRAMES_OF_A_WHILE = 60
A_FEW_ROWS = 3
# Frames enough for a note to roll the whole width of the roll and off its left edge.
FRAMES_TO_ROLL_OFF = 400
TRACK_NAMES = ('lead', 'drums')


class TestPianoRoll(unittest.TestCase):
    """The piano roll: every key a row, notes rolling in from the right, held notes growing, the drums in lanes at the bottom, the rows following the notes."""

    def played(self, *, roll, frames, notes, start=0.0):
        """Draw frames one after another from a moment, each hearing the notes given, and return the last frame's lines and the moment after."""
        lines = []
        now = start
        for _ in range(frames):
            lines = roll.frame(width=ROLL_WIDTH, height=ROLL_HEIGHT, now=now, heard=FrameHearing(notes=tuple(notes), seconds_per_beat=BEAT_SECONDS, beats=now / BEAT_SECONDS, names=TRACK_NAMES))
            notes = [note._replace(started=False) for note in notes]
            now += FRAME_SECONDS
        return lines, now

    def row_with_note(self, lines):
        return [place for place, line in enumerate(lines) if piano_roll.NOTE_CHARACTER in line.plain[piano_roll.LABEL_COLUMNS:]]

    def test_a_frame_fills_its_area(self):
        lines, _ = self.played(roll=PianoRollVisualizer(), frames=1, notes=[])
        self.assertEqual(len(lines), ROLL_HEIGHT)
        self.assertTrue(all(line.cell_len == ROLL_WIDTH for line in lines))

    def test_a_note_comes_in_at_the_right_and_rolls_left_and_grows_while_it_sounds(self):
        roll = PianoRollVisualizer()
        lines, now = self.played(roll=roll, frames=1, notes=[HeardNote(LEAD_TRACK, MIDDLE_C, FULL_VELOCITY, True, False)])
        row = self.row_with_note(lines)[0]
        self.assertEqual(lines[row].plain[-1], piano_roll.NOTE_CHARACTER)
        held = HeardNote(LEAD_TRACK, MIDDLE_C, FULL_VELOCITY, False, False)
        lines, now = self.played(roll=roll, frames=20, notes=[held], start=now)
        sounding = lines[row].plain.count(piano_roll.NOTE_CHARACTER)
        self.assertGreater(sounding, 3)
        self.assertEqual(lines[row].plain[-1], piano_roll.NOTE_CHARACTER)
        lines, now = self.played(roll=roll, frames=20, notes=[], start=now)
        self.assertNotEqual(lines[row].plain[-1], piano_roll.NOTE_CHARACTER)
        self.assertEqual(lines[row].plain.count(piano_roll.NOTE_CHARACTER), sounding)

    def test_it_rolls_columns_per_beat(self):
        roll = PianoRollVisualizer()
        lines, now = self.played(roll=roll, frames=1, notes=[HeardNote(LEAD_TRACK, MIDDLE_C, FULL_VELOCITY, True, False)])
        row = self.row_with_note(lines)[0]
        beats = 2
        lines, _ = self.played(roll=roll, frames=int(beats * BEAT_SECONDS / FRAME_SECONDS), notes=[], start=now)
        self.assertAlmostEqual(lines[row].plain.index(piano_roll.NOTE_CHARACTER), ROLL_WIDTH - 1 - beats * piano_roll.COLUMNS_PER_BEAT, delta=1)

    def test_drums_take_lanes_at_the_bottom_only_once_a_drum_plays(self):
        roll = PianoRollVisualizer()
        lines, now = self.played(roll=roll, frames=1, notes=[HeardNote(LEAD_TRACK, MIDDLE_C, FULL_VELOCITY, True, False)])
        self.assertFalse(any(line.plain.startswith(visualizers.MSG_PIANO_ROLL_DRUM_LANES[0]) for line in lines))
        lines, _ = self.played(roll=roll, frames=1, notes=[HeardNote(DRUM_TRACK, KICK, FULL_VELOCITY, True, True)], start=now)
        kick_row = ROLL_HEIGHT - 1 - drum_lane(KICK)
        self.assertTrue(lines[kick_row].plain.startswith(visualizers.MSG_PIANO_ROLL_DRUM_LANES[drum_lane(KICK)]))
        self.assertEqual(lines[kick_row].plain[-1], piano_roll.NOTE_CHARACTER)
        self.assertEqual(len(visualizers.MSG_PIANO_ROLL_DRUM_LANES), piano_roll.DRUM_ROWS)

    def test_every_key_has_a_row_and_each_c_a_line(self):
        roll = PianoRollVisualizer()
        lines, _ = self.played(roll=roll, frames=1, notes=[HeardNote(LEAD_TRACK, MIDDLE_C, FULL_VELOCITY, True, False)])
        c_rows = [place for place, line in enumerate(lines) if piano_roll.LINE_CHARACTER in line.plain]
        self.assertGreaterEqual(len(c_rows), 2)
        self.assertEqual(c_rows[1] - c_rows[0], OCTAVE)

    def test_the_first_notes_place_the_rows_at_once(self):
        roll = PianoRollVisualizer()
        self.played(roll=roll, frames=1, notes=[HeardNote(LEAD_TRACK, HIGH_NOTE, FULL_VELOCITY, True, False)])
        self.assertEqual(roll.get_centre(), HIGH_NOTE)

    def test_the_rows_stay_still_while_every_pitch_heard_fits(self):
        roll = PianoRollVisualizer()
        low = HeardNote(LEAD_TRACK, MIDDLE_C, FULL_VELOCITY, True, False)
        high = HeardNote(LEAD_TRACK, MIDDLE_C + OCTAVE, FULL_VELOCITY, True, False)
        _, now = self.played(roll=roll, frames=1, notes=[low, high])
        settled = roll.get_centre()
        self.assertEqual(settled, MIDDLE_C + OCTAVE / 2)
        # The low note alone, then the high note alone, for a long while: the rows don't move, since both fit.
        for note in (low, high, low, high):
            _, now = self.played(roll=roll, frames=FRAMES_OF_A_WHILE, notes=[note], start=now)
            self.assertEqual(roll.get_centre(), settled)

    def test_the_rows_ease_slowly_toward_what_sounds_only_when_the_pitches_heard_do_not_fit(self):
        roll = PianoRollVisualizer()
        low = HeardNote(LEAD_TRACK, FAR_LOW_NOTE, FULL_VELOCITY, True, False)
        high = HeardNote(LEAD_TRACK, FAR_HIGH_NOTE, FULL_VELOCITY, True, False)
        _, now = self.played(roll=roll, frames=1, notes=[low])
        self.assertEqual(roll.get_centre(), FAR_LOW_NOTE)
        # The high note is further off than the rows reach, so the rows go toward it, a little each frame and never in a jump.
        _, now = self.played(roll=roll, frames=1, notes=[high], start=now)
        _, now = self.played(roll=roll, frames=1, notes=[high._replace(started=False)], start=now)
        after_a_frame = roll.get_centre()
        self.assertGreater(after_a_frame, FAR_LOW_NOTE)
        self.assertLess(after_a_frame - FAR_LOW_NOTE, A_FEW_ROWS)
        _, now = self.played(roll=roll, frames=FRAMES_OF_A_WHILE, notes=[high._replace(started=False)], start=now)
        self.assertGreater(roll.get_centre(), after_a_frame)
        self.assertLessEqual(roll.get_centre(), FAR_HIGH_NOTE)
        # In silence the rows stay where they are.
        resting = roll.get_centre()
        self.played(roll=roll, frames=FRAMES_OF_A_WHILE, notes=[], start=now)
        self.assertEqual(roll.get_centre(), resting)

    def test_the_legend_names_the_tracks_on_the_roll_in_track_order_and_a_track_keeps_the_colour_it_was_first_heard_with(self):
        roll = PianoRollVisualizer()
        lines, now = self.played(roll=roll, frames=1, notes=[HeardNote(DRUM_TRACK, KICK, FULL_VELOCITY, True, True)])
        self.assertIn(visualizers.MSG_PIANO_ROLL_LEGEND_MARK + TRACK_NAMES[DRUM_TRACK], lines[0].plain)
        self.assertNotIn(TRACK_NAMES[LEAD_TRACK], lines[0].plain)
        lines, now = self.played(roll=roll, frames=1, notes=[HeardNote(LEAD_TRACK, MIDDLE_C, FULL_VELOCITY, True, False)], start=now)
        # The lead was heard second but is the song's first track, so its name comes first.
        legend = lines[0].plain
        self.assertLess(legend.index(TRACK_NAMES[LEAD_TRACK]), legend.index(TRACK_NAMES[DRUM_TRACK]))
        # Once the drum's hit has rolled off the left edge and the lead still sounds, only the lead is named.
        lines, _ = self.played(roll=roll, frames=FRAMES_TO_ROLL_OFF, notes=[HeardNote(LEAD_TRACK, MIDDLE_C, FULL_VELOCITY, False, False)], start=now)
        self.assertIn(TRACK_NAMES[LEAD_TRACK], lines[0].plain)
        self.assertNotIn(TRACK_NAMES[DRUM_TRACK], lines[0].plain)
        self.assertEqual(roll.track_colour(DRUM_TRACK), nth_colour(0))
        self.assertEqual(roll.track_colour(LEAD_TRACK), nth_colour(1))
        self.assertEqual(nth_colour(len(piano_roll.TRACK_COLOURS)), nth_colour(0))
        self.assertEqual(piano_roll.LEGEND_ROWS, 1)

class TestDigitalRain(unittest.TestCase):

    def test_each_note_that_starts_sends_a_stream_which_falls_off_the_bottom(self):
        rain = DigitalRain()
        rain.frame(width=WIDTH, height=HEIGHT, now=0.0, heard=heard(every_track_starting(tracks=TRACKS, number=0)))
        self.assertGreaterEqual(rain.stream_count(), TRACKS)
        for number in range(1, 400):
            rain.frame(width=WIDTH, height=HEIGHT, now=number * FRAME_SECONDS, heard=FrameHearing(notes=(), seconds_per_beat=BEAT_SECONDS, beats=0.0))
        # The notes' streams have gone; only the dim rain that falls by itself is left.
        self.assertLess(rain.stream_count(), TRACKS * 3)

    def test_it_draws_only_ones_and_zeros_in_green(self):
        rain = DigitalRain()
        lines = []
        for number in range(40):
            lines = rain.frame(width=WIDTH, height=HEIGHT, now=number * FRAME_SECONDS, heard=heard(every_track_starting(tracks=TRACKS, number=number)))
        self.assertEqual(len(lines), HEIGHT)
        self.assertTrue(set(NO_CHARACTERS.join(line.plain for line in lines)) <= set(visualizers.MSG_RAIN_DIGITS + SPACE))
        for line in lines:
            for span in line.spans:
                red, green, blue = span.style.color.get_truecolor()
                self.assertGreaterEqual(green, red)
                self.assertGreaterEqual(green, blue)

    def test_rain_falls_in_silence_too(self):
        rain = DigitalRain()
        for number in range(100):
            rain.frame(width=WIDTH, height=HEIGHT, now=number * FRAME_SECONDS, heard=heard([]))
        self.assertGreater(rain.stream_count(), 0)


if __name__ == '__main__':
    unittest.main()
