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
"""Draws the Arrange page: the track names across the top, a scene on each row with its clips beside it, and the frame around what the cursor is on.

The grid is laid out on Canvas lines, three for the header, three for each scene and three after
the last, and the frame is drawn over them last. The track names and the scene column stay in
place while the clips scroll. A bar under each scene shows its length against the longest
scene's, and one under each clip its length against its scene's. The page keeps the cursor and
how far the grid has scrolled, and this draws from them, as the pattern editor's drawings do
from the editor.
"""

from llamatron.composition.defaults import DEFAULT_REPEAT
from llamatron.strings.legends import What
from llamatron.strings.marks import (
    MSG_ADD_ROW_MARK, MSG_CLIP_WITH_MARKS, MSG_DIRECTION_MARK, MSG_GRAB_MARK, MSG_LAUNCH_APART_MARK, MSG_LOOP_MARK, MSG_MORPH_MARK, MSG_PLAY_MARK, MSG_REPEAT_MARK,
    MSG_PICKED_CLOSE, MSG_PICKED_OPEN, MSG_SCENE_ROW, MSG_SONG_BUTTON, MSG_SOUNDING_MARK, MSG_STOP_MARK,
)
from llamatron.tui.components.frame import Frame
from llamatron.tui.components.length_bar import LengthBar
from rich.text import Text

from llamatron.tui.drawing import laid_over, padded, Box, Canvas, fit, NOTHING, SPACE, Style
from llamatron.tui.screens.arrange_details import CLIP_CELL, DETAIL_WIDTH, DETAILS_LAYOUT, TRACK_CELL, clip_cell, detailed_clip_text, details_layout, scene_cell, track_cell
from llamatron.tui.screens.shared import scene_name
from llamatron.tui.text import clock

SCENE_WIDTH = 24
CELL_WIDTH = 13
# A scene's label and its bar leave the first column and the last for a frame's sides.
SCENE_LABEL_COLUMN = 1
SCENE_LABEL_WIDTH = SCENE_WIDTH - 2
SCENE_BAR_COLUMN = 3
SCENE_BAR = LengthBar(width=SCENE_WIDTH - SCENE_BAR_COLUMN - 1, hatched=True)
CLIP_BAR = LengthBar(width=CELL_WIDTH - 2, hatched=False)
# While Real Time is on, a play button sits before each clip's bar, which gives up a column to it, and before each scene's bar, which has the room.
PLAY_BUTTON_WIDTH = 2
CLIP_BAR_WITH_BUTTON = LengthBar(width=CELL_WIDTH - 2 - PLAY_BUTTON_WIDTH, hatched=False)
# The room a track's name leaves for the sounding light after it while Real Time is on.
SOUNDING_MARK_WIDTH = 2
# The lines above the scenes (room for a frame's top, the track names and the rule), each scene's (a spacer, the name and the bar)
# and the ones after them (a spacer, the + row and room for a frame's bottom).
HEADER_LINES = 3
# Where the clip area starts, the first column past the scene names' divider, which the visualizer fills, and how many lines up from its bottom a mode's name shows.
CLIP_AREA_LEFT = SCENE_WIDTH + 1
NAME_ROWS_UP = 2
SCENE_LINES = 3
FOOTER_LINES = 3
# How tall a frame's inside is: one line around a track's name or the + row, and a scene's lines but the spacer around a scene or a clip.
NAME_LINES = 1
# In the details view, the room a column keeps beside its text: a space before a clip's name and one after; the indent of a detail under
# its bar and one after; and a space before a track's name, the sounding light and one after. And where each kind of line is written.
NAME_ROOM = 2
DETAIL_ROOM = 2 + PLAY_BUTTON_WIDTH
TRACK_NAME_ROOM = 2 + SOUNDING_MARK_WIDTH
DETAIL_INDENT = 1 + PLAY_BUTTON_WIDTH
TRACK_DETAIL_INDENT = 1
# The lines of a scene before its details: the spacer, the name and the bar.
FIRST_DETAIL_LINE = 3
# How long a scene's detail may be under its bar, leaving room for the brackets of a pick before the scene column's divider.
SCENE_DETAIL_ROOM = SCENE_WIDTH - SCENE_BAR_COLUMN - 2


def clip_text(clip_slot, *, repeats_left=None):
    """Return what a clip shows on the grid: its name, or its pattern's, with marks for anything beyond its pattern. While the clip plays, its repeat mark counts down the repeats left."""
    name = clip_slot.get_display_name()
    marks = NOTHING
    if clip_slot.get_direction():
        marks += MSG_DIRECTION_MARK
    if clip_slot.get_grab_track():
        marks += MSG_GRAB_MARK
    if clip_slot.get_morph_target():
        marks += MSG_MORPH_MARK
    if clip_slot.loops():
        marks += MSG_LOOP_MARK
    if clip_slot.get_repeat() > DEFAULT_REPEAT:
        marks += MSG_REPEAT_MARK.format(repeat=clip_slot.get_repeat() if repeats_left is None else repeats_left)
    if marks:
        return MSG_CLIP_WITH_MARKS.format(name=fit(text=name, width=max(CELL_WIDTH - len(marks) - 2, 1)).rstrip(), marks=marks)
    return name


class ArrangeDrawing:
    """Draws an ArrangePage's grid from the page's cursor, how far it has scrolled, and the current song."""

    __slots__ = ('_page',)

    def __init__(self, page):
        self._page = page

    def shows_details(self):
        """Return whether the page shows its details view, the user's design, which widens the columns and lengthens the rows to fit the details under each bar."""
        return self._page.shows_details()

    def layout(self):
        """Return the current song's details and the room they need, worked out once for each change to the set."""
        document = self._page.document()
        return document.remembered(key=DETAILS_LAYOUT, on=(document,), compute=lambda: details_layout(
            document=document, least_width=CELL_WIDTH, name_room=NAME_ROOM, detail_room=DETAIL_ROOM, track_name_room=TRACK_NAME_ROOM))

    def opened_cell(self):
        """Return the cell Tab opened in the usual view, which alone shows its details, or None."""
        return self._page.opened_cell

    def widened(self):
        """Return whether any details show, every cell's in the details view or one cell's that Tab opened, so that columns and rows take their own sizes."""
        return self.shows_details() or self.opened_cell() is not None

    def cell_open(self, cell):
        """Return whether a cell shows its details: every cell in the details view, and in the usual view the one Tab opened."""
        return self.shows_details() or cell == self.opened_cell()

    def details_at_cursor(self):
        """Return the lines of details of what the cursor is on, a track's name, a scene's or a clip, whether or not they show, or none elsewhere."""
        page = self._page
        layout = self.layout()
        if page.on_track_name():
            return layout.track_details[page.track_place()]
        if page.on_plus_row() or page.on_header():
            return []
        if page.on_scene_name():
            return layout.scene_details[page.row]
        return layout.clip_details.get((page.row, page.track()), [])

    def draw_details(self, lines, *, details, column, here, room=None):
        """Draw lines of details from a column, each cut to room when given, the one Tab picked in brackets when here is true, the cell being the cursor's."""
        picked = self._page.picked_line() if here else None
        for place, (line, detail) in enumerate(zip(lines, details)):
            text = detail.text if room is None or len(detail.text) <= room else fit(text=detail.text, width=room).rstrip()
            line.write(column=column, text=text, style=detail.style)
            if place == picked:
                line.write(column=column - 1, text=MSG_PICKED_OPEN, style=Style.BOLD)
                line.write(column=column + len(text), text=MSG_PICKED_CLOSE, style=Style.BOLD)

    def track_width(self, place):
        """Return how wide a track's column is between its dividers: CELL_WIDTH, or in the details view as wide as its details need, and CELL_WIDTH for the + after the last track."""
        tracks = self._page.tracks()
        if not self.widened() or place >= len(tracks):
            return CELL_WIDTH
        if self.shows_details():
            return self.layout().track_widths[place]
        opened = self.opened_cell()
        if opened in (track_cell(tracks[place]),) or (opened[0] == CLIP_CELL and opened[2] == tracks[place]):
            return self.layout().cell_widths.get(opened, CELL_WIDTH)
        return CELL_WIDTH

    def header_lines(self):
        """Return how many lines the header takes: HEADER_LINES, and in the details view as many more as the track with the most details needs."""
        if self.shows_details():
            return HEADER_LINES + self.layout().header_extra_lines
        opened = self.opened_cell()
        if opened is not None and opened[0] == TRACK_CELL:
            return HEADER_LINES + len(self.layout().track_details[self._page.tracks().index(opened[1])])
        return HEADER_LINES

    def scene_lines(self, index):
        """Return how many lines a scene's row takes: SCENE_LINES, and in the details view as many more as its tallest cell's details need."""
        if self.shows_details():
            return SCENE_LINES + self.layout().scene_extra_lines[index]
        opened = self.opened_cell()
        if opened == scene_cell(index):
            return SCENE_LINES + len(self.layout().scene_details[index])
        if opened is not None and opened[0] == CLIP_CELL and opened[1] == index:
            return SCENE_LINES + len(self.layout().clip_details.get((index, opened[2]), []))
        return SCENE_LINES

    def visible_tracks(self, width):
        """Return the first and last visible places among the track columns and the + after them, scrolling to the cursor."""
        if self.widened():
            return self.visible_wide_tracks(width)
        count = max((width - SCENE_WIDTH - 2) // (CELL_WIDTH + 1), 1)
        total = len(self._page.tracks()) + 1
        if self._page.in_a_track_column():
            place = self._page.track_place()
            if place < self._page.left:
                self._page.left = place
            elif place >= self._page.left + count:
                self._page.left = place - count + 1
        self._page.left = max(min(self._page.left, max(total - count, 0)), 0)
        return self._page.left, min(self._page.left + count, total)

    def visible_wide_tracks(self, width):
        """Return the first and last visible places in the details view, where each column is as wide as its details need, scrolling to the cursor."""
        room = width - SCENE_WIDTH - (1 if self.shows_details() else 2)
        total = len(self._page.tracks()) + 1

        def fits(first, place):
            return sum(self.track_width(column) + 1 for column in range(first, place + 1)) <= room

        if self._page.in_a_track_column():
            place = self._page.track_place()
            self._page.left = min(self._page.left, place)
            while self._page.left < place and not fits(self._page.left, place):
                self._page.left += 1
        self._page.left = max(min(self._page.left, total - 1), 0)
        while self._page.left > 0 and fits(self._page.left - 1, total - 1):
            self._page.left -= 1
        last = self._page.left + 1
        while last < total and fits(self._page.left, last):
            last += 1
        return self._page.left, last

    def visible_scenes(self, height):
        """Return the range of scene indexes that fit, scrolling to the cursor, with the header and the + row always shown."""
        if self.widened():
            return self.visible_tall_scenes(height)
        room = max((height - HEADER_LINES - FOOTER_LINES) // SCENE_LINES, 1)
        if self._page.row < self._page.top:
            self._page.top = max(self._page.row, 0)
        elif self._page.row >= self._page.top + room:
            self._page.top = self._page.row - room + 1
        return range(self._page.top, min(self._page.top + room, len(self._page.scenes())))

    def visible_tall_scenes(self, height):
        """Return the range of scene indexes that fit in the details view, where each row is as tall as its details need, scrolling to the cursor."""
        room = height - self.header_lines() - FOOTER_LINES
        count = len(self._page.scenes())

        def fits(first, index):
            return sum(self.scene_lines(row) for row in range(first, index + 1)) <= room

        wanted = min(max(self._page.row, 0), count - 1)
        self._page.top = max(min(self._page.top, wanted), 0)
        while self._page.top < wanted and not fits(self._page.top, wanted):
            self._page.top += 1
        last = self._page.top + 1
        while last < count and fits(self._page.top, last):
            last += 1
        return range(self._page.top, min(last, count))

    def cell_column(self, place):
        """Return the column of the divider before a track's clip slot, where a frame's left edge goes: in the details view the first track's is the scene column's double divider, so that every column lies the same way between its dividers."""
        if self.shows_details():
            return SCENE_WIDTH + sum(self.track_width(column) + 1 for column in range(self._page.left, place))
        return SCENE_WIDTH + 1 + sum(self.track_width(column) + 1 for column in range(self._page.left, place))

    def draw_dividers(self, line, *, first, last):
        """Draw the scene column's divider down a line, and in the details view a double one and one between every two tracks, in blue, so that the view shows itself."""
        if not self.shows_details():
            line.write(column=SCENE_WIDTH, text=Box.BAR, style=Style.DIM)
            return
        line.write(column=SCENE_WIDTH, text=Box.DOUBLE_BAR, style=Style.DETAILS_DIVIDER)
        for place in range(first + 1, last + 1):
            line.write(column=self.cell_column(place), text=Box.BAR, style=Style.DETAILS_DIVIDER)

    def draw_rule(self, line, *, first, last):
        """Draw the rule under the track names, crossing the scene column's divider, and in the details view every divider, in blue."""
        if not self.shows_details():
            line.write(column=0, text=Box.RULE * SCENE_WIDTH + Box.CROSS + Box.RULE * ((last - first) * (CELL_WIDTH + 1) + 1), style=Style.DIM)
            return
        line.write(column=0, text=Box.RULE * (self.cell_column(last) + 1), style=Style.DIM)
        line.write(column=SCENE_WIDTH, text=Box.DOUBLE_CROSS, style=Style.DETAILS_DIVIDER)
        for place in range(first + 1, last + 1):
            line.write(column=self.cell_column(place), text=Box.CROSS, style=Style.DETAILS_DIVIDER)

    def scene_label(self, index):
        scene = self._page.scenes()[index]
        repeat = scene.get_repeat()
        name = scene_name(scene=scene, index=index)
        if repeat > DEFAULT_REPEAT:
            name += SPACE + MSG_REPEAT_MARK.format(repeat=repeat)
        if not scene.launches_together():
            name += SPACE + MSG_LAUNCH_APART_MARK
        length = clock(self._page.document().lengths().scene_seconds(index))
        return fit(text=MSG_SCENE_ROW.format(number=index + 1, name=name), width=SCENE_LABEL_WIDTH - len(length) - 1) + length

    def draw_header(self, lines, *, first, last):
        """Draw the row of track names, with the + after the last one, over the corner, and the rule under them.

        The corner is blank, since the crumbs say where you are, until Real Time is on: then it is
        the song's play button, which Space presses, and a light after a track's name says a note
        sounds on it.
        """
        tracks = self._page.tracks()
        names = lines[1]
        for line in lines[1:-1]:
            self.draw_dividers(line, first=first, last=last)
        transport = self._page.transport()
        if self._page.real_time_on():
            playing = transport.is_playing()
            names.write(column=SCENE_LABEL_COLUMN, text=MSG_SONG_BUTTON.format(mark=MSG_STOP_MARK if playing else MSG_PLAY_MARK), style=Style.PLAYING if playing else Style.DIM)
        for place in range(first, last):
            column = self.cell_column(place) + 1
            width = self.track_width(place)
            if place < len(tracks):
                shown = self.shown_track_name(tracks[place])
                if self._page.real_time_on():
                    names.write(column=column, text=fit(text=SPACE + shown, width=width - SOUNDING_MARK_WIDTH), style=Style.BOLD)
                    if transport.is_track_sounding(tracks[place]):
                        names.write(column=column + width - 1, text=MSG_SOUNDING_MARK, style=Style.SOUNDING)
                else:
                    names.write(column=column, text=fit(text=SPACE + shown, width=width), style=Style.BOLD)
                if self.cell_open(track_cell(tracks[place])):
                    here = self._page.on_track_name() and self._page.track_place() == place
                    self.draw_details(lines[2:-1], details=self.layout().track_details[place], column=column + TRACK_DETAIL_INDENT, here=here)
            else:
                names.write(column=column, text=MSG_ADD_ROW_MARK.center(width), style=Style.DIM)
        if last < len(tracks) + 1:
            names.write(column=self.cell_column(last) + 1, text=Box.MORE, style=Style.DIM)
        self.draw_rule(lines[-1], first=first, last=last)

    def shown_track_name(self, name):
        """Return a track's name as the header shows it: whole, cut to its column, or in the details view cut at DETAIL_WIDTH, its column widened to fit."""
        if self.widened() and len(name) > DETAIL_WIDTH:
            return fit(text=name, width=DETAIL_WIDTH).rstrip()
        return name

    def draw_scene(self, lines, *, index, first, last, clips=True):
        """Draw a scene's three lines: the spacer above it, its name with its time, and its length bar, with its clips beside them unless clips is false."""
        lengths = self._page.document().lengths()
        tracks = self._page.tracks()
        for line in lines:
            self.draw_dividers(line, first=first, last=last)
        lines[1].write(column=SCENE_LABEL_COLUMN, text=self.scene_label(index), style=Style.BOLD)
        layout = self.layout() if self.widened() else None
        if self.cell_open(scene_cell(index)):
            here = self._page.on_scene_name() and not self._page.on_plus_row() and self._page.row == index
            self.draw_details(lines[FIRST_DETAIL_LINE:], details=layout.scene_details[index], column=SCENE_BAR_COLUMN, here=here, room=SCENE_DETAIL_ROOM)
        transport = self._page.transport()
        real_time = self._page.real_time_on()
        played = transport.scene_elapsed(index) if real_time else None
        lines[2].write(column=SCENE_BAR_COLUMN, text=SCENE_BAR.draw(amount=lengths.scene_seconds(index), total=lengths.longest_scene_seconds(), played=played))
        if real_time:
            self.play_button(lines[2], column=SCENE_LABEL_COLUMN, playing=index in transport.playing_scenes())
        for place in range(first, min(last, len(tracks)) if clips else first):
            column = self.cell_column(place) + 1
            width = self.track_width(place)
            details = self.cell_open(clip_cell(index=index, track=tracks[place]))
            named = detailed_clip_text if details else clip_text
            clip_slot = self._page.document().clip_slot(index=index, track=tracks[place])
            if clip_slot is None:
                if index == self._page.row and self._page.on_clip_slot() and self._page.track_place() == place:
                    lines[1].write(column=column, text=MSG_ADD_ROW_MARK.center(width))
                    lines[2].write(column=column, text=What.ADD.center(width))
                continue
            if real_time:
                playing = transport.is_clip_playing(index=index, track=tracks[place])
                repeats_left = transport.repeats_left(index=index, track=tracks[place]) if playing else None
                clip_played = transport.clip_elapsed(index=index, track=tracks[place]) if playing else None
                lines[1].write(column=column, text=fit(text=SPACE + named(clip_slot, repeats_left=repeats_left), width=width))
                self.play_button(lines[2], column=column, playing=playing)
                bar = CLIP_BAR_WITH_BUTTON if width == CELL_WIDTH else LengthBar(width=width - 2 - PLAY_BUTTON_WIDTH, hatched=False)
                lines[2].write(column=column + 1 + PLAY_BUTTON_WIDTH,
                               text=self.clip_bar(bar, lengths=lengths, clip_slot=clip_slot, index=index, track=tracks[place], played=clip_played))
            else:
                lines[1].write(column=column, text=fit(text=SPACE + named(clip_slot), width=width))
                bar = CLIP_BAR if width == CELL_WIDTH else LengthBar(width=width - 2, hatched=False)
                lines[2].write(column=column + 1, text=self.clip_bar(bar, lengths=lengths, clip_slot=clip_slot, index=index, track=tracks[place]))
            if details:
                indent = DETAIL_INDENT if real_time else 1
                here = self._page.on_clip_slot() and self._page.row == index and self._page.track_place() == place
                self.draw_details(lines[FIRST_DETAIL_LINE:], details=layout.clip_details.get((index, tracks[place]), []), column=column + indent, here=here)

    @staticmethod
    def clip_bar(bar, *, lengths, clip_slot, index, track, played=None):
        """Return a clip's length bar: full for a looping clip, and otherwise its seconds against its scene's first play.

        With played, the seconds the clip has played so far, the bar is a read head like the
        scene's, filling from the left as the clip plays (the user's idea of 2026-11-10): a
        looping clip's fills over one play of its scene and starts over.
        """
        total = lengths.scene_play_seconds(index)
        if clip_slot.loops():
            return bar.full() if played is None else bar.draw(amount=total, total=total, played=played)
        return bar.draw(amount=lengths.clip_seconds(index=index, track=track), total=total, played=played)

    @staticmethod
    def play_button(line, *, column, playing):
        """Draw a play button, dim, or the stop mark in the playing colour while the thing plays, the user's one use of colour."""
        if playing:
            line.write(column=column, text=MSG_STOP_MARK, style=Style.PLAYING)
        else:
            line.write(column=column, text=MSG_PLAY_MARK, style=Style.DIM)

    def draw_footer(self, lines, *, at_end, first, last):
        """Draw the spacer under the last scene and the + row where a scene is added, when the end of the list is on screen."""
        for line in lines:
            self.draw_dividers(line, first=first, last=last)
        if at_end:
            lines[1].write(column=SCENE_BAR_COLUMN, text=MSG_ADD_ROW_MARK, style=Style.DIM)

    def frame_place(self, *, shown, first, last):
        """Return the frame around what the cursor is on, the line its top edge is on and how many lines it holds, or None when the cursor is off screen."""
        names = self.header_lines() - 2
        if self._page.on_corner():
            return Frame(left=0, right=SCENE_WIDTH - 1), 0, names
        if self._page.on_header():
            place = self._page.track_place()
            if first <= place < last:
                return Frame(left=self.cell_column(place), right=self.cell_column(place) + self.track_width(place) + 1), 0, names
            return None
        scenes_height = sum(self.scene_lines(index) for index in shown)
        if self._page.on_plus_row():
            return Frame(left=0, right=SCENE_WIDTH - 1), self.header_lines() + scenes_height, NAME_LINES
        if self._page.row not in shown:
            return None
        line = self.header_lines() + sum(self.scene_lines(index) for index in range(shown.start, self._page.row))
        inside = self.scene_lines(self._page.row) - 1
        if self._page.on_scene_name():
            return Frame(left=0, right=SCENE_WIDTH - 1), line, inside
        place = self._page.track_place()
        column = self.cell_column(place)
        return Frame(left=column, right=column + self.track_width(place) + 1), line, inside

    def visualized_body(self, *, width, height, mode, now, heard):
        """Return the page's lines with a visualizer mode in the clip area: the track names along the top and the scene names down the left as ever, and the mode's frame over everything inside them, down to the last line above the footer, with no frame for the cursor."""
        first, last = self.visible_tracks(width)
        shown = self.visible_scenes(height)
        lines = [Canvas(width) for _ in range(max(height, HEADER_LINES))]
        self.draw_header(lines[:HEADER_LINES], first=first, last=last)
        for number, index in enumerate(shown):
            start = HEADER_LINES + number * SCENE_LINES
            if start + SCENE_LINES <= len(lines):
                self.draw_scene(lines[start:start + SCENE_LINES], index=index, first=first, last=last, clips=False)
        for line in lines[HEADER_LINES:]:
            line.write(column=SCENE_WIDTH, text=Box.BAR, style=Style.DIM)
        texts = [line.text() for line in lines]
        frame = mode.frame(width=max(width - CLIP_AREA_LEFT, 0), height=len(lines) - HEADER_LINES, now=now, heard=heard)
        for row, piece in enumerate(frame):
            texts[HEADER_LINES + row] = laid_over(line=texts[HEADER_LINES + row], start=CLIP_AREA_LEFT, piece=piece)
        return texts

    @staticmethod
    def with_name(*, lines, name):
        """Return the page's lines with a visualizer mode's name laid over the clip area, in reverse video, centred NAME_ROWS_UP lines from its bottom, or as they are with no name."""
        if name is None or len(lines) <= HEADER_LINES + NAME_ROWS_UP:
            return lines
        piece = Text(padded(name), style=Style.REVERSE)
        width = max(line.cell_len for line in lines)
        row = len(lines) - 1 - NAME_ROWS_UP
        start = CLIP_AREA_LEFT + max((width - CLIP_AREA_LEFT - piece.cell_len) // 2, 0)
        named = list(lines)
        named[row] = laid_over(line=lines[row], start=start, piece=piece)
        return named

    def body(self, *, width, height):
        """Return the page's lines: the header, the scenes that fit, the footer, and the frame drawn over them last."""
        first, last = self.visible_tracks(width)
        shown = self.visible_scenes(height)
        header = self.header_lines()
        lines = [Canvas(width) for _ in range(header + sum(self.scene_lines(index) for index in shown) + FOOTER_LINES)]
        self.draw_header(lines[:header], first=first, last=last)
        start = header
        for index in shown:
            self.draw_scene(lines[start:start + self.scene_lines(index)], index=index, first=first, last=last)
            start += self.scene_lines(index)
        self.draw_footer(lines[-FOOTER_LINES:], at_end=shown.stop == len(self._page.scenes()), first=first, last=last)
        placed = self.frame_place(shown=shown, first=first, last=last)
        if placed is not None:
            # The frame's inside is as tall as what it holds: a scene's or a clip's lines but the spacer, a name's, or the + row's one.
            frame, top, inside = placed
            if self._page.picking() or self._page.moving is not None:
                frame = frame.styled(Style.DETAILS_LOCKED)
            frame.top(lines[top])
            for line in lines[top + 1:top + 1 + inside]:
                frame.sides(line)
            frame.bottom(lines[top + 1 + inside])
        return [line.text() for line in lines]
