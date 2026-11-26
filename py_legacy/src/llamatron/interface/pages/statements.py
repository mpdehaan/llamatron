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


from llamatron.interface.forms import grouped_choices, statement_rows
from llamatron.interface.forms.grouped_choices import number_or_names, value_groups
from llamatron.interface.forms.nodes import ChoiceField, Field
from llamatron.interface.forms.statement_rows import FirstStatementRow, StatementRow
from llamatron.model.objects import conditions
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import StatementPart
from llamatron.user_strings import errors, labels, legends

# A page's first table, which keeps its lines' labels apart from any other's.
FIRST_TABLE = 0
# The number a statement divides by may not be this.
ZERO = 0
# What a table's heading says after its name: nothing, never a mark of a value set.
NOTHING_SAID = ''
# The first choice of a value's picker is a number to type; the registers follow.


class BypassWhenPresenter:
    """A page of its own holding one table of Bypass When statements, which a chain's or a generator's page has no room for:
    holder() returns what holds the statements as it is now, a chain or a generator's settings, and the page asks for every
    dialog the table's cells need."""

    __slots__ = ('_page', '_document', '_holder')

    def __init__(self, *, page, document, holder):
        self._page = page
        self._document = document
        self._holder = holder

    def form(self):
        """Return the table's lines with no heading, since the table is all the page holds."""
        return statement_lines(page=self._page, table=FIRST_TABLE, statements=self._statements, store=self._store)

    def _statements(self):
        holder = self._holder()
        return holder.get_bypass_when()

    def _store(self, *, place, statement):
        holder = self._holder()
        self._document.change_set(holder.set_bypass_statement, place=place, statement=statement)


def statement_section(*, page, label, table, statements, store):
    """Return a table's section: its heading and a line for each statement it may hold.

    statements() is the table as its object keeps it, and store(place=, statement=) writes one
    statement, or removes it for None. table is the table's place among the page's tables.
    """
    heading = page.heading(label=label, is_set=None, said=lambda: NOTHING_SAID)
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
            store(place=at, statement=None)

    def changed(part, value):
        store(place=at, statement={**statement, part: value})

    cells = [_register_cell(page=page, statement=statement, store=lambda written: store(place=at, statement=written), clear=clear)]
    if statement is not None:
        operator = statement[StatementPart.OPERATOR]
        cells.append(_choice_cell(
            page=page, title=labels.MSG_STATEMENT_OPERATOR_TITLE, choices=file_format.OPERATORS, current=operator, width=statement_rows.OPERATOR_WIDTH,
            store=lambda chosen: store(place=at, statement=conditions.with_operator(statement=statement, operator=chosen)), clear=clear,
        ))
        for part in conditions.parts_of(operator):
            if part == StatementPart.COMPARISON:
                cells.append(_choice_cell(
                    page=page, title=labels.MSG_STATEMENT_COMPARISON_TITLE, choices=file_format.RESULT_COMPARISONS, current=statement[part], width=statement_rows.OPERATOR_WIDTH,
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
    return _choice_cell(page=page, title=labels.MSG_STATEMENT_REGISTER_TITLE, choices=choices, current=current, width=statement_rows.REGISTER_WIDTH, store=chosen, clear=clear, grouped=grouped)


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
        page.ask_grouped(title=labels.MSG_STATEMENT_VALUE_TITLE, grouped=grouped, current=current if current in file_format.VALUE_NAMES else grouped_choices.NUMBER_CHOSEN, then=picked)
    return Field(label=labels.MSG_STATEMENT_VALUE_TITLE, value=lambda: str(current).ljust(statement_rows.NUMBER_WIDTH), enter=pick, enter_what=legends.What.CHOOSE, clear=clear)
