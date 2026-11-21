# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Conditional Execution on a settings page: a table of statements about the registers, and a scene's or a clip's sets and adds.

One table serves every page that has one, a generator's, a chain's, a scene's, a clip's and a
track's: a heading, and under it a line for each statement the table may hold. A line is a row
of cells, as wide as its statement: the register alone while the line is ignored, the register
and odd or even, the register, a comparison and what it is compared with, or the register, a
sum, its number, a comparison and what the result is compared with. Each cell keeps a fixed
width, so nothing moves as a line changes. Left and Right move between the cells, ENTER
changes the one under the cursor, and Bksp sets the line back to ignored.
"""

from llamatron.interface.tracker import drawing
from llamatron.interface.tracker.dialogs import grouped_choices
from llamatron.interface.tracker.dialogs.grouped_choices import number_or_names, value_groups
from llamatron.interface.tracker.screens.shared.field import Cells, ChoiceField, Field, NumberField
from llamatron.model.objects import conditions
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import StatementPart
from llamatron.user_strings import errors, labels, legends, marks

# A page's first table and its second, which keep their lines' labels apart.
FIRST_TABLE = 0
SECOND_TABLE = 1
# How wide each cell is drawn, so that the cells after it never move.
REGISTER_WIDTH = len(labels.MSG_STATEMENT_IGNORED)
OPERATOR_WIDTH = max(len(operator) for operator in file_format.OPERATORS)
NUMBER_WIDTH = len(str(-limits.MAX_STATEMENT_NUMBER))
# The number a statement divides by may not be this.
ZERO = 0
# The first choice of a value's picker is a number to type; the registers follow.


def statement_section(*, page, label, table, statements, store):
    """Return a table's section: its heading and a line for each statement it may hold.

    statements() is the table as its object keeps it, and store(place, statement) writes one
    statement, or removes it for None. table is the table's place among the page's tables.
    """
    heading = page.heading(label=label, is_set=None, said=lambda: drawing.NOTHING)
    lines = [_line(page=page, place=place, table=table, statements=statements, store=store) for place in range(limits.MAX_STATEMENTS)]
    return [heading, *lines]


def register_fields(*, page, label, name_label, values, store, lowest=limits.MIN_REGISTER_VALUE):
    """Return a section of one number for each register, blank until typed: what a scene or a clip sets the registers to, or adds to them.

    values() is what each register is given, and store(register, value) gives one a value, or none for None.
    """
    heading = page.heading(label=label, is_set=lambda: bool(values()))
    return [heading, *[_register_field(page=page, label=name_label.format(name=register), register=register, values=values, store=store, lowest=lowest) for register in file_format.REGISTER_NAMES]]


def _register_field(*, page, label, register, values, store, lowest):
    held = values().get(register)
    return NumberField(
        page=page, label=label, number=held, start=ZERO, shown=marks.MSG_NONE_SHOWN if held is None else str(held),
        lowest=lowest, highest=limits.MAX_REGISTER_VALUE, set=lambda number: store(register, number), clear=lambda: store(register, None),
    )


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
    return Cells(label=labels.MSG_STATEMENT_LINE_LABEL * (table * limits.MAX_STATEMENTS + place + 1), cells=cells)


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
