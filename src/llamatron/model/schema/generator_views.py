# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""How a generator plugin describes its page: the inside of its tab, columns of settings under headings, each setting named by
the kind of field that edits it. A plugin's view.py holds one GeneratorView, and the tracker draws any plugin's page from it, so
that a plugin's page needs no code outside its folder. The descriptions hold only names, words and values; what draws them is
the tracker's."""

from typing import NamedTuple


class ChoiceView(NamedTuple):
    """A setting chosen from a list of values: the setting's file name, its label, the values in their order, the value it takes
    when the file leaves it out, and each value's name where the value is not a word to show as it is."""

    setting: str
    label: str
    choices: tuple
    default: object
    names: object = None


class NumberView(NamedTuple):
    """A whole number of the generator, stepped between the limits its setting's description holds, blank until given: the
    setting's file name and its label."""

    setting: str
    label: str


class ShapeView(NamedTuple):
    """One shape over time, a Density, a Swell or an Articulate: a section headed by the shape's name holding its start, end, over
    and then, each named with the shape in front, like density_start."""

    shape: str


class RestartView(NamedTuple):
    """The generator's Restart: when it starts over, every clip, on new scene or whole song."""


class ColumnView(NamedTuple):
    """A column of a generator's tab: its heading, or None for a column without one, and its settings from the top."""

    heading: object
    settings: tuple


class GeneratorView(NamedTuple):
    """A generator's tab, or its page: its columns from the left, and the help its page's F1 shows."""

    columns: tuple
    help: str
