# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A settings page's tab box as plain nodes: its tabs, each with fields across its top and columns under headings, the row of tabs
the cursor stops on, and where the cursor goes from a field among the spots the tracker drew them at (Spot), with nothing of how
the box looks (interface/tracker/renderers/tab_box.py)."""

from dataclasses import dataclass, field as dataclass_field

from llamatron.interface.forms.nodes import Field, Heading
from llamatron.user_strings import labels, marks

NAME_LINE = 1
# Where the cursor is, among the chosen tab's fields, when it is on the row of tabs.
ON_TAB_ROW = -1
ON_TAB_ROW = -1
# Where a move inside the box leads when it leaves the box downward, to what is under the box.
BELOW_BOX = -2
BELOW_BOX = -2
# The band of the fields across a tab's top, such as Enabled and Mode, above the columns' first band.
TOP_BAND = -1


@dataclass(slots=True, kw_only=True)
class TabColumn:
    """A column of a tab: its heading, drawn bold above it, or None for none, its fields, whether it starts a band of its own
    under the columns before it, as a generator's Restart does, whatever room is left beside them, and whether it is boxed."""

    heading: object
    fields: list
    under: bool = False
    # Whether it is drawn in a light box of its own, as an effect block is, every boxed column of a tab as wide and as tall as
    # the widest and tallest, so that they line up.
    boxed: bool = False


@dataclass(slots=True, kw_only=True)
class Spot:
    """Where a field of a tab is drawn: its band of columns side by side (TOP_BAND for the fields across the top), its column
    among the band's, counted from the left, and the line its cursor stands on, counted from the top of its column."""

    band: int
    column: int
    line: int


@dataclass(slots=True, kw_only=True)
class Tab:
    """One tab of a tab box: its name, the fields across its top, its columns, whether the built-in generator it shows is on,
    True or False, or None for a tab that shows no generator, its remarks, dim lines under its settings, and whether it isn't
    ready yet, as a song wizard's tab before a genre is chosen, which draws it dim."""

    label: str
    top: list = dataclass_field(default_factory=list)
    columns: list = dataclass_field(default_factory=list)
    on: object = None
    remarks: list = dataclass_field(default_factory=list)
    not_ready: bool = False

    def every_field(self):
        """Return the tab's fields in the order the cursor goes through them: across the top, then column by column."""
        fields = list(self.top)
        for column in self.columns:
            fields += column.fields
        return fields

    def is_dim(self):
        """Return whether the tab's name is drawn dim: a generator's that is off, or a tab not ready yet."""
        return self.on is False or self.not_ready

    def shown_name(self):
        """Return the tab's name as its tab shows it, with the mark of its generator being on or off where it shows one."""
        if self.on is None:
            return self.label
        mark = marks.MSG_TOGGLE_ON
        if not self.on:
            mark = marks.MSG_FIELD_TOGGLE_OFF
        return marks.MSG_TAB_WITH_MARK.format(name=self.label, mark=mark)


@dataclass(slots=True, kw_only=True)
class TabBox:
    """A page's tab box among its fields: its tabs, in order. The page shows the row of tabs as a field the cursor stops on,
    then the selected tab's fields."""

    tabs: list
    label: str = labels.MSG_TABS_LABEL

    IS_TAB_BOX = True
    IS_TAB_ROW = False

    def tab_named(self, name):
        """Return the place of the tab of a name, or the first's where none has it."""
        for place, tab in enumerate(self.tabs):
            if tab.label == name:
                return place
        return 0

    def place_holding(self, label):
        """Return the place of the first tab holding a field of a label, or None where none does."""
        for place, tab in enumerate(self.tabs):
            if any(field.label == label for field in tab.every_field()):
                return place
        return None


@dataclass(slots=True, kw_only=True)
class TabRow(Field):
    """The row of tabs, where the cursor stops: Left and Right, and [ and ], choose the tab before or after, stopping at the ends."""

    IS_TAB_ROW = True

    def row_keys(self, page):
        """Return the keys that choose another tab."""
        return [page.bind(page.KEYS.ALONG_TABS, action=page.step_tab)]


def columns_of_sections(fields):
    """Return the columns of a run of sections, each heading's fields a column under the heading's name, and any fields before
    the first heading a column with no heading."""
    columns = []
    current = TabColumn(heading=None, fields=[])
    for field in fields:
        if isinstance(field, Heading):
            if current.fields:
                columns.append(current)
            current = TabColumn(heading=field.label, fields=[])
        else:
            current.fields.append(field)
    if current.fields:
        columns.append(current)
    return columns


def without_headings(fields):
    """Return a section's fields without its heading, since a tab shows its settings open, in columns of their own."""
    return [field for field in fields if not isinstance(field, Heading)]


def spot_below(*, spots, here):
    """Return where Down leads from the field at a place: the next field down its column; at a column's foot, the first field of
    the column below in the next band, the one in the same place or else the last; under the last band, BELOW_BOX."""
    spot = spots[here]
    later = [place for place in _column_places(spots=spots, band=spot.band, column=spot.column) if place > here]
    if later:
        return later[0]
    bands = [band for band in _bands_in(spots) if band > spot.band]
    if not bands:
        return BELOW_BOX
    return _column_places(spots=spots, band=bands[0], column=_column_near(spots=spots, band=bands[0], column=spot.column))[0]


def spot_above(*, spots, here):
    """Return where Up leads from the field at a place: the field above in its column; at a column's head, the last field of the
    column above in the band before, the one in the same place or else the last; above the first band, ON_TAB_ROW."""
    spot = spots[here]
    earlier = [place for place in _column_places(spots=spots, band=spot.band, column=spot.column) if place < here]
    if earlier:
        return earlier[-1]
    bands = [band for band in _bands_in(spots) if band < spot.band]
    if not bands:
        return ON_TAB_ROW
    return _column_places(spots=spots, band=bands[-1], column=_column_near(spots=spots, band=bands[-1], column=spot.column))[-1]


def spot_beside(*, spots, here, direction):
    """Return where Left or Right leads from the field at a place: the field of the column beside, in the same band, whose line is
    nearest, the upper of two as near; at the band's side, the same place."""
    spot = spots[here]
    places = _column_places(spots=spots, band=spot.band, column=spot.column + direction)
    if not places:
        return here
    return min(places, key=lambda place: (abs(spots[place].line - spot.line), spots[place].line))


def spot_like(*, spots, spot):
    """Return the place of the field standing where a spot of another tab stood: in the same band and column, on the nearest
    line; else the column of that place in the nearest band that has one; else the first field."""
    for band in sorted(_bands_in(spots), key=lambda band: abs(band - spot.band)):
        same = _column_places(spots=spots, band=band, column=spot.column)
        if same:
            return min(same, key=lambda place: (abs(spots[place].line - spot.line), spots[place].line))
    return 0


def has_columns_beside(*, spots, here):
    """Return whether the field at a place shares its band with another column, so that Left and Right have somewhere to go."""
    spot = spots[here]
    return any(other.band == spot.band and other.column != spot.column for other in spots)


def spot_from_below(spots):
    """Return where Up from under the box leads: the last field of the first column of the last band."""
    last_band = _bands_in(spots)[-1]
    return _column_places(spots=spots, band=last_band, column=0)[-1]


def _column_places(*, spots, band, column):
    """Return the places of the fields of a column of a band, top to bottom."""
    return [place for place, spot in enumerate(spots) if spot.band == band and spot.column == column]


def _bands_in(spots):
    """Return the bands the fields stand in, top to bottom."""
    return sorted({spot.band for spot in spots})


def _column_near(*, spots, band, column):
    """Return the column of a band in a column's place, or the band's last where it has fewer."""
    columns = sorted({spot.column for spot in spots if spot.band == band})
    if column in columns:
        return column
    return columns[-1]
