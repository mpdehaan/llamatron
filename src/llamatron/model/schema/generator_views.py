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
    """A whole number of the generator, stepped between the limits its setting's description holds: the setting's file name, its
    label, and the number it takes when the file leaves it out, or None for a number shown blank until given."""

    setting: str
    label: str
    default: object = None


class TimeView(NamedTuple):
    """How long each step of a row is, chosen from the lengths every time setting offers, the pattern's step size unless set:
    the setting's file name and its label."""

    setting: str
    label: str


class StepsView(NamedTuple):
    """A row of on-or-off steps, which ENTER opens on a page of its own: the file name of the row's setting, which of the
    generator's rows it is (the settings answer step_row(row)), its label, the name its page gives the row, and the line its page
    shows above the row, saying what a lit step does."""

    setting: str
    row: str
    label: str
    row_name: str
    note: str


class ShapeView(NamedTuple):
    """One shape over time, a Density, a Swell or an Articulate: a section headed by the shape's name holding its start, end, over
    and then, each named with the shape in front, like density_start."""

    shape: str


class RestartView(NamedTuple):
    """The generator's Restart: when it starts over, every clip, on new scene or whole song."""


class SectionView(NamedTuple):
    """A section of a generator's settings under a heading, closed until opened and saying (set) while anything inside holds a
    value: its heading and its settings from the top."""

    heading: str
    settings: tuple


class ColumnView(NamedTuple):
    """A column of a generator's tab: its heading, or None for a column without one, and its settings from the top."""

    heading: object
    settings: tuple


class GeneratorView(NamedTuple):
    """A generator's tab, or its page: its columns from the left, and the help its page's F1 shows."""

    columns: tuple
    help: str
