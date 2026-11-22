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
    label, the number it takes when the file leaves it out, or None for a number shown blank until given, how it is shown, a
    template filled with {number} or None for the number alone, and what shows for 0 where that has a word of its own."""

    setting: str
    label: str
    default: object = None
    shown: object = None
    zero_shown: object = None


class ToggleView(NamedTuple):
    """A setting that is on or off: the setting's file name, its label, whether it is on when the file leaves it out, and where
    that differs by the generator's mode, a dictionary of it by mode."""

    setting: str
    label: str
    default: bool = False
    by_mode: object = None


class OctaveView(NamedTuple):
    """One end of a range of octaves, shown in the set's octave labels and kept from crossing the other end, which the settings'
    limits_of answers: the setting's file name, its label, and the octave it takes when the file leaves it out."""

    setting: str
    label: str
    default: int


class TrackView(NamedTuple):
    """A track of the current song the generator names, chosen from the song's tracks, (none) first: the setting's file name and
    its label. A rename of the track follows."""

    setting: str
    label: str


class ProgressionView(NamedTuple):
    """A progression's chords, shown as numerals in the song's scale, which ENTER opens in the chord editor: its label. The
    settings answer the progression's rows (get_chords and the rest)."""

    label: str


class GuitarBarView(NamedTuple):
    """A Guitarify's bar of strokes, shown as its ready-made name or as the player's own, which ENTER opens in the bar editor: its
    label."""

    label: str


class TimeView(NamedTuple):
    """A length of time, chosen from the lengths every time setting offers: the setting's file name, its label, and what its first
    choice, the value when left out, shows, None for the pattern's step size."""

    setting: str
    label: str
    first: object = None


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
    """A column of a generator's tab: its heading, or None for a column without one, its settings from the top, and the modes it
    shows in, or none for every mode."""

    heading: object
    settings: tuple
    modes: tuple = ()


class GeneratorView(NamedTuple):
    """A generator's tab, or its page: its columns from the left, the help its page's F1 shows, and its Mode, a ChoiceView shown
    first, or None for a generator with one way of working."""

    columns: tuple
    help: str
    mode: object = None
