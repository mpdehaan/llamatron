// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Statements about the draws (the Python model/objects/conditions.py): a draw compared with a number or another draw, asked
//! whether it is odd or even, or a sum worked out first and its result compared. Every sum is in integers: a division rounds
//! down and a remainder takes the sign of what divides; a draw that divides and holds 0 makes the statement true.

use crate::registers::{draw_place, Values};
use llamatron_model::file::data::Data;
use llamatron_names::file_format;

/// What a value is divided by to tell odd from even.
const PARITY_DIVISOR: i64 = 2;

#[derive(Clone, Debug, PartialEq)]
enum Operand {
    Number(i64),
    Draw(usize),
}

#[derive(Clone, Debug, PartialEq)]
pub struct Statement {
    register: usize,
    operator: String,
    value: Option<Operand>,
    comparison: Option<String>,
    against: Option<Operand>,
}

const COMPARING: &[&str] = &["<", "<=", "=", ">=", ">", "!="];
const ARITHMETIC: &[&str] = &["+", "-", "%", "*", "/"];
const PARITY: &[&str] = &["odd", "even"];
const MAX_STATEMENT_NUMBER: i64 = 999;

fn operand(value: &Data) -> Option<Operand> {
    if let Some(place) = value.as_str().and_then(draw_place) {
        return Some(Operand::Draw(place));
    }
    let number = value.as_whole()? as i64;
    (-MAX_STATEMENT_NUMBER..=MAX_STATEMENT_NUMBER)
        .contains(&number)
        .then_some(Operand::Number(number))
}

/// A division that rounds down, as Python's // does.
fn floor_divided(first: i64, second: i64) -> i64 {
    let quotient = first / second;
    if first % second != 0 && ((first < 0) != (second < 0)) {
        return quotient - 1;
    }
    quotient
}

/// A remainder that takes the sign of what divides, as Python's % does.
fn python_mod(first: i64, second: i64) -> i64 {
    first - second * floor_divided(first, second)
}

fn compared(comparison: &str, first: i64, second: i64) -> bool {
    match comparison {
        "<" => first < second,
        "<=" => first <= second,
        "=" => first == second,
        ">=" => first >= second,
        ">" => first > second,
        _ => first != second,
    }
}

impl Statement {
    /// The statement a step's parts make in the order they are written, a part left out None, or None where they name no
    /// draw or make no whole statement.
    pub fn of(parts: &[Option<&Data>]) -> Option<Statement> {
        let register = draw_place(parts[0]?.as_str()?)?;
        let operator = parts.get(1).copied().flatten()?.python_str();
        let present = |place: usize| parts.get(place).copied().flatten();
        let statement = if PARITY.contains(&operator.as_str()) {
            if present(2).is_some() || present(3).is_some() || present(4).is_some() {
                return None;
            }
            Statement {
                register,
                operator,
                value: None,
                comparison: None,
                against: None,
            }
        } else if COMPARING.contains(&operator.as_str()) {
            if present(3).is_some() || present(4).is_some() {
                return None;
            }
            Statement {
                register,
                operator,
                value: Some(operand(present(2)?)?),
                comparison: None,
                against: None,
            }
        } else if ARITHMETIC.contains(&operator.as_str()) {
            let value = operand(present(2)?)?;
            if (operator == "%" || operator == "/") && value == Operand::Number(0) {
                return None;
            }
            let comparison = present(3)?.python_str();
            if !COMPARING.contains(&comparison.as_str()) {
                return None;
            }
            Statement {
                register,
                operator,
                value: Some(value),
                comparison: Some(comparison),
                against: Some(operand(present(4)?)?),
            }
        } else {
            return None;
        };
        Some(statement)
    }

    fn number(operand: &Option<Operand>, values: &Values) -> i64 {
        match operand {
            Some(Operand::Draw(place)) => values[*place],
            Some(Operand::Number(number)) => *number,
            None => 0,
        }
    }

    /// Whether the statement holds for the draws' values.
    pub fn is_true(&self, values: &Values) -> bool {
        let held = values[self.register];
        if PARITY.contains(&self.operator.as_str()) {
            return (held.rem_euclid(PARITY_DIVISOR) != 0) == (self.operator == file_format::Operator::ODD);
        }
        let value = Statement::number(&self.value, values);
        if COMPARING.contains(&self.operator.as_str()) {
            return compared(&self.operator, held, value);
        }
        if (self.operator == "%" || self.operator == "/") && value == 0 {
            return true;
        }
        let worked = match self.operator.as_str() {
            "+" => held + value,
            "-" => held - value,
            "*" => held * value,
            "%" => python_mod(held, value),
            _ => floor_divided(held, value),
        };
        compared(self.comparison.as_deref().unwrap_or("="), worked, Statement::number(&self.against, values))
    }

    /// The draws the statement reads, by their places, in the draws' order.
    pub fn draws_read(&self) -> Vec<usize> {
        let mut read = vec![self.register];
        for operand in [&self.value, &self.against] {
            if let Some(Operand::Draw(place)) = operand {
                read.push(*place);
            }
        }
        read.sort();
        read.dedup();
        read
    }
}
