# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""How the tracker draws what a dialog shows (interface/forms/dialogs.py): its paragraphs, wrapped or cut to the dialog's width,
dim where said in passing, its answers as a row of boxed buttons, a picker's list, a line being typed and
the rows of a dialog's settings."""

from rich.text import Text

from llamatron.interface.forms import dialogs
from llamatron.interface.tracker import drawing
from llamatron.interface.tracker.components.button_row import button_row
from llamatron.interface.tracker.drawing import cursor_mark, fit, padded, Style, wrapped
from llamatron.user_strings import marks


def said_lines(*, paragraphs, width):
    """Return the lines of a dialog's paragraphs at a width."""
    lines = []
    for paragraph in paragraphs:
        lines += _paragraph_lines(paragraph=paragraph, width=width)
    return lines


def answer_lines(answers):
    """Return the three lines of a dialog's answers, the selected one double-lined."""
    return button_row(buttons=list(answers.buttons), selected=answers.selected)


def message_lines(*, paragraphs, answers, width):
    """Return what a message or a question shows: its paragraphs, a blank line, and its answers."""
    return [*said_lines(paragraphs=paragraphs, width=width), Text(drawing.NOTHING), *answer_lines(answers)]


def choice_lines(*, choices, width):
    """Return a picker's list: what was typed, dim, then each row after its cursor's mark, cut to the width, a heading dim."""
    lines = []
    if choices.typed:
        lines.append(Text(fit(text=drawing.SPACE + marks.MSG_SEARCH_SHOWN.format(text=choices.typed), width=width), style=Style.DIM))
    return [*lines, *row_lines_of(rows=choices.rows, width=width)]


def row_lines_of(*, rows, width):
    """Return a list's rows, each after its cursor's mark and cut to the width, or as it is with no width: a heading dim, a bold
    row bold."""
    lines = []
    for row in rows:
        text = cursor_mark(row.under_cursor) + row.text
        if width is not None:
            text = fit(text=text, width=width)
        if row.heading:
            lines.append(Text(text, style=Style.DIM))
        elif row.bold:
            lines.append(Text(text, style=Style.BOLD))
        else:
            lines.append(Text(text))
    return lines


def column_lines(*, rows, width, height):
    """Return one list of several side by side: its rows cut to the column's width, and blank ones of that width under them up
    to a height, so that the columns beside it line up."""
    lines = row_lines_of(rows=rows, width=width)
    return [*lines, *[Text(drawing.SPACE * width)] * (height - len(lines))]


def side_by_side(*, columns, gap):
    """Return lists drawn side by side, their lines joined across, a gap between one list and the next."""
    lines = []
    for row in range(len(columns[0])):
        line = Text(drawing.NOTHING)
        for place, column in enumerate(columns):
            line.append_text(column[row])
            line.append(drawing.SPACE * gap if place < len(columns) - 1 else drawing.NOTHING)
        lines.append(line)
    return lines


def column_headings(*, names, widths, chosen, gap):
    """Return the headings over lists side by side, each over its list after the room a cursor's mark takes, the chosen list's
    bold and the others dim."""
    line = Text(drawing.NOTHING)
    for place, name in enumerate(names):
        line.append(fit(text=drawing.SPACE * len(cursor_mark(False)) + name, width=widths[place]), style=Style.BOLD if place == chosen else Style.DIM)
        line.append(drawing.SPACE * gap if place < len(names) - 1 else drawing.NOTHING)
    return line


def grid_cells_line(cells):
    """Return one line of a grid of choices: each choice's name after its key-like padding, reversed under the cursor and
    padded out to its column's width, each heading bold in its column, and each gap blank across its column."""
    line = Text(no_wrap=True)
    for cell in cells:
        if cell.kind == dialogs.GAP_CELL:
            line.append(drawing.SPACE * cell.width)
        elif cell.kind == dialogs.HEADING_CELL:
            line.append(fit(text=drawing.SPACE + cell.text, width=cell.width), style=Style.BOLD)
        else:
            line.append(padded(cell.text), style=Style.REVERSE if cell.selected else Style.PLAIN)
            line.append(drawing.SPACE * max(cell.width - len(cell.text) - 2, 0))
    return line


def bar_level_line(level):
    """Return one level of a row of bars: its label dim, then each cell's piece of bar centred."""
    line = Text(level.label, style=Style.DIM)
    for cell in level.cells:
        line.append(cell.center(level.cell_width))
    return line


def number_cells_line(numbers):
    """Return the numbers under a row of bars, the cursor's reversed, as the cursor's cell of the step editors is."""
    line = Text(drawing.SPACE * numbers.indent)
    for place, number in enumerate(numbers.numbers):
        if place == numbers.selected:
            line.append(str(number).center(numbers.cell_width), style=Style.REVERSE)
        else:
            line.append(str(number).center(numbers.cell_width))
    return line


def dim_line(text):
    """Return a line said in passing, dim, as it is: no wrapping and no cutting, as a rule of marks is."""
    return Text(text, style=Style.DIM)


def pieces_line(pieces):
    """Return a line of pieces, each drawn dim, bold or plain."""
    line = Text(no_wrap=True)
    for part in pieces:
        if part.dim:
            line.append(part.text, style=Style.DIM)
        elif part.bold:
            line.append(part.text, style=Style.BOLD)
        else:
            line.append(part.text, style=Style.PLAIN)
    return line


def filled(*, lines, height):
    """Return lines made up to a height with blank ones, so that a list keeps its height as it scrolls or shrinks."""
    return [*lines, *[Text(drawing.NOTHING)] * (height - len(lines))]


def typed_line(*, typed, width):
    """Return a line being typed, scrolled so that the cursor always shows, the cursor drawn in reverse video over the
    character it is before, or over a space at the end."""
    shown = width - len(marks.MSG_PROMPT_MARK) - len(typed.label) - 1
    start = max(typed.cursor - shown + 1, 0)
    text = typed.text[start:start + shown]
    at = typed.cursor - start
    line = Text(marks.MSG_PROMPT_MARK + typed.label + text[:at])
    line.append(text[at:at + 1] or drawing.SPACE, style=Style.REVERSE)
    line.append(text[at + 1:])
    return line


def row_lines(*, rows, label_width):
    """Return a dialog's settings, each its cursor's mark, its label padded to the labels' width and its value, bold under the
    cursor and dim where it cannot be set."""
    lines = []
    for row in rows:
        line = Text(cursor_mark(row.under_cursor) + row.label.ljust(label_width))
        style = Style.PLAIN
        if row.blocked:
            style = Style.DIM
        elif row.under_cursor:
            style = Style.BOLD
        line.append(row.value, style=style)
        lines.append(line)
    return lines


def _paragraph_lines(*, paragraph, width):
    if paragraph.refusal:
        return [Text(paragraph.text, style=Style.REFUSAL)]
    if paragraph.heading and paragraph.fills_width:
        return [Text(fit(text=paragraph.text, width=width), style=Style.BOLD)]
    if paragraph.heading:
        return [Text(paragraph.text, style=Style.BOLD)]
    if paragraph.as_it_is:
        return [Text(paragraph.text)]
    if paragraph.one_line and paragraph.fills_width:
        return [Text(fit(text=paragraph.text, width=width))]
    if paragraph.one_line and paragraph.dim:
        return [Text(fit(text=paragraph.text, width=width), style=Style.DIM)]
    if paragraph.one_line:
        return [Text(fit(text=paragraph.text, width=width).rstrip())]
    if paragraph.dim:
        return [Text(line.plain, style=Style.DIM) for line in wrapped(text=paragraph.text, width=width)]
    return wrapped(text=paragraph.text, width=width)

def key_columns(*, items, width, columns):
    """Return the keys as lines of so many columns, filled down one column and then the next, each key as the main menu draws one."""
    rows = -(-len(items) // columns)
    column_width = width // columns
    lines = []
    for row in range(rows):
        line = Text(no_wrap=True)
        for column in range(columns):
            at = row + column * rows
            if at < len(items):
                line.append_text(key_cell(item=items[at], width=column_width))
        lines.append(line)
    return lines


def key_cell(*, item, width):
    """Return one key as a cell of the given width: its label in reverse video, then what it does."""
    cell = Text(no_wrap=True)
    cell.append(padded(item.shown_label()), style=Style.REVERSE)
    cell.append(drawing.SPACE + item.what)
    cell.truncate(width)
    cell.append(drawing.SPACE * (width - cell.cell_len))
    return cell
