// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Bypass When on a settings page (the Python pages/statements.py and forms/statement_rows.py): a line for each statement
//! a table may hold, each a row of cells as wide as its statement, drawn as a grid of five columns, each as wide as its
//! widest value, so that nothing moves as a line changes.

use crate::forms::nodes::{Drawn, Edit, Field};
use llamatron_model::file::data::Data;
use llamatron_model::schema::generated::file_format::{
    Operator, ARITHMETIC_OPERATORS, DIVIDING_OPERATORS, DRAW_NAMES, OPERATORS, PARITY_OPERATORS, RESULT_COMPARISONS, VALUE_NAMES,
};
use llamatron_model::schema::generated::limits::{MAX_STATEMENTS, MAX_STATEMENT_NUMBER};
use llamatron_strings::{labels, legends};

/// The widths of a statement's parts: its register, its operator, a value, a comparison and what is compared with.
pub fn part_widths() -> [usize; 5] {
    let register = labels::MSG_STATEMENT_IGNORED.chars().count();
    let operator = OPERATORS.iter().map(|each| each.chars().count()).max().unwrap_or(0);
    let number = format!("{}", -MAX_STATEMENT_NUMBER).len();
    let value = VALUE_NAMES.iter().map(|each| each.len()).max().unwrap_or(0).max(number);
    let comparison = RESULT_COMPARISONS.iter().map(|each| each.chars().count()).max().unwrap_or(0);
    [register, operator, value, comparison, value]
}

fn text_of(value: Option<&Data>) -> String {
    match value {
        Some(Data::Text(text)) => text.clone(),
        Some(Data::Whole(number)) => number.to_string(),
        Some(Data::Float(number)) => number.to_string(),
        _ => String::new(),
    }
}

/// A cell that steps through a list and picks from it: a line's register, its operator or its comparison.
fn chosen(id: usize, title: &str, current: &str) -> Field {
    Field::custom(id, title, current)
        .with_adjust()
        .with_enter(legends::What::CHOOSE)
        .with_clear(legends::What::CLEAR)
}

/// A cell that holds a number or names a draw, picked or typed but never stepped.
fn valued(id: usize, title: &str, current: &str) -> Field {
    Field::custom(id, title, current)
        .with_enter(legends::What::CHOOSE)
        .with_clear(legends::What::CLEAR)
}

/// The cells of one line: the register alone, or ignored, while the line holds no statement; then its operator and the
/// parts the operator takes.
fn cells_of(first_id: usize, statement: Option<&Data>) -> Vec<Field> {
    let Some(statement) = statement else {
        return vec![chosen(first_id, labels::MSG_STATEMENT_REGISTER_TITLE, labels::MSG_STATEMENT_IGNORED)];
    };
    let register = text_of(statement.get("register"));
    let operator = text_of(statement.get("operator"));
    let mut cells = vec![
        chosen(first_id, labels::MSG_STATEMENT_REGISTER_TITLE, &register),
        chosen(first_id + 1, labels::MSG_STATEMENT_OPERATOR_TITLE, &operator),
    ];
    for (place, part) in parts_of(&operator).iter().enumerate() {
        let id = first_id + 2 + place;
        let value = text_of(statement.get(part));
        if *part == "comparison" {
            cells.push(chosen(id, labels::MSG_STATEMENT_COMPARISON_TITLE, &value));
        } else {
            cells.push(valued(id, labels::MSG_STATEMENT_VALUE_TITLE, &value));
        }
    }
    cells
}

/// A table's lines, a line for each statement it may hold; table is the table's place among the page's tables, which
/// sets each line's label apart, and first_id the first id the lines' cells take.
pub fn statement_lines(table: usize, statements: &[Data], first_id: usize) -> Vec<Field> {
    let most = MAX_STATEMENTS as usize;
    (0..most)
        .map(|place| {
            let row_id = first_id + place * 10;
            let label = labels::MSG_STATEMENT_LINE_LABEL.repeat(table * most + place + 1);
            let mut row = Field::cells(row_id, &label, cells_of(row_id + 1, statements.get(place)));
            row.drawn = Drawn::StatementRow {
                first: place == 0,
                last: place == most - 1,
            };
            row
        })
        .collect()
}

/// The parts a statement holds after its operator, in order: none for odd and even, a value for a comparison, and a value,
/// a comparison and what to compare with for a sum.
fn parts_of(operator: &str) -> &'static [&'static str] {
    if PARITY_OPERATORS.contains(&operator) {
        &[]
    } else if ARITHMETIC_OPERATORS.contains(&operator) {
        &[VALUE, COMPARISON, AGAINST]
    } else {
        &[VALUE]
    }
}

// The parts of a statement, as the file names them.
const REGISTER: &str = "register";
const OPERATOR: &str = "operator";
const VALUE: &str = "value";
const COMPARISON: &str = "comparison";
const AGAINST: &str = "against";
/// What a new statement compares with, and what a dividing one divides by.
const NEW_NUMBER: i128 = 0;
const NEW_DIVISOR: i128 = 1;
/// What choosing a number to type stands for in a value's picker.
const NUMBER_CHOSEN: &str = "number";

/// What a key did to a table of statements: a dialog to open, the statement to store at a place (None to remove it), a
/// refusal to say, or nothing.
pub enum StatementChange {
    Ask(Edit),
    Store { place: usize, statement: Option<Data> },
    Refuse(&'static str),
    Nothing,
}

/// What an edit to one of a table's cells does, the table's cells taking ids from first_id as statement_lines gives them.
pub fn statement_change(statements: &[Data], first_id: usize, id: usize, edit: &Edit) -> StatementChange {
    let Some(offset) = id.checked_sub(first_id + 1) else {
        return StatementChange::Nothing;
    };
    let (place, cell) = (offset / 10, offset % 10);
    if place >= MAX_STATEMENTS as usize {
        return StatementChange::Nothing;
    }
    // A line past the table's last statement writes the next one, since a table keeps no gaps.
    let at = place.min(statements.len());
    let statement = statements.get(place);
    if *edit == Edit::Clear {
        return match statement {
            Some(_) => StatementChange::Store { place: at, statement: None },
            None => StatementChange::Nothing,
        };
    }
    match (cell, statement) {
        (0, _) => register_change(statement, at, edit),
        (_, None) => StatementChange::Nothing,
        (1, Some(statement)) => {
            let current = text_of(statement.get(OPERATOR));
            match chosen_from(labels::MSG_STATEMENT_OPERATOR_TITLE, OPERATORS, &current, edit) {
                Chosen::Ask(asked) => StatementChange::Ask(asked),
                Chosen::Value(operator) => store(at, with_operator(statement, &operator)),
                Chosen::Nothing => StatementChange::Nothing,
            }
        }
        (part_cell, Some(statement)) => {
            let operator = text_of(statement.get(OPERATOR));
            let Some(part) = parts_of(&operator).get(part_cell - 2).copied() else {
                return StatementChange::Nothing;
            };
            if part == COMPARISON {
                let current = text_of(statement.get(COMPARISON));
                return match chosen_from(labels::MSG_STATEMENT_COMPARISON_TITLE, RESULT_COMPARISONS, &current, edit) {
                    Chosen::Ask(asked) => StatementChange::Ask(asked),
                    Chosen::Value(comparison) => store(at, with_part(statement, part, Data::text(&comparison))),
                    Chosen::Nothing => StatementChange::Nothing,
                };
            }
            let divides = part == VALUE && DIVIDING_OPERATORS.contains(&operator.as_str());
            value_change(statement, at, part, divides, edit)
        }
    }
}

/// What a step or a pick of a list's value comes to: a picker to open, the value taken, or nothing.
enum Chosen {
    Ask(Edit),
    Value(String),
    Nothing,
}

/// A list's cell edited: stepped along the list, stopping at its ends, a picker opened on ENTER, or a value picked.
fn chosen_from(title: &str, choices: &[&str], current: &str, edit: &Edit) -> Chosen {
    let place = choices.iter().position(|choice| *choice == current).unwrap_or(choices.len() / 2);
    match edit {
        Edit::Adjust(offset) => {
            let moved = (place as i64 + offset).clamp(0, choices.len() as i64 - 1) as usize;
            Chosen::Value(choices[moved].to_string())
        }
        Edit::Enter => Chosen::Ask(Edit::AskChoice {
            title: title.to_string(),
            options: choices.iter().map(|choice| choice.to_string()).collect(),
            current: place,
            choices: choices.iter().map(|choice| choice.to_string()).collect(),
        }),
        Edit::Choice(chosen) => Chosen::Value(chosen.clone()),
        _ => Chosen::Nothing,
    }
}

/// The register's cell edited: ignored first, then each draw; a line given a register starts as a new statement.
fn register_change(statement: Option<&Data>, at: usize, edit: &Edit) -> StatementChange {
    let mut choices = vec![labels::MSG_STATEMENT_IGNORED];
    choices.extend(DRAW_NAMES.iter().copied());
    let current = statement.map_or(labels::MSG_STATEMENT_IGNORED.to_string(), |statement| text_of(statement.get(REGISTER)));
    let register = match edit {
        Edit::Enter => {
            let grouped = Grouped::of(vec![
                (None, vec![labels::MSG_STATEMENT_IGNORED]),
                (Some(labels::MSG_PICKER_DRAWS_HEADING), DRAW_NAMES.to_vec()),
            ]);
            return StatementChange::Ask(grouped.asking(labels::MSG_STATEMENT_REGISTER_TITLE, &current));
        }
        edit => match chosen_from(labels::MSG_STATEMENT_REGISTER_TITLE, &choices, &current, edit) {
            Chosen::Value(register) => register,
            _ => return StatementChange::Nothing,
        },
    };
    match (register == labels::MSG_STATEMENT_IGNORED, statement) {
        (true, Some(_)) => StatementChange::Store { place: at, statement: None },
        (true, None) => StatementChange::Nothing,
        (false, None) => store(at, new_statement(&register)),
        (false, Some(statement)) => store(at, with_part(statement, REGISTER, Data::text(&register))),
    }
}

/// A value's cell edited: ENTER offers a number to type or a draw, under their headings; a number typed is refused where
/// it would divide by zero.
fn value_change(statement: &Data, at: usize, part: &str, divides: bool, edit: &Edit) -> StatementChange {
    let current = text_of(statement.get(part));
    let names_a_value = VALUE_NAMES.contains(&current.as_str());
    match edit {
        Edit::Enter => {
            let grouped = Grouped::of(vec![
                (Some(labels::MSG_PICKER_CONSTANT_HEADING), vec![labels::MSG_STATEMENT_NUMBER_CHOICE]),
                (Some(labels::MSG_PICKER_DRAWS_HEADING), DRAW_NAMES.to_vec()),
            ]);
            let opening = if names_a_value { current.as_str() } else { NUMBER_CHOSEN };
            StatementChange::Ask(grouped.asking(labels::MSG_STATEMENT_VALUE_TITLE, opening))
        }
        Edit::Choice(chosen) if chosen == NUMBER_CHOSEN => {
            let typed = if names_a_value {
                0
            } else {
                statement.get(part).and_then(Data::as_whole).map_or(0, |whole| whole as i64)
            };
            StatementChange::Ask(Edit::AskNumber {
                title: labels::MSG_STATEMENT_VALUE_TITLE.to_string(),
                value: typed,
                lowest: Some(-MAX_STATEMENT_NUMBER),
                highest: Some(MAX_STATEMENT_NUMBER),
            })
        }
        Edit::Choice(chosen) => store(at, with_part(statement, part, Data::text(chosen))),
        Edit::Number(0) if divides => StatementChange::Refuse(llamatron_strings::errors::ERR_CANNOT_DIVIDE_BY_ZERO),
        Edit::Number(number) => store(at, with_part(statement, part, Data::Whole(*number as i128))),
        _ => StatementChange::Nothing,
    }
}

/// A picker's choices in groups, each under a heading or none, with a blank line between groups; the headings and the
/// blank lines are never chosen.
struct Grouped {
    shown: Vec<String>,
    values: Vec<String>,
    headings: Vec<usize>,
}

impl Grouped {
    /// The groups laid out as the picker shows them, each choice standing for itself.
    fn of(groups: Vec<(Option<&str>, Vec<&str>)>) -> Grouped {
        let mut grouped = Grouped {
            shown: Vec::new(),
            values: Vec::new(),
            headings: Vec::new(),
        };
        for (place, (heading, choices)) in groups.into_iter().enumerate() {
            if place > 0 {
                grouped.heading("");
            }
            if let Some(heading) = heading {
                grouped.heading(heading);
            }
            for choice in choices {
                grouped.shown.push(choice.to_string());
                grouped.values.push(choice.to_string());
            }
        }
        grouped
    }

    /// Add a line that is never chosen: a heading, or the blank line between groups.
    fn heading(&mut self, text: &str) {
        self.headings.push(self.shown.len());
        self.shown.push(text.to_string());
        self.values.push(String::new());
    }

    /// The edit that asks for one of the choices, opening on the one that stands for current, or the first.
    fn asking(self, title: &str, current: &str) -> Edit {
        let opening = (0..self.values.len())
            .find(|place| !self.headings.contains(place) && self.values[*place] == current)
            .unwrap_or(0);
        Edit::AskGrouped {
            title: title.to_string(),
            options: self.shown,
            current: opening,
            choices: self.values,
            headings: self.headings,
        }
    }
}

/// The change that stores a statement at a place.
fn store(place: usize, statement: Data) -> StatementChange {
    StatementChange::Store {
        place,
        statement: Some(statement),
    }
}

/// The statement a line starts as once given a register: the register less than 0, which is then edited.
pub fn new_statement(register: &str) -> Data {
    Data::Map(vec![
        (Data::text(REGISTER), Data::text(register)),
        (Data::text(OPERATOR), Data::text(Operator::LESS)),
        (Data::text(VALUE), Data::Whole(NEW_NUMBER)),
    ])
}

/// A statement with one part changed, the others kept in their order.
pub fn with_part(statement: &Data, part: &str, value: Data) -> Data {
    let mut pairs: Vec<(Data, Data)> = statement.as_map().map(<[(Data, Data)]>::to_vec).unwrap_or_default();
    match pairs.iter_mut().find(|(key, _)| key.as_str() == Some(part)) {
        Some(pair) => pair.1 = value,
        None => pairs.push((Data::text(part), value)),
    }
    Data::Map(pairs)
}

/// A statement given another operator, keeping each part the new operator still takes and filling in the rest, so that no
/// statement is left half written.
pub fn with_operator(statement: &Data, operator: &str) -> Data {
    let divides = DIVIDING_OPERATORS.contains(&operator);
    let new_value = if divides { NEW_DIVISOR } else { NEW_NUMBER };
    let mut pairs = vec![
        (Data::text(REGISTER), statement.get(REGISTER).cloned().unwrap_or(Data::Null)),
        (Data::text(OPERATOR), Data::text(operator)),
    ];
    for part in parts_of(operator) {
        let starting = match *part {
            VALUE => Data::Whole(new_value),
            COMPARISON => Data::text(Operator::SAME),
            _ => Data::Whole(NEW_NUMBER),
        };
        let mut value = statement.get(part).cloned().unwrap_or(starting);
        if divides && *part == VALUE && value == Data::Whole(0) {
            value = Data::Whole(new_value);
        }
        pairs.push((Data::text(part), value));
    }
    Data::Map(pairs)
}

/// A table with the statement at a place replaced, removed for None, or added just past the last; None when no statement
/// is left.
pub fn with_statement(statements: &[Data], place: usize, statement: Option<Data>) -> Option<Data> {
    let mut table = statements.to_vec();
    match statement {
        None if place < table.len() => {
            table.remove(place);
        }
        None => {}
        Some(statement) if place >= table.len() => table.push(statement),
        Some(statement) => table[place] = statement,
    }
    (!table.is_empty()).then_some(Data::List(table))
}
