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

"""What a batch video shows, moment by moment, once the title has gone: the user's design.

Arrange fades in, in grey on black, with the READY box over it and the cursor on the corner; after
READY_SECONDS the song starts, and over GROW_SECONDS the box grows out into the scene frame while
Arrange and READY fade and the visualizer fades in inside it. From then on the visualizer fills the
frame, and the frame's pulse goes round a lap every FRAME_LAP_BARS bars of the song, taking the next
of FRAME_COLOURS and turning round at each change of scene, the colour easing across rather than
snapping. When the song has ended, everything fades to black. The drawing is in
tui/components/stage_drawing.py; Arrange's page hands this its lines, the visualizer's frame and
what it hears, and the app says when the song starts and ends.
"""

from llamatron.tui.components.stage_drawing import (
    BLACK, BORDER_BLUE, black_line, blacked, border_cells, faded, frame_box, grown, inside_of, overlaid, pulse_cells, ready_box, ready_cells,
    visualizer_area, visualizer_laid_in, clips_laid_in,
)
from llamatron.tui.components.title_card import eased

# How long Arrange takes to fade in, how long READY shows before the song starts, and how long the box takes to grow into the frame.
ARRANGE_FADE_IN_SECONDS = 0.6
READY_SECONDS = 3.0
GROW_SECONDS = 1.5
# Alternating inside the frame, the user's design and the default for batch videos: the clips, then the visualizer, each
# for ALTERNATE_SECONDS, starting on the clips, each change a fade through black over ALTERNATE_FADE_SECONDS, one view
# dimming out before the other comes in, so that nothing flashes.
ALTERNATE_SECONDS = 10.0
ALTERNATE_FADE_SECONDS = 1.5
FADED_HALF = 0.5
# READY fades out over the first share of the growing.
READY_FADE_SHARE = 0.4
# The pulse: a lap of the READY box every BOX_LAP_SECONDS, and of the frame every FRAME_LAP_BARS bars; a colour change eases across over COLOUR_SECONDS.
BOX_LAP_SECONDS = 2.0
FRAME_LAP_BARS = 4
COLOUR_SECONDS = 0.5
# The pulse moves by the frames' smoothed length: how much of a change in a frame's length it takes each frame, and the longest step it takes.
STEP_SMOOTHING = 0.1
LONGEST_STEP_SECONDS = 0.2
QUARTERS_IN_A_WHOLE = 4
CLOCKWISE = 1
# The frame's colours, a scene each in turn, starting from the READY box's blue so that the pulse keeps its colour as the box grows.
FRAME_COLOURS = (BORDER_BLUE, (230, 60, 230), (240, 50, 40), (255, 190, 30), (40, 230, 80), (30, 215, 255))


class BatchStage:
    """The stage of one batch video: when it began, when the song started and ended, and the pulse."""

    __slots__ = ('_began', '_lap_beats', '_song_began', '_ended', '_end_seconds', '_black', '_head', '_direction', '_scene', '_colour',
                 '_colour_from', '_colour_since', '_last', '_step', '_alternate')

    def __init__(self, *, began, bar_length, alternate=False):
        """began is when Arrange showed, in the clock's seconds; bar_length is a bar of the song in whole notes, which the frame's lap is counted in; alternate, whether the frame alternates between the clips and the visualizer."""
        self._began = began
        self._alternate = alternate
        self._lap_beats = FRAME_LAP_BARS * float(bar_length) * QUARTERS_IN_A_WHOLE
        self._song_began = None
        self._ended = None
        self._end_seconds = None
        self._black = False
        self._head = 0.0
        self._direction = CLOCKWISE
        self._scene = None
        self._colour = 0
        self._colour_from = 0
        self._colour_since = None
        self._last = None
        self._step = None

    def head(self):
        """Return where the pulse's head is round its track, as a share of a lap."""
        return self._head

    def direction(self):
        """Return which way the pulse goes round: 1 clockwise, -1 not."""
        return self._direction

    def start_song(self, *, at):
        """The song starts now: the box begins to grow."""
        self._song_began = at

    def end(self, *, at, seconds):
        """The song has ended: everything fades to black over seconds."""
        if self._ended is None:
            self._ended = at
            self._end_seconds = max(seconds, 1e-6)

    def cut_to_black(self):
        """Show black from now on, as the opening alone ends (internal_tools/demo_splash_screen.py)."""
        self._black = True

    def is_growing_or_grown(self, now):
        return self._song_began is not None and now >= self._song_began

    def visualizer_share(self, now):
        """Return how far the frame has turned from the clips to the visualizer, from 0 to 1: always 1 without alternating, and alternating starts on the clips as the box grows."""
        if not self._alternate:
            return 1.0
        if self._song_began is None:
            return 0.0
        played = now - self._song_began - GROW_SECONDS
        if played < 0:
            return 0.0
        place = played % (2 * (ALTERNATE_SECONDS + ALTERNATE_FADE_SECONDS))
        if place < ALTERNATE_SECONDS:
            return 0.0
        place -= ALTERNATE_SECONDS
        if place < ALTERNATE_FADE_SECONDS:
            return place / ALTERNATE_FADE_SECONDS
        place -= ALTERNATE_FADE_SECONDS
        if place < ALTERNATE_SECONDS:
            return 1.0
        return 1.0 - (place - ALTERNATE_SECONDS) / ALTERNATE_FADE_SECONDS

    def shows_clips(self, now):
        """Return whether the clips can be seen in the frame now, so that Arrange is drawn again at the frame's size only then."""
        return self._alternate and self.is_growing_or_grown(now) and self.visualizer_share(now) < FADED_HALF

    def shows_visualizer(self, now):
        """Return whether the visualizer can be seen now, so that its frame is worked out only then."""
        return self.is_growing_or_grown(now) and self.visualizer_share(now) > FADED_HALF

    def grown_share(self, now):
        """Return how far the box has grown into the frame, from 0 to 1."""
        if self._song_began is None:
            return 0.0
        return min(max((now - self._song_began) / GROW_SECONDS, 0.0), 1.0)

    def colour(self, now):
        """Return the pulse's colour now, easing from the last scene's to this one's."""
        to = FRAME_COLOURS[self._colour % len(FRAME_COLOURS)]
        if self._colour_since is None:
            return to
        share = eased((now - self._colour_since) / COLOUR_SECONDS)
        start = FRAME_COLOURS[self._colour_from % len(FRAME_COLOURS)]
        return tuple(round(begin + (finish - begin) * share) for begin, finish in zip(start, to))

    def move_pulse(self, *, now, seconds_per_beat, scene):
        """Move the pulse on since the last frame: by the clock round the box, and round the frame at a speed the song's tempo sets, a lap every FRAME_LAP_BARS bars, blended as it grows; turn it round and take the next colour when the scene changes.

        It moves by the frames' smoothed length, never by the beats counted since the last frame,
        which arrive unevenly and made it jerky (the user's ask): the tempo sets its speed, and
        nothing steps it.
        """
        seconds = 0.0 if self._last is None else min(max(now - self._last, 0.0), LONGEST_STEP_SECONDS)
        self._last = now
        if self._step is None:
            self._step = seconds if seconds > 0 else None
        else:
            self._step += (seconds - self._step) * STEP_SMOOTHING
        step = self._step or 0.0
        share = self.grown_share(now)
        laps = (1.0 - share) * step / BOX_LAP_SECONDS + share * step / (seconds_per_beat * self._lap_beats)
        self._head = (self._head + self._direction * laps) % 1.0
        if scene is not None and self._song_began is not None:
            if self._scene is not None and scene != self._scene:
                self._direction = -self._direction
                self._colour_from = self._colour
                self._colour += 1
                self._colour_since = now
            self._scene = scene

    def screen(self, *, arrange, width, height, now, frame, seconds_per_beat, scene, clips=None):
        """Return the whole screen at a moment: arrange is Arrange's lines as the page draws them, frame the visualizer's lines for visualizer_area, or None before it shows, and clips Arrange drawn again at the size of the frame's inside, or None while the clips don't show."""
        if self._black:
            return [black_line(width) for _ in range(height)]
        self.move_pulse(now=now, seconds_per_beat=seconds_per_beat, scene=scene)
        share = self.grown_share(now)
        showing = eased((now - self._began) / ARRANGE_FADE_IN_SECONDS)
        ending = 1.0 if self._ended is None else 1.0 - eased((now - self._ended) / self._end_seconds)
        arrange_level = showing * (1.0 - eased(share))
        lines = []
        for number in range(height):
            line = faded(line=arrange[number], level=arrange_level) if arrange_level > 0 and number < len(arrange) else black_line(0)
            if len(line.plain) < width:
                line.append_text(black_line(width - len(line.plain)))
            lines.append(line[:width])
        rect = grown(start=ready_box(width=width, height=height), end=frame_box(width=width, height=height), share=share)
        lines = blacked(lines=lines, rect=rect)
        turned = self.visualizer_share(now)
        # A fade through black: the clips dim out over the first half of a change and the visualizer comes in over the second.
        clips_level = max(1.0 - turned / FADED_HALF, 0.0) * ending
        visualizer_level = max((turned - FADED_HALF) / FADED_HALF, 0.0) * ending
        if share > 0 and clips_level > 0 and clips is not None:
            lines = clips_laid_in(lines=lines, clips=clips, at=inside_of(frame_box(width=width, height=height)), inside=inside_of(rect), level=clips_level)
        if frame is not None and share > 0 and visualizer_level > 0:
            lines = visualizer_laid_in(lines=lines, frame_lines=frame, area=visualizer_area(width=width, height=height), inside=inside_of(rect),
                                       level=eased(share) * visualizer_level)
        cells = border_cells(rect=rect, level=showing * (1.0 - eased(share)))
        cells.update(ready_cells(rect=rect, level=showing * (1.0 - eased(share / READY_FADE_SHARE))))
        cells.update(pulse_cells(rect=rect, head=self._head, direction=self._direction, colour=self.colour(now), level=showing * ending))
        # A cell drawn black adds nothing, so it is left out.
        return overlaid(lines=lines, cells={place: cell for place, cell in cells.items() if tuple(cell[1].color.get_truecolor()) != BLACK})

