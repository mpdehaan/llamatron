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

"""Tests a batch video's stage on its own (tui/batch_stage.py and tui/components/stage_drawing.py), on moments the test chooses: the READY box, its growing into the scene frame, the pulse and the fade to black."""

import unittest

from rich.text import Text

from llamatron.strings.about import MSG_BLOCK, MSG_READY_WORD
from llamatron.tui.batch_stage import ALTERNATE_FADE_SECONDS, ALTERNATE_SECONDS, FRAME_COLOURS, FRAME_LAP_BARS, GROW_SECONDS, READY_SECONDS, BatchStage
from llamatron.tui.components.stage_drawing import (
    BLACK, FRAME_GAP_COLUMNS, FRAME_GAP_ROWS, GAP_COLUMNS, GAP_ROWS, PULSE_CEILING, SIDE_TRACK, faded, frame_box, inside_of, pulse_levels, ready_box,
    track_cells, visualizer_area,
)
from llamatron.tui.components.title_card import NARROW, words_width
from llamatron.tui.drawing import Box

WIDTH = 100
HEIGHT = 30
ARRANGE_WORD = 'treble'
ARRANGE_LINE = (ARRANGE_WORD + ' 1   bass 1').center(WIDTH)
READY_ROWS = 5
COUNT = 40
WHOLE_BAR = 1
# Half a second a beat: 120 beats a minute.
SECONDS_PER_BEAT = 0.5
QUARTERS = 4
# Frames for the pulse's speed: a twentieth of a second, drawn long and short by turns.
FRAME = 0.05
PULSE_FRAMES = 60
UNEVEN_SHORT = 0.6
UNEVEN_LONG = 1.4
CLIPS_FIRST_WORD = 'llamatron'
SPACE = ' '
SHOWN = 1.0
PLAYING = READY_SECONDS + GROW_SECONDS + 1.0
CLOCKWISE = 1
ANTICLOCKWISE = -1
LINE_BREAK = '\n'
BLANK = ''


def arrange():
    return [Text(ARRANGE_LINE, style='bold') for _ in range(HEIGHT)]


def colours(lines):
    return [tuple(span.style.color.get_truecolor()) for line in lines for span in line.spans]


# Moments of an alternating frame, in seconds after the box has grown: on the clips, half way through the fade to the
# visualizer, on the visualizer, and back on the clips after a whole round.
ON_CLIPS = 1.0
MID_FADE = ALTERNATE_SECONDS + ALTERNATE_FADE_SECONDS / 2
ON_VISUALIZER = ALTERNATE_SECONDS + ALTERNATE_FADE_SECONDS + 1.0
CLIPS_AGAIN = 2 * (ALTERNATE_SECONDS + ALTERNATE_FADE_SECONDS) + 1.0


def visualizer_frame():
    """Return a visualizer's frame for the tests: every cell a block."""
    return [Text(MSG_BLOCK * WIDTH) for _ in range(HEIGHT)]


def inside_text(lines):
    """Return the text inside the frame, where the clips and the visualizer show, leaving out the track the pulse goes round."""
    inside = inside_of(frame_box(width=WIDTH, height=HEIGHT))
    return LINE_BREAK.join(line.plain[inside.left:inside.right + 1] for line in lines[inside.top:inside.bottom + 1])


def alternating_at(after_grown):
    """Return an alternating stage's screen a number of seconds after its box has grown, and the stage."""
    stage = BatchStage(began=0.0, bar_length=WHOLE_BAR, alternate=True)
    stage.start_song(at=READY_SECONDS)
    now = READY_SECONDS + GROW_SECONDS + after_grown
    return stage.screen(arrange=arrange(), width=WIDTH, height=HEIGHT, now=now, frame=visualizer_frame(), seconds_per_beat=SECONDS_PER_BEAT, scene=0, clips=arrange()), stage


def stage_at(now, *, stage=None, scene=0, seconds_per_beat=None):
    stage = stage or BatchStage(began=0.0, bar_length=WHOLE_BAR)
    if now >= READY_SECONDS and not stage.is_growing_or_grown(now):
        stage.start_song(at=READY_SECONDS)
    return stage, stage.screen(arrange=arrange(), width=WIDTH, height=HEIGHT, now=now, frame=visualizer_frame(), seconds_per_beat=seconds_per_beat or SECONDS_PER_BEAT, scene=scene)


class TestGeometry(unittest.TestCase):

    def test_the_ready_box_holds_ready_with_two_rows_and_four_columns_of_gap(self):
        # The gap is the black gap inside the track, which the frame keeps too, and the room left inside it.
        inside = inside_of(ready_box(width=WIDTH, height=HEIGHT))
        self.assertEqual(inside.right - inside.left + 1 + 2 * FRAME_GAP_COLUMNS, words_width(word=MSG_READY_WORD, scale=NARROW) + 2 * GAP_COLUMNS)
        self.assertEqual(inside.bottom - inside.top + 1 + 2 * FRAME_GAP_ROWS, READY_ROWS + 2 * GAP_ROWS)

    def test_the_frame_leaves_the_outermost_cells_black_then_the_track_then_a_gap(self):
        frame = frame_box(width=WIDTH, height=HEIGHT)
        self.assertEqual((frame.top, frame.bottom), (0, HEIGHT - 1))
        area = visualizer_area(width=WIDTH, height=HEIGHT)
        self.assertEqual(area.top, frame.top + 2 + FRAME_GAP_ROWS)
        self.assertEqual(area.left, frame.left + 1 + SIDE_TRACK + FRAME_GAP_COLUMNS)
        self.assertGreater(frame.left, 0)

    def test_the_track_goes_round_clockwise_two_columns_wide_down_the_sides(self):
        box = ready_box(width=WIDTH, height=HEIGHT)
        places = track_cells(box)
        self.assertEqual(places[0], [(box.top + 1, box.left + 1)])
        self.assertEqual(places[1][0], (box.top + 1, box.left + 2))
        sides = [place for place in places if len(place) == SIDE_TRACK]
        self.assertEqual(len(sides), 2 * (box.bottom - box.top - 3))


class TestPulse(unittest.TestCase):

    def test_the_head_is_brightest_and_the_tail_trails_behind_the_way_it_goes(self):
        levels = pulse_levels(count=COUNT, head=0.5, direction=CLOCKWISE)
        head = COUNT // 2
        self.assertAlmostEqual(levels[head], PULSE_CEILING)
        self.assertGreater(levels[head - 2], levels[head - 4])
        self.assertEqual(levels[head + 2], 0.0)
        turned = pulse_levels(count=COUNT, head=0.5, direction=ANTICLOCKWISE)
        self.assertGreater(turned[head + 2], 0.0)
        self.assertEqual(turned[head - 2], 0.0)

    def test_a_change_of_scene_turns_the_pulse_round_and_takes_the_next_colour(self):
        stage, _ = stage_at(PLAYING, scene=0)
        self.assertEqual(stage.colour(PLAYING), FRAME_COLOURS[0])
        before = stage.direction()
        stage_at(PLAYING + 0.1, stage=stage, scene=1)
        self.assertEqual(stage.direction(), -before)
        self.assertEqual(stage.colour(PLAYING + 10), FRAME_COLOURS[1])


class TestStage(unittest.TestCase):

    def test_before_the_song_arrange_shows_with_ready_in_its_box(self):
        _, lines = stage_at(SHOWN)
        text = LINE_BREAK.join(line.plain for line in lines)
        self.assertIn(ARRANGE_WORD, text)
        self.assertIn(Box.DOUBLE_TOP_LEFT, text)
        self.assertEqual(len(lines), HEIGHT)
        self.assertTrue(all(len(line.plain) == WIDTH for line in lines))

    def test_once_grown_the_border_and_arrange_are_gone_and_the_visualizer_fills_the_frame(self):
        _, lines = stage_at(PLAYING)
        text = LINE_BREAK.join(line.plain for line in lines)
        self.assertNotIn(Box.DOUBLE_TOP_LEFT, text)
        area = visualizer_area(width=WIDTH, height=HEIGHT)
        self.assertEqual(lines[area.top].plain[area.left:area.right + 1], MSG_BLOCK * (area.right - area.left + 1))

    def test_alternating_starts_on_the_clips_then_turns_to_the_visualizer_and_back(self):
        for after, clips in ((ON_CLIPS, True), (ON_VISUALIZER, False), (CLIPS_AGAIN, True)):
            with self.subTest(after=after):
                text = inside_text(alternating_at(after)[0])
                self.assertEqual(ARRANGE_WORD in text, clips)
                self.assertEqual(MSG_BLOCK in text, not clips)

    def test_a_change_fades_through_black_with_neither_view_at_its_middle(self):
        lines, stage = alternating_at(MID_FADE)
        text = inside_text(lines)
        self.assertNotIn(ARRANGE_WORD, text)
        self.assertNotIn(MSG_BLOCK, text)
        self.assertFalse(stage.shows_visualizer(READY_SECONDS + GROW_SECONDS + ON_CLIPS))
        self.assertTrue(stage.shows_visualizer(READY_SECONDS + GROW_SECONDS + ON_VISUALIZER))

    def test_the_clips_are_arrange_drawn_whole_at_the_frames_inside_from_its_top_left(self):
        stage = BatchStage(began=0.0, bar_length=WHOLE_BAR, alternate=True)
        stage.start_song(at=READY_SECONDS)
        now = READY_SECONDS + GROW_SECONDS + ON_CLIPS
        self.assertTrue(stage.shows_clips(now))
        inside = inside_of(frame_box(width=WIDTH, height=HEIGHT))
        clips = [Text(CLIPS_FIRST_WORD + SPACE * (inside.right - inside.left))] * (inside.bottom - inside.top + 1)
        lines = stage.screen(arrange=arrange(), width=WIDTH, height=HEIGHT, now=now, frame=None, seconds_per_beat=SECONDS_PER_BEAT, scene=0, clips=clips)
        self.assertEqual(lines[inside.top].plain[inside.left:inside.left + len(CLIPS_FIRST_WORD)], CLIPS_FIRST_WORD)

    def test_the_pulse_goes_a_lap_every_four_bars_at_the_songs_tempo_however_unevenly_frames_come(self):
        stage = BatchStage(began=0.0, bar_length=WHOLE_BAR)
        stage.start_song(at=0.0)
        now = GROW_SECONDS
        stage.move_pulse(now=now, seconds_per_beat=SECONDS_PER_BEAT, scene=None)
        moves = []
        for number in range(PULSE_FRAMES):
            before = stage.head()
            now += FRAME * (UNEVEN_LONG if number % 2 else UNEVEN_SHORT)
            stage.move_pulse(now=now, seconds_per_beat=SECONDS_PER_BEAT, scene=None)
            moves.append((stage.head() - before) % 1.0)
        settled = moves[PULSE_FRAMES // 2:]
        lap_seconds = FRAME_LAP_BARS * QUARTERS * SECONDS_PER_BEAT
        self.assertAlmostEqual(sum(settled) / len(settled), FRAME / lap_seconds, delta=FRAME / lap_seconds / 10)
        self.assertLess(max(settled) - min(settled), FRAME * (UNEVEN_LONG - UNEVEN_SHORT) / lap_seconds / 2)

    def test_without_alternating_the_visualizer_alone_fills_the_frame(self):
        stage = BatchStage(began=0.0, bar_length=WHOLE_BAR)
        for after in (ON_CLIPS, ON_VISUALIZER):
            self.assertEqual(stage.visualizer_share(READY_SECONDS + GROW_SECONDS + after), SHOWN)

    def test_after_the_end_everything_fades_to_black(self):
        stage, _ = stage_at(PLAYING)
        stage.end(at=PLAYING, seconds=1.0)
        _, lines = stage_at(PLAYING + 2.0, stage=stage)
        self.assertTrue(all(colour == BLACK for colour in colours(lines)))

    def test_the_opening_alone_cuts_to_black(self):
        stage = BatchStage(began=0.0, bar_length=WHOLE_BAR)
        stage.cut_to_black()
        lines = stage.screen(arrange=arrange(), width=WIDTH, height=HEIGHT, now=SHOWN, frame=None, seconds_per_beat=SECONDS_PER_BEAT, scene=None)
        self.assertTrue(all(line.plain.strip() == BLANK for line in lines))

    def test_fading_keeps_a_colour_and_turns_it_down(self):
        line = Text('x', style='rgb(200,100,50)')
        self.assertEqual(colours([faded(line=line, level=0.5)])[0], (100, 50, 25))
        self.assertEqual(colours([faded(line=line, level=0.0)])[0], BLACK)


if __name__ == '__main__':
    unittest.main()
