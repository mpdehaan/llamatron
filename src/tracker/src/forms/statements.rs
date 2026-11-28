// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The statements about the draws that the pattern editor's When rows hold (the Python forms/statement_rows.py): how wide
//! each part is drawn, so that nothing moves as a line changes, and how a statement is started and changed part by part.

use llamatron_model::file::data::Data;
use llamatron_model::schema::generated::file_format::{
    Operator, ARITHMETIC_OPERATORS, DIVIDING_OPERATORS, OPERATORS, PARITY_OPERATORS, RESULT_COMPARISONS, VALUE_NAMES,
};
use llamatron_model::schema::generated::limits::MAX_STATEMENT_NUMBER;
use llamatron_names::file_format;
use llamatron_strings::labels;

/// The widths of a statement's parts: its register, its operator, a value, a comparison and what is compared with.
pub fn part_widths() -> [usize; 5] {
    let register = labels::MSG_STATEMENT_IGNORED.chars().count();
    let operator = OPERATORS.iter().map(|each| each.chars().count()).max().unwrap_or(0);
    let number = format!("{}", -MAX_STATEMENT_NUMBER).len();
    let value = VALUE_NAMES.iter().map(|each| each.len()).max().unwrap_or(0).max(number);
    let comparison = RESULT_COMPARISONS.iter().map(|each| each.chars().count()).max().unwrap_or(0);
    [register, operator, value, comparison, value]
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
const REGISTER: &str = file_format::StatementPart::REGISTER;
const OPERATOR: &str = file_format::StatementPart::OPERATOR;
const VALUE: &str = file_format::StatementPart::VALUE;
const COMPARISON: &str = file_format::StatementPart::COMPARISON;
const AGAINST: &str = file_format::StatementPart::AGAINST;
/// What a new statement compares with, and what a dividing one divides by.
const NEW_NUMBER: i128 = 0;
const NEW_DIVISOR: i128 = 1;

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
