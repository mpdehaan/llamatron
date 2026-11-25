// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Bypass When on a settings page (the Python pages/statements.py and forms/statement_rows.py): a line for each statement
//! a table may hold, each a row of cells as wide as its statement, drawn as a grid of five columns, each as wide as its
//! widest value, so that nothing moves as a line changes.

use crate::forms::nodes::{Drawn, Field};
use llamatron_model::file::data::Data;
use llamatron_model::schema::generated::file_format::{ARITHMETIC_OPERATORS, OPERATORS, PARITY_OPERATORS, RESULT_COMPARISONS, VALUE_NAMES};
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

fn chosen(id: usize, title: &str, current: &str) -> Field {
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
    let parts: &[&str] = if PARITY_OPERATORS.contains(&operator.as_str()) {
        &[]
    } else if ARITHMETIC_OPERATORS.contains(&operator.as_str()) {
        &["value", "comparison", "against"]
    } else {
        &["value"]
    };
    for (place, part) in parts.iter().enumerate() {
        let id = first_id + 2 + place;
        let value = text_of(statement.get(part));
        if *part == "comparison" {
            cells.push(chosen(id, labels::MSG_STATEMENT_COMPARISON_TITLE, &value));
        } else {
            cells.push(chosen(id, labels::MSG_STATEMENT_VALUE_TITLE, &value));
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
