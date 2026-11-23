# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The tab box of a settings page: an outlined box with a row of tabs on its top edge, the selected tab open into the box and bold,
and inside it the selected tab's settings: the ones across the top, such as a built-in generator's Enabled and Mode, then its
columns side by side under bold headings, wrapping under each other where they don't fit, then its remarks, dim. The box keeps
the height of its tallest tab, so that choosing another tab moves nothing below it.

A tab of a built-in generator shows ● after its name when the generator is on, and ○, dim, when it is off. Where the tabs are
wider than the box, < and > stand at the ends for the tabs hidden that way."""

from rich.text import Text

from llamatron.interface.forms import tab_box as tab_box_nodes
from llamatron.interface.forms.tab_box import Spot
from llamatron.interface.tracker import drawing
from llamatron.interface.tracker.drawing import Box, Style
from llamatron.interface.tracker.renderers.fields import field_lines
from llamatron.user_strings import marks

# Space between columns side by side, and the most lines of remarks a tab shows.
COLUMN_GAP = drawing.INDENT
COLUMN_GAP = drawing.INDENT
MOST_REMARKS = 3
MOST_REMARKS = 3
# The box's sides and what stands between a side and the settings.
SIDES = 2
SIDES = 2
INSET = drawing.SPACE
INSET = drawing.SPACE
# The tab row's lines: the tabs' tops, their names, and the box's top edge, which the tab row's names are on.
TAB_ROW_LINES = 3
TAB_ROW_LINES = 3
NAME_LINE = 1
TOP_BAND = -1
# The blank line kept under the tallest tab's last line, so that nothing crowds the box's bottom edge.
SPACE_UNDER = 1


def box_lines(*, page, box, chosen, cursor, width):
    """Return the box's lines, and the place among them of the line the cursor is on, or None where it is elsewhere. cursor is
    where the cursor is: tab_box_nodes.ON_TAB_ROW, the place of the field it is on among the chosen tab's fields, or None outside the box."""
    inner = width - SIDES - len(INSET) * SIDES
    contents = [_tab_contents(page=page, tab=tab, inner=inner, cursor=None) for tab in box.tabs]
    lines, selected = _tab_contents(page=page, tab=box.tabs[chosen], inner=inner, cursor=cursor)
    height = max(len(content[0]) for content in contents) + SPACE_UNDER
    lines += [Text(drawing.NOTHING)] * (height - len(lines))
    result = [*boxed_tabs(tabs=box.tabs, chosen=chosen, width=width, here=cursor == tab_box_nodes.ON_TAB_ROW, lines=lines)]
    if cursor == tab_box_nodes.ON_TAB_ROW:
        return result, NAME_LINE
    if selected is None:
        return result, None
    return result, TAB_ROW_LINES + selected


def boxed_tabs(*, tabs, chosen, width, here, lines):
    """Return a row of tabs over a box of a width holding lines, the chosen tab open into the box and reversed where the cursor
    is on the row: what a settings page's tab box draws, and a list page that shows its rows in tabs too."""
    inner = inner_width(width)
    result = _tab_row(tabs=tabs, chosen=chosen, width=width, here=here)
    for line in lines:
        result.append(_boxed(line=line, inner=inner))
    result.append(Text(Box.BOTTOM_LEFT + Box.RULE * (width - SIDES) + Box.BOTTOM_RIGHT, no_wrap=True))
    return result


def inner_width(width):
    """Return how wide the inside of a box of a width is, between its sides and their insets."""
    return width - SIDES - len(INSET) * SIDES


def spots_of(*, page, tab, width):
    """Return where each of a tab's fields is drawn in a box of a width, as Spots, in the order of the tab's fields."""
    inner = width - SIDES - len(INSET) * SIDES
    spots = [Spot(band=tab_box_nodes.TOP_BAND, column=0, line=place) for place in range(len(tab.top))]
    drawn = [_column_lines(page=page, column=column, inner=inner, cursor=None)[0] for column in tab.columns]
    for band_place, band in enumerate(_bands_of(widths=[_column_width(lines) for lines in drawn], inner=inner, under=_columns_under(tab.columns))):
        for column_place, place in enumerate(band):
            spots += _column_spots(page=page, column=tab.columns[place], band=band_place, column_place=column_place, inner=inner)
    return spots


def _column_spots(*, page, column, band, column_place, inner):
    """Return the Spots of a column's fields, each line counted from the column's top, its heading's line included."""
    spots = []
    line = 0
    if column.heading is not None:
        line += 1
    for field in column.fields:
        spots.append(Spot(band=band, column=column_place, line=line + field.SELECTED_LINE))
        line += len(field_lines(field, page=page, here=False, label_width=0, width=inner))
    return spots


def _tab_contents(*, page, tab, inner, cursor):
    """Return a tab's lines inside the box and the place of the cursor's among them, or None: a blank line, the fields across
    the top, the columns after a blank line, and the remarks after another."""
    lines = [Text(drawing.NOTHING)]
    selected = None
    top_width = max((len(field.get_drawn_label(page)) for field in tab.top), default=0) + len(COLUMN_GAP)
    for place, field in enumerate(tab.top):
        here = place == cursor
        if here:
            selected = len(lines) + field.SELECTED_LINE
        lines += field_lines(field, page=page, here=here, label_width=top_width, width=inner)
    if tab.top and tab.columns:
        lines.append(Text(drawing.NOTHING))
    bands, band_selected = _bands(page=page, columns=tab.columns, inner=inner, cursor=_after_top(cursor=cursor, top=tab.top))
    if band_selected is not None:
        selected = len(lines) + band_selected
    lines += bands
    if tab.remarks:
        lines.append(Text(drawing.NOTHING))
        lines += [Text(remark, style=Style.DIM, no_wrap=True) for remark in tab.remarks[:MOST_REMARKS]]
    return lines, selected


def _after_top(*, cursor, top):
    """Return the cursor's place among the columns' fields, or None where it is not among them."""
    if cursor is None or cursor < len(top):
        return None
    return cursor - len(top)


def _bands(*, page, columns, inner, cursor):
    """Return the columns' lines, as many side by side as fit the box's inside, the rest in bands below after a blank line, and the
    place of the cursor's line among them, or None."""
    drawn = []
    first = 0
    for column in columns:
        drawn.append(_column_lines(page=page, column=column, inner=inner, cursor=_within(cursor=cursor, first=first, count=len(column.fields))))
        first += len(column.fields)
    lines = []
    selected = None
    for band in _bands_of(widths=[_column_width(column_lines) for column_lines, _ in drawn], inner=inner, under=_columns_under(columns)):
        lines, selected = _band_added(lines=lines, band=[drawn[place] for place in band], selected=selected)
    return lines, selected


def _bands_of(*, widths, inner, under=()):
    """Return the bands columns of some widths stand in, each the places of the columns side by side in it: as many as fit the
    box's inside, the rest in the bands below, and each column whose place is among under starting a band of its own."""
    bands = []
    band = []
    for place, width in enumerate(widths):
        if band and (place in under or _band_width([*[widths[each] for each in band], width]) > inner):
            bands.append(band)
            band = []
        band.append(place)
    if band:
        bands.append(band)
    return bands


def _columns_under(columns):
    """Return the places of the columns that start a band of their own."""
    return {place for place, column in enumerate(columns) if column.under}


def _within(*, cursor, first, count):
    """Return the cursor's place within a column whose fields start at first, or None where it is in another."""
    if cursor is None or not first <= cursor < first + count:
        return None
    return cursor - first


def _column_lines(*, page, column, inner, cursor):
    """Return a column's lines, its heading bold above its fields, each label as wide as its column's widest, and the place of the
    cursor's line among them, or None."""
    label_width = max((len(field.get_drawn_label(page)) for field in column.fields), default=0) + len(COLUMN_GAP)
    lines = []
    if column.heading is not None:
        lines.append(Text(drawing.INDENT + column.heading, style=Style.BOLD, no_wrap=True))
    selected = None
    for place, field in enumerate(column.fields):
        here = place == cursor
        if here:
            selected = len(lines) + field.SELECTED_LINE
        lines += field_lines(field, page=page, here=here, label_width=label_width, width=inner)
    return lines, selected


def _band_width(widths):
    """Return how wide columns of some widths are side by side, with the space between them."""
    return sum(widths) + len(COLUMN_GAP) * (len(widths) - 1)


def _column_width(lines):
    """Return how wide a column is: as wide as its widest line."""
    return max((line.cell_len for line in lines), default=0)


def _band_added(*, lines, band, selected):
    """Return the lines with a band of columns side by side added after a blank line between bands, and the cursor's line."""
    if lines:
        lines = [*lines, Text(drawing.NOTHING)]
    widths = [_column_width(column_lines) for column_lines, _ in band]
    height = max(len(column_lines) for column_lines, _ in band)
    start = len(lines)
    for row in range(height):
        line = Text(no_wrap=True)
        for place, (column_lines, _) in enumerate(band):
            if place:
                line.append(COLUMN_GAP)
            part = Text(drawing.NOTHING)
            if row < len(column_lines):
                part = column_lines[row]
            line.append_text(part)
            line.append(drawing.SPACE * (widths[place] - part.cell_len))
        lines.append(line)
    for _, column_selected in band:
        if column_selected is not None:
            selected = start + column_selected
    return lines, selected


def _boxed(*, line, inner):
    """Return a line of the inside of the box between its sides, cut or padded to the inside's width."""
    boxed = Text(Box.BAR + INSET, no_wrap=True)
    shown = line[:inner]
    boxed.append_text(shown)
    boxed.append(drawing.SPACE * (inner - shown.cell_len) + INSET + Box.BAR)
    return boxed


def _tab_row(*, tabs, chosen, width, here):
    """Return the row of tabs: the tabs' tops, their names, the chosen one bold and those of a generator that's off dim, and the
    box's top edge, open under the chosen tab; < and > stand for tabs hidden at either end."""
    names, shown_chosen = _tabs_shown(tabs=tabs, chosen=chosen, width=width)
    widths = [len(drawing.padded(name)) for name, _ in names]
    tops = Text(Box.TOP_LEFT + Box.TOP_TEE.join(Box.RULE * each for each in widths) + Box.TOP_RIGHT, no_wrap=True)
    middle = Text(Box.BAR, no_wrap=True)
    for place, (name, dim) in enumerate(names):
        style = Style.PLAIN
        if place == shown_chosen:
            style = Style.BOLD
            if here:
                style = Style.REVERSE
        if dim:
            style = f'{style} {Style.DIM}'.strip()
        middle.append(drawing.padded(name), style=style)
        middle.append(Box.BAR)
    return [tops, middle, Text(_top_edge(widths=widths, chosen=shown_chosen, width=width), no_wrap=True)]


def _top_edge(*, widths, chosen, width):
    """Return the box's top edge under the tabs: a rule, open under the chosen tab, each tab's side meeting it in the joint that
    joins the lines there."""
    edges = [0]
    for each in widths:
        edges.append(edges[-1] + each + 1)
    cells = [Box.RULE] * width
    for place, each in enumerate(widths):
        if place == chosen:
            for column in range(edges[place] + 1, edges[place] + 1 + each):
                cells[column] = drawing.SPACE
    for place, column in enumerate(edges):
        cells[column] = _joint(place=place, chosen=chosen, last=len(edges) - 1, at_right=column == width - 1)
    if edges[-1] < width - 1:
        cells[width - 1] = Box.TOP_RIGHT
    return drawing.NOTHING.join(cells)


def _joint(*, place, chosen, last, at_right):
    """Return the joint where the side of a tab, counted from the left, meets the box's top edge."""
    if place == 0:
        if chosen == 0:
            return Box.BAR
        return Box.LEFT_TEE
    if place == last and at_right:
        if chosen == last - 1:
            return Box.BAR
        return Box.RIGHT_TEE
    if chosen == place - 1:
        return Box.BOTTOM_LEFT
    if chosen == place:
        return Box.BOTTOM_RIGHT
    return Box.BOTTOM_TEE


def _tabs_shown(*, tabs, chosen, width):
    """Return the names of the tabs that fit, each with whether it is drawn dim, < and > standing first and last for the tabs hidden
    that way, and the place of the chosen tab among them."""
    names = [(tab.shown_name(), tab.on is False) for tab in tabs]
    first = chosen
    last = chosen
    while True:
        grown = False
        if last + 1 < len(names) and _row_width(names=names, first=first, last=last + 1) <= width:
            last += 1
            grown = True
        if first > 0 and _row_width(names=names, first=first - 1, last=last) <= width:
            first -= 1
            grown = True
        if not grown:
            break
    shown = names[first:last + 1]
    shown_chosen = chosen - first
    if first > 0:
        shown = [(marks.MSG_TABS_HIDDEN_BEFORE, False), *shown]
        shown_chosen += 1
    if last + 1 < len(names):
        shown.append((marks.MSG_TABS_HIDDEN_AFTER, False))
    return shown, shown_chosen


def _row_width(*, names, first, last):
    """Return how wide the tabs from first to last are, with room for < and > where tabs are hidden either way."""
    shown = names[first:last + 1]
    width = 1 + sum(len(drawing.padded(name)) + 1 for name, _ in shown)
    if first > 0:
        width += len(drawing.padded(marks.MSG_TABS_HIDDEN_BEFORE)) + 1
    if last + 1 < len(names):
        width += len(drawing.padded(marks.MSG_TABS_HIDDEN_AFTER)) + 1
    return width
