# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A table of statements' lines, as plain nodes: each line a row of cells as wide as its statement, the register alone while it is
ignored, the register and odd or even, the register, a comparison and what it is compared with, or the register, a sum, its
number, a comparison and what the result is compared with, drawn as a grid of five columns each as wide as its widest value
(interface/tracker/renderers/statement_rows.py), so that nothing moves or grows as a line changes.
"""

from dataclasses import dataclass

from llamatron.interface.forms.nodes import Cells
from llamatron.model.schema import file_format, limits
from llamatron.user_strings import labels

# How the tracker draws a line: a row of the grid, and the first row, which draws the grid's top edge above itself.
STATEMENT_ROW = 'statement row'
FIRST_STATEMENT_ROW = 'first statement row'
# How wide each cell is drawn, so that the cells after it never move.
REGISTER_WIDTH = len(labels.MSG_STATEMENT_IGNORED)
OPERATOR_WIDTH = max(len(operator) for operator in file_format.OPERATORS)
NUMBER_WIDTH = len(str(-limits.MAX_STATEMENT_NUMBER))
# The widest value each column of the grid shows. A line's cells are its register, its operator, then a value or a sum's
# number, a comparison and a value.
VALUE_WIDTH = max(NUMBER_WIDTH, *[len(name) for name in file_format.VALUE_NAMES])
COMPARISON_WIDTH = max(len(comparison) for comparison in file_format.RESULT_COMPARISONS)
PART_WIDTHS = (REGISTER_WIDTH, OPERATOR_WIDTH, VALUE_WIDTH, COMPARISON_WIDTH, VALUE_WIDTH)
COLUMNS = len(PART_WIDTHS)


@dataclass(slots=True, kw_only=True)
class StatementRow(Cells):
    """A line of a table of statements, drawn as a row of the table's grid: its cells between bars, every column at its own
    width whether the line fills it or not, and the rule under it, the grid's bottom edge under the last line."""

    last: bool

    DRAWN_AS = STATEMENT_ROW


@dataclass(slots=True, kw_only=True)
class FirstStatementRow(StatementRow):
    """The first line of a table of statements, which draws the grid's top edge above itself."""

    SELECTED_LINE = 1
    DRAWN_AS = FIRST_STATEMENT_ROW
