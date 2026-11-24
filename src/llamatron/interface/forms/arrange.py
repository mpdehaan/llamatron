# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Arrange's grid, as plain nodes with nothing of how it is drawn: each line of the page is a list of nodes, each at the column
it starts, later ones laid over earlier ones, and the frame around what the cursor is on is laid over them all. The tracker
draws them (interface/tracker/renderers/arrange.py), the only code that knows how they look.

The nodes are not frozen, unlike the other forms' nodes, since Arrange makes a few hundred for every key and a frozen one was
measured at nearly twice the time to make; nothing changes a node once it is made."""

from dataclasses import dataclass, field as dataclass_field

# How a piece of text is drawn: as it is, as a name, said in passing, playing, sounding, or as a stock cell's word.
PLAIN = 'plain'
NAME = 'name'
FAINT = 'faint'
PLAYING = 'playing'
SOUNDING = 'sounding'
STOCK = 'stock'
# How the frame is drawn: around what the cursor is on, locked while a detail is picked or a thing carried, or around the
# scene that plays in a recording nobody performs.
CURSOR_FRAME = 'cursor'
LOCKED_FRAME = 'locked'
PLAYING_SCENE_FRAME = 'playing scene'


@dataclass(slots=True, kw_only=True)
class ArrangeText:
    """Text at a column, drawn as its kind says."""

    column: int
    text: str
    kind: str = PLAIN


@dataclass(slots=True, kw_only=True)
class Dividers:
    """The grid's lines down a line: the scene column's double divider at a column, and a single one at each of the others."""

    double_at: int
    columns: tuple = dataclass_field(default_factory=tuple)
    # Whether the lines are the grid's light ones, or dim, as beside a visualizer.
    faint: bool = False


@dataclass(slots=True, kw_only=True)
class ArrangeRule:
    """A grid line across a line, from the left edge to a right end, crossing the scene column's double divider and each of the
    single ones."""

    end: int
    double_at: int
    crosses: tuple = dataclass_field(default_factory=tuple)


@dataclass(slots=True, kw_only=True)
class MoreMark:
    """The mark in the last divider's place that says more tracks lie to the right."""

    column: int


@dataclass(slots=True, kw_only=True)
class PlayButton:
    """A play button at a column, or the stop mark while the thing it plays plays."""

    column: int
    playing: bool = False


@dataclass(slots=True, kw_only=True)
class DetailLine:
    """One line of a cell's details, as the details view and Scene View show it: its text, cut to the details' width, how it
    is drawn (PLAIN, FAINT or STOCK), and what it names that ENTER opens, a Target, or None. A line naming a thing is drawn in
    the colour of its kind's pages."""

    text: str
    kind: str = PLAIN
    target: object = None


@dataclass(slots=True, kw_only=True)
class Detail:
    """A line of details at a column, cut to room when given, and in brackets when it is the line Tab picked."""

    column: int
    line: DetailLine
    picked: bool = False
    room: object = None


@dataclass(slots=True, kw_only=True)
class CellFrame:
    """The double-lined frame between two columns, its top edge on a line, holding so many lines, drawn as its kind says."""

    left: int
    right: int
    top: int
    inside: int
    kind: str = CURSOR_FRAME
