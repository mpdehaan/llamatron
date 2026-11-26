# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A row of a step's statement about the registers in the pattern editor: one of the five parts of a Stop When, Restart When or Mute When statement.

The five rows of a section are one statement stood on end, so each step holds one statement of
each kind: the register, the operator, a number or a register, and after a sum the comparison of
its result and what the result is compared with. A row writes its part through the pattern's
one setter of a whole statement, so that no step is left holding half of one.
"""

from llamatron.interface.forms import grouped_choices
from llamatron.interface.forms.grouped_choices import number_or_names, value_groups
from llamatron.interface.tracker import key_table, keybindings
from llamatron.interface.tracker.components.pattern_row import PatternRow
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.dialogs.prompt_dialog import PromptDialog
from llamatron.model.objects import conditions
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import StatementPart, StepStatement
from llamatron.user_strings import errors, labels, marks

# The first step, which cannot start the pattern over.
FIRST_STEP = 0
# What a number starts from when the part holds a register, and the number a statement may not divide by.
ZERO = 0
# The parts chosen from a list, with the list and the picker's title, and the parts that hold a number or a register.
CHOSEN_PARTS = {
    StatementPart.REGISTER: (grouped_choices.VALUE_NAMES_IN_ORDER, labels.MSG_STATEMENT_REGISTER_TITLE),
    StatementPart.OPERATOR: (file_format.OPERATORS, labels.MSG_STATEMENT_OPERATOR_TITLE),
    StatementPart.COMPARISON: (file_format.RESULT_COMPARISONS, labels.MSG_STATEMENT_COMPARISON_TITLE),
}


class StatementRow(PatternRow):
    """ENTER chooses the part from a list, Space goes to the next choice or number, [ and ] step, and Bksp takes the step's whole statement away.

    A step with no statement can take only a register, which starts one; the other rows show
    the light slash there, as does a part the statement's operator has no use for.
    """

    KEYS = keybindings.StatementRow

    __slots__ = ('kind', 'part')

    def __init__(self, *, editor, name):
        super().__init__(editor=editor, name=name)
        self.kind, self.part = file_format.STATEMENT_OF_ROW[name]

    def on_rests(self):
        return True

    def statement(self, *, step=None):
        """Return the statement of the row's kind on a step, or None."""
        return self.editor.pattern().get_statement(kind=self.kind, step=self.editor.step if step is None else step)

    def blocked(self, *, step=None):
        place = self.editor.step if step is None else step
        if self.kind == StepStatement.RESTART and place == FIRST_STEP:
            return True
        if self.part == StatementPart.REGISTER:
            return False
        statement = self.statement(step=place)
        return statement is None or self.part not in statement

    def cell_text(self, *, step):
        statement = self.statement(step=step)
        return marks.MSG_UNSET_MARK if statement is None else str(statement[self.part])

    def keys(self):
        return [
            self.bind(self.KEYS.CHOOSE, action=self.choose),
            self.bind(self.KEYS.NEXT, action=lambda: self.nudge(key_table.STEP_FORWARD)),
            *self.adjust_keys(),
            self.bind(self.KEYS.CLEAR, action=lambda: self.store(None)),
        ]

    def store(self, statement):
        self.editor.document().change_pattern(self.editor.document().pattern(self.editor.item).set_statement, kind=self.kind, step=self.editor.step, statement=statement)

    def with_part(self, value):
        """Give the cursor's step this row's part, starting a statement where the step has none and taking the statement away for no register."""
        statement = self.statement()
        if self.part == StatementPart.REGISTER:
            if value is None:
                self.store(None)
            else:
                self.store(conditions.new_statement(value) if statement is None else {**statement, self.part: value})
        elif self.part == StatementPart.OPERATOR:
            self.store(conditions.with_operator(statement=statement, operator=value))
        elif self.divides(statement) and value == ZERO:
            self.editor.refuse(errors.ERR_CANNOT_DIVIDE_BY_ZERO)
        else:
            self.store({**statement, self.part: value})

    def divides(self, statement):
        """Return whether the row holds what the statement divides by, which cannot be 0."""
        return self.part == StatementPart.VALUE and statement[StatementPart.OPERATOR] in file_format.DIVIDING_OPERATORS

    def choices(self):
        """Return the row's choices in the order the keys step through them, a step with no register first on the register's row, or None on a row that holds a number or a register."""
        if self.part not in CHOSEN_PARTS:
            return None
        choices = list(CHOSEN_PARTS[self.part][0])
        return [None, *choices] if self.part == StatementPart.REGISTER else choices

    def nudge(self, offset):
        """Step to the next or the last choice, or a number up or down, stopping at each end."""
        statement = self.statement()
        choices = self.choices()
        if choices is not None:
            place = choices.index(None if statement is None else statement[self.part]) + offset
            if 0 <= place < len(choices):
                self.with_part(choices[place])
            return
        current = statement[self.part]
        number = ZERO if current in file_format.VALUE_NAMES else current + offset
        if -limits.MAX_STATEMENT_NUMBER <= number <= limits.MAX_STATEMENT_NUMBER:
            self.with_part(number)

    def choose(self):
        """Open the picker of the row's choices, or of a number to type and each register."""
        statement = self.statement()
        if self.part == StatementPart.REGISTER:
            grouped = value_groups(first=(None, [(labels.MSG_STATEMENT_IGNORED, None)]))
            current = None if statement is None else statement[self.part]
            self.editor.ask_grouped(title=labels.MSG_STATEMENT_REGISTER_TITLE, grouped=grouped, current=current, then=lambda place: self.with_part(grouped.value_at(place)))
            return
        if self.part in CHOSEN_PARTS:
            choices, title = CHOSEN_PARTS[self.part]
            current = choices.index(statement[self.part])
            self.editor.ask(dialog=ChoiceDialog(title=title, options=list(choices), current=current), then=lambda place: self.with_part(choices[place]))
            return
        current = statement[self.part]
        grouped = number_or_names()

        def picked(place):
            chosen = grouped.value_at(place)
            if chosen == grouped_choices.NUMBER_CHOSEN:
                self.ask_number(ZERO if current in file_format.VALUE_NAMES else current)
            else:
                self.with_part(chosen)
        opens_on = current if current in file_format.VALUE_NAMES else grouped_choices.NUMBER_CHOSEN
        self.editor.ask_grouped(title=labels.MSG_STATEMENT_VALUE_TITLE, grouped=grouped, current=opens_on, then=picked)

    def ask_number(self, current):
        lowest = -limits.MAX_STATEMENT_NUMBER
        highest = limits.MAX_STATEMENT_NUMBER

        def answered(text):
            try:
                number = int(text.strip())
            except ValueError:
                self.editor.refuse(errors.ERR_TYPED_NOT_AN_INTEGER.format(text=text))
                return
            if lowest <= number <= highest:
                self.with_part(number)
            else:
                self.editor.refuse(errors.ERR_OUT_OF_RANGE.format(number=number, low=lowest, high=highest))
        self.editor.ask(dialog=PromptDialog(title=labels.MSG_STATEMENT_VALUE_TITLE, value=current), then=answered)
