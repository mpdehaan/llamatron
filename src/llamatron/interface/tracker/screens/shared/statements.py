# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Bypass When on a settings page: a table of statements about the registers, and a scene's or a clip's sets and adds.

One table serves every page that has one, a generator's, a chain's, a scene's, a clip's and a
track's: a heading, and under it a line for each statement the table may hold. A line is a row
of cells, as wide as its statement: the register alone while the line is ignored, the register
and odd or even, the register, a comparison and what it is compared with, or the register, a
sum, its number, a comparison and what the result is compared with. The lines are drawn as a
grid of five columns, as many as the longest statement has, each column as wide as its widest
value, so that nothing moves or grows as a line changes. Left and Right move between the cells,
ENTER changes the one under the cursor, and Bksp sets the line back to ignored.
"""

from dataclasses import dataclass
from rich.text import Text

from llamatron.interface.tracker import drawing
from llamatron.interface.tracker.dialogs import grouped_choices
from llamatron.interface.tracker.dialogs.grouped_choices import number_or_names, value_groups
from llamatron.interface.tracker.drawing import Box, cursor_mark, padded, Style
from llamatron.interface.tracker.screens.shared.field import Cells, ChoiceField, Field
from llamatron.model.objects import conditions
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import StatementPart
from llamatron.user_strings import errors, labels, legends, marks

# A page's first table, which keeps its lines' labels apart from any other's.
FIRST_TABLE = 0
# How wide each cell is drawn, so that the cells after it never move.
REGISTER_WIDTH = len(labels.MSG_STATEMENT_IGNORED)
OPERATOR_WIDTH = max(len(operator) for operator in file_format.OPERATORS)
NUMBER_WIDTH = len(str(-limits.MAX_STATEMENT_NUMBER))
# The number a statement divides by may not be this.
ZERO = 0
# How wide each column of the grid is inside its bars: the widest value a cell of it shows, a space each side, the picker's
# mark and a space after it. A line's cells are its register, its operator, then a value or a sum's number, a comparison and a value.
VALUE_WIDTH = max(NUMBER_WIDTH, *[len(name) for name in file_format.VALUE_NAMES])
COMPARISON_WIDTH = max(len(comparison) for comparison in file_format.RESULT_COMPARISONS)
CELL_WIDTHS = [len(padded(drawing.NOTHING)) + len(padded(marks.MSG_PICKER_MARK)) - 1 + width for width in (REGISTER_WIDTH, OPERATOR_WIDTH, VALUE_WIDTH, COMPARISON_WIDTH, VALUE_WIDTH)]
COLUMNS = len(CELL_WIDTHS)
# The first choice of a value's picker is a number to type; the registers follow.


@dataclass(slots=True, kw_only=True)
class StatementRow(Cells):
    """A line of a table of statements, drawn as a row of the table's grid: its cells between bars, every column at its own
    width whether the line fills it or not, and the rule under it, the grid's bottom edge under the last line."""

    last: bool

    def lines(self, *, page, here, label_width, width):
        """Return the row's line of cells, the cell under the cursor in reverse video, and the rule under it."""
        return [self.cells_line(page=page, here=here), self.rule_under()]

    def cells_line(self, *, page, here):
        """Return the line of the row's cells between the grid's bars, a column the line doesn't fill left blank."""
        line = Text(cursor_mark(here), no_wrap=True)
        line.append(Box.BAR)
        for place, cell_width in enumerate(CELL_WIDTHS):
            line.append_text(self.cell_text(page=page, here=here, place=place).copy())
            line.append(drawing.SPACE * (cell_width - self.cell_text(page=page, here=here, place=place).cell_len))
            line.append(Box.BAR)
        return line

    def cell_text(self, *, page, here, place):
        """Return what a cell of the row shows: its value, padded, in reverse video under the cursor, and the picker's mark where
        it opens a list; nothing in a column the line doesn't fill."""
        text = Text(no_wrap=True)
        if place >= len(self.cells):
            return text
        cell = self.cells[place]
        on_cell = here and place == min(page.cell, len(self.cells) - 1)
        text.append(padded(str(cell.value()).rstrip()), style=Style.REVERSE if on_cell else Style.PLAIN)
        if cell.enter_what == legends.What.CHOOSE:
            text.append(marks.MSG_PICKER_MARK, style=Style.DIM)
        return text

    def rule_under(self):
        """Return the rule under the row: between rows, or the grid's bottom edge under the last."""
        if self.last:
            return grid_rule(left=Box.BOTTOM_LEFT, joint=Box.BOTTOM_TEE, right=Box.BOTTOM_RIGHT)
        return grid_rule(left=Box.LEFT_TEE, joint=Box.CROSS, right=Box.RIGHT_TEE)


@dataclass(slots=True, kw_only=True)
class FirstStatementRow(StatementRow):
    """The first line of a table of statements, which draws the grid's top edge above itself."""

    SELECTED_LINE = 1

    def lines(self, *, page, here, label_width, width):
        """Return the grid's top edge, the row's line of cells and the rule under it."""
        top = grid_rule(left=Box.TOP_LEFT, joint=Box.TOP_TEE, right=Box.TOP_RIGHT)
        return [top, self.cells_line(page=page, here=here), self.rule_under()]


def grid_rule(*, left, joint, right):
    """Return a rule across the grid of statements, with its ends and the joints where the columns' bars meet it."""
    rule = left + joint.join(Box.RULE * width for width in CELL_WIDTHS) + right
    return Text(drawing.INDENT + rule, no_wrap=True)


def statement_section(*, page, label, table, statements, store):
    """Return a table's section: its heading and a line for each statement it may hold.

    statements() is the table as its object keeps it, and store(place, statement) writes one
    statement, or removes it for None. table is the table's place among the page's tables.
    """
    heading = page.heading(label=label, is_set=None, said=lambda: drawing.NOTHING)
    return [heading, *statement_lines(page=page, table=table, statements=statements, store=store)]


def statement_lines(*, page, table, statements, store):
    """Return a table's lines without a heading, a line for each statement it may hold, for a page that is the table alone."""
    return [_line(page=page, place=place, table=table, statements=statements, store=store) for place in range(limits.MAX_STATEMENTS)]


def _line(*, page, place, table, statements, store):
    """Return one line of a table: the cells of the statement at a place, or the register's cell alone for a line past the last statement."""
    held = statements()
    statement = held[place] if place < len(held) else None
    # A line past the table's last statement writes the next one, since a table keeps no gaps.
    at = min(place, len(held))

    def clear():
        if statement is not None:
            store(at, None)

    def changed(part, value):
        store(at, {**statement, part: value})

    cells = [_register_cell(page=page, statement=statement, store=lambda written: store(at, written), clear=clear)]
    if statement is not None:
        operator = statement[StatementPart.OPERATOR]
        cells.append(_choice_cell(
            page=page, title=labels.MSG_STATEMENT_OPERATOR_TITLE, choices=file_format.OPERATORS, current=operator, width=OPERATOR_WIDTH,
            store=lambda chosen: store(at, conditions.with_operator(statement=statement, operator=chosen)), clear=clear,
        ))
        for part in conditions.parts_of(operator):
            if part == StatementPart.COMPARISON:
                cells.append(_choice_cell(
                    page=page, title=labels.MSG_STATEMENT_COMPARISON_TITLE, choices=file_format.RESULT_COMPARISONS, current=statement[part], width=OPERATOR_WIDTH,
                    store=lambda chosen, part=part: changed(part, chosen), clear=clear,
                ))
            else:
                divides = part == StatementPart.VALUE and operator in file_format.DIVIDING_OPERATORS
                cells.append(_value_cell(page=page, current=statement[part], divides=divides, store=lambda value, part=part: changed(part, value), clear=clear))
    return _grid_row(table=table, place=place, cells=cells)


def _grid_row(*, table, place, cells):
    """Return the row of the grid a line's cells are drawn in: the first draws the grid's top edge, the last its bottom edge."""
    label = labels.MSG_STATEMENT_LINE_LABEL * (table * limits.MAX_STATEMENTS + place + 1)
    last = place == limits.MAX_STATEMENTS - 1
    if place == 0:
        return FirstStatementRow(label=label, cells=cells, last=last)
    return StatementRow(label=label, cells=cells, last=last)


def _register_cell(*, page, statement, store, clear):
    """Return the cell that names a line's register, or says the line is ignored."""
    choices = [labels.MSG_STATEMENT_IGNORED, *grouped_choices.VALUE_NAMES_IN_ORDER]
    current = labels.MSG_STATEMENT_IGNORED if statement is None else statement[StatementPart.REGISTER]
    grouped = value_groups(first=(None, [(labels.MSG_STATEMENT_IGNORED, labels.MSG_STATEMENT_IGNORED)]))

    def chosen(register):
        if register == labels.MSG_STATEMENT_IGNORED:
            clear()
        elif statement is None:
            store(conditions.new_statement(register))
        else:
            store({**statement, StatementPart.REGISTER: register})
    return _choice_cell(page=page, title=labels.MSG_STATEMENT_REGISTER_TITLE, choices=choices, current=current, width=REGISTER_WIDTH, store=chosen, clear=clear, grouped=grouped)


def _choice_cell(*, page, title, choices, current, width, store, clear, grouped=None):
    """Return a cell that picks one of a list, drawn at a width of its own, its picker in groups where grouped is given."""
    return ChoiceField(page=page, label=title, choices=choices, current=current, shown=current.ljust(width), set=store, clear=clear, clear_what=legends.What.CLEAR, grouped=grouped)


def _value_cell(*, page, current, divides, store, clear):
    """Return a cell that holds a number, a draw or a register: ENTER offers a number to type, each draw and each register, under their headings."""
    grouped = number_or_names()

    def typed(number):
        if divides and number == ZERO:
            page.refuse(errors.ERR_CANNOT_DIVIDE_BY_ZERO)
            return
        store(number)

    def picked(place):
        chosen = grouped.value_at(place)
        if chosen == grouped_choices.NUMBER_CHOSEN:
            page.ask_number(
                title=labels.MSG_STATEMENT_VALUE_TITLE, value=str(current) if current not in file_format.VALUE_NAMES else str(ZERO), then=typed,
                low=-limits.MAX_STATEMENT_NUMBER, high=limits.MAX_STATEMENT_NUMBER,
            )
        else:
            store(chosen)

    def pick():
        page.ask(dialog=grouped.dialog(title=labels.MSG_STATEMENT_VALUE_TITLE, current=current if current in file_format.VALUE_NAMES else grouped_choices.NUMBER_CHOSEN), then=picked)
    return Field(label=labels.MSG_STATEMENT_VALUE_TITLE, value=lambda: str(current).ljust(NUMBER_WIDTH), enter=pick, enter_what=legends.What.CHOOSE, clear=clear)
