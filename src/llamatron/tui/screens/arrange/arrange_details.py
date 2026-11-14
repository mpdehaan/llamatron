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
"""What Arrange shows in its details view, the user's design: D shows, under each bar, the details that are cluttery while performing but needed to understand how a song is put together.

Every detail is a line of its own under the bar of what holds it, a scene, a clip, or a track's
name in the header, and shows only when it isn't the default. Chains come first, each by its name
in parentheses with its generators under it, in the order they run, in green; then the rest,
each a word and a colon, like scale: for a scale that differs from the song's, and a clip's
morph and direction spelled out. A column widens to its longest line, a
detail cut at DETAIL_WIDTH and a clip's name never, and a scene's row grows to its tallest cell.

The layout is worked out once for each change to the set (Document.remembered), so moving the
cursor costs nothing.
"""

from typing import NamedTuple

from llamatron.composition.defaults import DEFAULT_REPEAT
from llamatron.composition.file_format import SHAPES, Section
from llamatron.strings.labels import MSG_FOLLOW_ACTION_NAMES, MSG_STRUM_WORDS
from llamatron.strings.marks import (
    MSG_CLIP_WITH_MARKS, MSG_DETAILS_ADVANCE, MSG_DETAILS_ADD_CHAIN, MSG_DETAILS_CHAIN, MSG_DETAILS_DIRECTION, MSG_DETAILS_DIRECTION_NAMES, MSG_DETAILS_EUCLID, MSG_DETAILS_GRAB,
    MSG_DETAILS_GROOVE, MSG_DETAILS_INSTRUMENT, MSG_DETAILS_LIST_SEPARATOR, MSG_DETAILS_MARKS_SEPARATOR, MSG_DETAILS_MORPH, MSG_DETAILS_MUTED,
    MSG_DETAILS_NO_GROOVE, MSG_DETAILS_RESET, MSG_DETAILS_SCALE, MSG_DETAILS_SHAPE, MSG_DETAILS_SHAPE_NAMES, MSG_DETAILS_STRUM, MSG_DETAILS_TEMPO,
    MSG_DETAILS_STOCK, MSG_DETAILS_TEMPO_RAMP, MSG_DETAILS_TRANSPOSE, MSG_LOOP_MARK, MSG_REPEAT_MARK,
)
from llamatron.tui import themes
from llamatron.tui.drawing import Style, fit

# The widest a detail line is drawn, the user's choice: a longer one is cut with an ellipsis. A clip's name is never cut.
DETAIL_WIDTH = 24
# The key the layout is remembered under.
DETAILS_LAYOUT = 'arrange details layout'
NO_TRANSPOSE = 0


# What the + line under a cell's chains names, which Enter answers by asking for a chain to add.
ADD_CHAIN = 'add chain'


class DetailLine(NamedTuple):
    """One line of details: its text, cut to DETAIL_WIDTH, its style, in its kind's theme colour for a line naming a thing, and what it names that Enter opens, a Target, or None for a line that names nothing with a page of its own."""

    text: str
    style: str
    target: object


class Target(NamedTuple):
    """What a line of details names: a section of the set, or a generator's kind, and the name of the item; for a chain, its
    place in the cell's list of chains, which removing it needs, since a chain can be listed twice; ADD_CHAIN for the + line."""

    kind: str
    name: str
    place: int = None


class DetailsLayout(NamedTuple):
    """The details of the current song and the room they need: each track's details and its column's width, each scene's details, each clip's, and how many lines each scene's row and the header need beyond their usual ones."""

    track_details: list
    track_widths: list
    scene_details: list
    clip_details: dict
    clip_names: dict
    scene_extra_lines: list
    header_extra_lines: int
    cell_widths: dict


# What a cell of Arrange is called when Tab opens it alone: a track's name, a scene's name or a clip.
TRACK_CELL = 'track'
SCENE_CELL = 'scene'
CLIP_CELL = 'clip'


def track_cell(name):
    return (TRACK_CELL, name)


def scene_cell(index):
    return (SCENE_CELL, index)


def clip_cell(*, index, track):
    return (CLIP_CELL, index, track)


def detailed_clip_text(clip_slot, *, repeats_left=None):
    """Return what a clip shows on its name line in the details view: its name, never cut, then its loop or repeat mark; its morph and its direction are lines of their own."""
    marks = []
    if clip_slot.loops():
        marks.append(MSG_LOOP_MARK)
    if clip_slot.get_repeat() > DEFAULT_REPEAT:
        marks.append(MSG_REPEAT_MARK.format(repeat=clip_slot.get_repeat() if repeats_left is None else repeats_left))
    if not marks:
        return clip_slot.get_display_name()
    return MSG_CLIP_WITH_MARKS.format(name=clip_slot.get_display_name(), marks=MSG_DETAILS_MARKS_SEPARATOR.join(marks))


def detail(text, *, style=Style.PLAIN, target=None):
    """Return a line of details, cut to DETAIL_WIDTH, naming a Target that Enter opens, or nothing; a line naming a thing is drawn in the colour of its kind's pages, the user's rule."""
    colour = themes.target_theme(target.kind) if target else None
    if colour is not None:
        style = themes.text_style(colour)
    return DetailLine(text=fit(text=text, width=DETAIL_WIDTH).rstrip() if len(text) > DETAIL_WIDTH else text, style=style, target=target)


def chain_lines(*, song, names):
    """Return a line for each chain the cell runs, chain: name, in the order they run, in the chains' theme colour, then the +
    line that adds one, the user's design: a cell holds chains, and a chain's generators are seen on the chain's own page."""
    lines = [detail(MSG_DETAILS_CHAIN.format(name=name), target=Target(kind=Section.CHAINS, name=name, place=place)) for place, name in enumerate(names)]
    return lines + [detail(MSG_DETAILS_ADD_CHAIN, style=Style.DIM, target=Target(kind=ADD_CHAIN, name=None))]


def shape_lines(owner):
    """Return a line for each shape, Density, Swell or Articulate, that a scene or a clip sets."""
    lines = []
    for shape in SHAPES:
        values = owner.get_shape(shape)
        if values is not None:
            lines.append(detail(MSG_DETAILS_SHAPE.format(shape=MSG_DETAILS_SHAPE_NAMES[shape], start=values.start, end=values.end)))
    return lines


def groove_lines(choice):
    """Return the line of a scene's or a track's groove choice, none when it takes the song's."""
    if choice is None:
        return []
    if choice is False:
        return [detail(MSG_DETAILS_NO_GROOVE)]
    return [detail(MSG_DETAILS_GROOVE.format(name=choice), target=Target(kind=Section.GROOVES, name=choice))]


def strum_lines(strum):
    """Return the line of a strum set on a clip or a track."""
    if strum is None:
        return []
    return [detail(MSG_DETAILS_STRUM.format(direction=MSG_STRUM_WORDS.get(strum.direction, strum.direction)))]


def scale_lines(*, song, name):
    """Return the line of a scene's or a clip's own scale, only where it differs from the song's."""
    if name is None or name == song.get_scale_name():
        return []
    return [detail(MSG_DETAILS_SCALE.format(name=name), target=Target(kind=Section.SCALES, name=name))]


def clip_details(*, setlist, song, clip_slot):
    """Return a clip's lines of details: its chains, its own scale, its morph, its direction, its grab, its Advance when it isn't the set's default, its strum and its shapes."""
    lines = chain_lines(song=song, names=clip_slot.get_chain_names())
    lines += scale_lines(song=song, name=clip_slot.get_scale_name())
    if clip_slot.get_morph_target():
        lines.append(detail(MSG_DETAILS_MORPH.format(pattern=clip_slot.get_morph_target())))
    if clip_slot.get_direction() in MSG_DETAILS_DIRECTION_NAMES:
        lines.append(detail(MSG_DETAILS_DIRECTION.format(direction=MSG_DETAILS_DIRECTION_NAMES[clip_slot.get_direction()])))
    if clip_slot.get_grab_track():
        lines.append(detail(MSG_DETAILS_GRAB.format(track=clip_slot.get_grab_track())))
    written = clip_slot.get_written_follow_action()
    if written is not None and written != setlist.get_default_follow_action():
        lines.append(detail(MSG_DETAILS_ADVANCE.format(action=MSG_FOLLOW_ACTION_NAMES[written])))
    lines += strum_lines(clip_slot.get_strum())
    return lines + shape_lines(clip_slot)


def scene_details(*, song, scene):
    """Return a scene's lines of details: its chains, its scale, its tempo or tempo ramp, its groove, the registers it resets and its shapes."""
    lines = chain_lines(song=song, names=scene.get_chain_names())
    lines += scale_lines(song=song, name=scene.get_scale_name())
    if scene.get_tempo_setting() is not None:
        lines.append(detail(MSG_DETAILS_TEMPO.format(tempo=scene.get_tempo_setting())))
    elif scene.get_tempo_start() is not None:
        lines.append(detail(MSG_DETAILS_TEMPO_RAMP.format(start=scene.get_tempo_start(), end=scene.get_tempo_end())))
    lines += groove_lines(scene.get_groove_choice())
    if scene.get_reset_names():
        lines.append(detail(MSG_DETAILS_RESET.format(registers=MSG_DETAILS_LIST_SEPARATOR.join(scene.get_reset_names()))))
    return lines + shape_lines(scene)


def track_details(*, song, track):
    """Return a track's lines of details: its chains, its instrument, its transpose, its groove, its Euclidean mask, its strum and whether it's muted."""
    lines = chain_lines(song=song, names=track.get_chain_names())
    if track.get_instrument_name():
        lines.append(detail(MSG_DETAILS_INSTRUMENT.format(name=track.get_instrument_name()), target=Target(kind=Section.INSTRUMENTS, name=track.get_instrument_name())))
    if track.get_transpose() != NO_TRANSPOSE:
        lines.append(detail(MSG_DETAILS_TRANSPOSE.format(amount=track.get_transpose())))
    lines += groove_lines(track.get_groove_choice())
    euclid = track.get_euclid()
    if euclid is not None:
        lines.append(detail(MSG_DETAILS_EUCLID.format(hits=euclid.hits, steps=euclid.steps)))
    lines += strum_lines(track.get_strum())
    if track.is_muted():
        lines.append(detail(MSG_DETAILS_MUTED))
    return lines


def or_stock(lines):
    """Return a cell's lines of details, with the one word stock, in red, the user's design, above the + of a cell with nothing else."""
    if all(line.target is not None and line.target.kind == ADD_CHAIN for line in lines):
        return [detail(MSG_DETAILS_STOCK, style=Style.DETAILS_STOCK), *lines]
    return lines


def details_layout(*, document, least_width, name_room, detail_room, track_name_room):
    """Return the current song's details and the room they need, each column at least least_width, wide enough for each clip's name and name_room more, each detail and detail_room more, and the track's name and track_name_room more."""
    setlist = document.setlist()
    song = document.song()
    names = document.track_names()
    scenes = song.get_scenes()
    tracks = [song.get_track(name) for name in names]
    in_tracks = [or_stock(track_details(song=song, track=track)) for track in tracks]
    in_scenes = [or_stock(scene_details(song=song, scene=scene)) for scene in scenes]
    in_clips = {}
    clip_names = {}
    cells = {}
    for name, lines in zip(names, in_tracks):
        cells[track_cell(name)] = max([least_width, min(len(name), DETAIL_WIDTH) + track_name_room] + [len(line.text) + detail_room for line in lines])
    widths = [cells[track_cell(name)] for name in names]
    extra = []
    for index, scene in enumerate(scenes):
        tallest = len(in_scenes[index])
        for place, name in enumerate(names):
            clip_slot = scene.get_clip_slot(name)
            if clip_slot is None:
                continue
            lines = or_stock(clip_details(setlist=setlist, song=song, clip_slot=clip_slot))
            in_clips[(index, name)] = lines
            clip_names[(index, name)] = detailed_clip_text(clip_slot)
            tallest = max(tallest, len(lines))
            cells[clip_cell(index=index, track=name)] = max([least_width, len(clip_names[(index, name)]) + name_room] + [len(line.text) + detail_room for line in lines])
            widths[place] = max(widths[place], cells[clip_cell(index=index, track=name)])
        extra.append(tallest)
    header = max([len(lines) for lines in in_tracks] + [0])
    return DetailsLayout(track_details=in_tracks, track_widths=widths, scene_details=in_scenes, clip_details=in_clips, clip_names=clip_names,
                         scene_extra_lines=extra, header_extra_lines=header, cell_widths=cells)
