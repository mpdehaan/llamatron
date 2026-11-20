# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Conditional Execution: statements about the registers that stop a thing while any of them is true.

A table is a short list of statements, each written as a file writes it, a dictionary of its
parts. One of three shapes: a register compared with a number or another register, AX < 3; a
register asked whether it is odd or even; or a sum worked out first and its result compared,
AX % 3 = 0, where each number may be another register. The same table is kept by a generator, a
chain, a scene, a clip and a track, so the check, the reading and the answer are all here.

Every sum is in integers: a division rounds down and a remainder takes the sign of what divides.
A written 0 is refused after a division or a remainder. A register that divides and holds 0 as
the song plays is never divided by: the statement counts as true, so the thing it is on is stopped.

A scene's and a clip's sets and adds of the registers are checked here too, since they are what
the statements are usually written against.
"""

from llamatron.composition import file_format, limits
from llamatron.composition.checks import is_whole_number, listed
from llamatron.composition.file_format import Operator, StatementPart
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.setting import Checked
from llamatron.strings import errors

# What a number is divided by to learn whether it is odd.
PARITY = 2
NO_REMAINDER = 0
# The number a new statement is written with, the number a new division divides by, and the number nothing divides by.
NEW_NUMBER = 0
NEW_DIVISOR = 1
ZERO = 0
FIRST_PLACE = 0
LAST_PLACE_BACK = 1
# The parts each shape of statement holds besides its register and operator.
COMPARING_PARTS = (StatementPart.VALUE,)
ARITHMETIC_PARTS = (StatementPart.VALUE, StatementPart.COMPARISON, StatementPart.AGAINST)
EVERY_PART = (StatementPart.REGISTER, StatementPart.OPERATOR, *ARITHMETIC_PARTS)
# Where a statement's register stands among its parts, and what a statement read from a pattern's rows is called in a refusal nobody sees.
REGISTER_PLACE = 0
NO_NAME = ''

# How each comparison answers for two integers.
COMPARED = {
    Operator.LESS: lambda left, right: left < right,
    Operator.AT_MOST: lambda left, right: left <= right,
    Operator.SAME: lambda left, right: left == right,
    Operator.AT_LEAST: lambda left, right: left >= right,
    Operator.MORE: lambda left, right: left > right,
    Operator.DIFFERENT: lambda left, right: left != right,
}
# What each sum makes of two integers.
WORKED_OUT = {
    Operator.PLUS: lambda left, right: left + right,
    Operator.MINUS: lambda left, right: left - right,
    Operator.TIMES: lambda left, right: left * right,
    Operator.REMAINDER: lambda left, right: left % right,
    Operator.DIVIDED_BY: lambda left, right: left // right,
}


def parts_of(operator):
    """Return the parts a statement with an operator holds after it, in order: none for odd and even, a value for a comparison, and a value, a comparison and what to compare with for a sum."""
    if operator in file_format.PARITY_OPERATORS:
        return ()
    return ARITHMETIC_PARTS if operator in file_format.ARITHMETIC_OPERATORS else COMPARING_PARTS


def new_statement(register):
    """Return the statement a line starts as once it is given a register: the register less than 0, which is then edited."""
    return {StatementPart.REGISTER: register, StatementPart.OPERATOR: Operator.LESS, StatementPart.VALUE: NEW_NUMBER}


def with_operator(*, statement, operator):
    """Return a statement given another operator, keeping each part the new operator still takes and filling in the rest, so that no statement is left half written."""
    changed = {StatementPart.REGISTER: statement[StatementPart.REGISTER], StatementPart.OPERATOR: operator}
    starting = {StatementPart.VALUE: NEW_DIVISOR if operator in file_format.DIVIDING_OPERATORS else NEW_NUMBER, StatementPart.COMPARISON: Operator.SAME, StatementPart.AGAINST: NEW_NUMBER}
    for part in parts_of(operator):
        changed[part] = statement.get(part, starting[part])
    if operator in file_format.DIVIDING_OPERATORS and changed[StatementPart.VALUE] == ZERO:
        changed[StatementPart.VALUE] = starting[StatementPart.VALUE]
    return changed


def _is_number(value):
    return is_whole_number(value) and -limits.MAX_STATEMENT_NUMBER <= value <= limits.MAX_STATEMENT_NUMBER


def _check_number(*, name, part, value):
    """Refuse what a statement works with unless it is a register's name or an integer within the limits."""
    if value not in file_format.STATEMENT_NAMES and not _is_number(value):
        raise InvalidValue(errors.ERR_STATEMENT_BAD_NUMBER.format(
            name=name, part=part, lowest=-limits.MAX_STATEMENT_NUMBER, highest=limits.MAX_STATEMENT_NUMBER, value=value))


def check_statement(*, name, statement):
    """Refuse one statement unless it is one of the three shapes, whole."""
    if not isinstance(statement, dict) or not set(statement) <= set(EVERY_PART):
        raise InvalidValue(errors.ERR_BAD_STATEMENT.format(name=name, value=statement))
    if statement.get(StatementPart.REGISTER) not in file_format.STATEMENT_NAMES:
        raise InvalidValue(errors.ERR_STATEMENT_BAD_REGISTER.format(name=name, names=listed(file_format.STATEMENT_NAMES), value=statement.get(StatementPart.REGISTER)))
    operator = statement.get(StatementPart.OPERATOR)
    if operator not in file_format.OPERATORS:
        raise InvalidValue(errors.ERR_STATEMENT_BAD_OPERATOR.format(name=name, choices=listed(file_format.OPERATORS), value=operator))
    wanted = parts_of(operator)
    for part in ARITHMETIC_PARTS:
        if part in statement and part not in wanted:
            raise InvalidValue(errors.ERR_STATEMENT_EXTRA_PART.format(name=name, operator=operator, part=part, value=statement[part]))
    if StatementPart.VALUE in wanted:
        _check_number(name=name, part=StatementPart.VALUE, value=statement.get(StatementPart.VALUE))
        if operator in file_format.DIVIDING_OPERATORS and statement[StatementPart.VALUE] == ZERO:
            raise InvalidValue(errors.ERR_STATEMENT_DIVIDES_BY_ZERO.format(name=name))
    if StatementPart.COMPARISON in wanted:
        if statement.get(StatementPart.COMPARISON) not in file_format.RESULT_COMPARISONS:
            raise InvalidValue(errors.ERR_STATEMENT_BAD_COMPARISON.format(name=name, choices=listed(file_format.RESULT_COMPARISONS), value=statement.get(StatementPart.COMPARISON)))
        _check_number(name=name, part=StatementPart.AGAINST, value=statement.get(StatementPart.AGAINST))


def statement_of(parts):
    """Return the statement made of parts in the order they are written, None for a part left out, or None when the parts name no register or make no whole statement, as rows written by hand can."""
    if parts[REGISTER_PLACE] is None:
        return None
    statement = {part: value for part, value in zip(EVERY_PART, parts) if value is not None}
    try:
        check_statement(name=NO_NAME, statement=statement)
    except InvalidValue:
        return None
    return statement


def statements_setting(name):
    """Return the description of a setting that holds a table of statements, under the name a file gives it."""
    def check(value):
        if not isinstance(value, list) or len(value) > limits.MAX_STATEMENTS:
            raise InvalidValue(errors.ERR_TOO_MANY_STATEMENTS.format(name=name, most=limits.MAX_STATEMENTS, value=value))
        for statement in value:
            check_statement(name=name, statement=statement)
    return Checked(name=name, check=check)


def register_values_setting(name):
    """Return the description of a setting that gives some of the registers an integer each: what to set them to, or what to add to them."""
    def check(value):
        right = isinstance(value, dict) and all(
            register in file_format.REGISTER_NAMES and is_whole_number(amount) and limits.MIN_REGISTER_VALUE <= amount <= limits.MAX_REGISTER_VALUE
            for register, amount in value.items())
        if not right:
            raise InvalidValue(errors.ERR_BAD_REGISTER_VALUES.format(
                name=name, names=listed(file_format.REGISTER_NAMES), lowest=limits.MIN_REGISTER_VALUE, highest=limits.MAX_REGISTER_VALUE, value=value))
    return Checked(name=name, check=check)


def with_register_value(*, values, register, value):
    """Return what a setting of register values holds once one register is given a value, or None for the register to be left out; None when nothing is left."""
    if register not in file_format.REGISTER_NAMES:
        raise InvalidValue(errors.ERR_NO_SUCH_REGISTER.format(name=register, names=listed(file_format.REGISTER_NAMES)))
    held = dict(values or {})
    if value is None:
        held.pop(register, None)
    else:
        held[register] = value
    return {name: held[name] for name in file_format.REGISTER_NAMES if name in held} or None


def with_statement(*, statements, place, statement):
    """Return a table with the statement at a place replaced, or removed for None; a place just past the last adds one. None when no statement is left."""
    table = [dict(each) for each in statements or []]
    last = min(len(table), limits.MAX_STATEMENTS - LAST_PLACE_BACK)
    if not FIRST_PLACE <= place <= last:
        raise InvalidValue(errors.ERR_NO_SUCH_STATEMENT.format(place=place, most=last))
    if statement is None:
        if place < len(table):
            table.pop(place)
    elif place == len(table):
        table.append(dict(statement))
    else:
        table[place] = dict(statement)
    return table or None


def _number(*, written, values):
    """Return what a statement works with as an integer: a register's value, or the number written."""
    return values.get(written, 0) if written in file_format.STATEMENT_NAMES else written


def is_true(*, statement, values):
    """Return whether one statement holds for the registers' values."""
    held = values.get(statement[StatementPart.REGISTER], 0)
    operator = statement[StatementPart.OPERATOR]
    if operator in file_format.PARITY_OPERATORS:
        return (held % PARITY != NO_REMAINDER) == (operator == Operator.ODD)
    value = _number(written=statement[StatementPart.VALUE], values=values)
    if operator in file_format.COMPARING_OPERATORS:
        return COMPARED[operator](held, value)
    if operator in file_format.DIVIDING_OPERATORS and value == ZERO:
        return True
    against = _number(written=statement[StatementPart.AGAINST], values=values)
    return COMPARED[statement[StatementPart.COMPARISON]](WORKED_OUT[operator](held, value), against)


def any_true(*, statements, values):
    """Return whether any statement of a table holds for the registers' values. A table with no statement never does."""
    return any(is_true(statement=statement, values=values) for statement in statements)
