// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A pattern as a set stores it (the Python model/objects/pattern.py): its count of steps, its settings, and its rows, each a
//! list of a value a step, kept as each row's kind keeps them (model/schema/row_descriptions.py) and written back leaving out
//! the rows with nothing in them, so that files stay short.

use crate::file::data::Data;
use crate::objects::holder::{in_table, passed_over, Holder};
use crate::schema::checking::plain_data;
use crate::schema::checking::InvalidValue;
use crate::schema::generated::file_format::{PatternSetting, PATTERN_ROWS};
use crate::schema::generated::limits::MIN_STEPS;
use crate::schema::generated::rows::{RowKind, ROWS};
use crate::schema::generated::settings::{Plain, PATTERN};
use llamatron_strings::errors;
use llamatron_strings::named;

#[derive(Clone, Debug, PartialEq)]
pub struct Pattern {
    steps: i128,
    settings: Holder,
    rows: Vec<Option<Vec<Data>>>,
}

fn kind_of(row: &str) -> RowKind {
    ROWS.iter().find(|(name, _)| *name == row).map(|(_, kind)| *kind).unwrap_or(RowKind::Plain)
}

/// Whether a value is what Python takes as true.
fn truthy(value: &Data) -> bool {
    !matches!(value, Data::Null | Data::Bool(false)) && *value != Data::Whole(0) && *value != Data::Float(0.0) && *value != Data::text("")
}

/// A step's chosen set as a pattern keeps it: the chosen in the choices' order, or nothing where none is chosen.
fn in_order(chosen: &Data, choices: &[Plain]) -> Data {
    let items = chosen.as_list().unwrap_or(&[]);
    let ordered: Vec<Data> = choices.iter().map(plain_data).filter(|choice| items.contains(choice)).collect();
    if ordered.is_empty() {
        return Data::Null;
    }
    Data::List(ordered)
}

/// A row's values as the pattern keeps them.
fn read_row(row: &str, values: &[Data]) -> Vec<Data> {
    match kind_of(row) {
        RowKind::ChosenSet(choices) => values
            .iter()
            .map(|value| if value.is_null() { Data::Null } else { in_order(value, choices) })
            .collect(),
        _ => values.to_vec(),
    }
}

fn blank(row: &str) -> Data {
    match kind_of(row) {
        RowKind::Toggle => Data::Bool(false),
        _ => Data::Null,
    }
}

/// Whether a row has any step that isn't its blank, which is what makes it worth writing.
fn holds_something(row: &str, values: &[Data]) -> bool {
    let blank = blank(row);
    values.iter().any(|value| !value.is_null() && *value != blank)
}

/// A row as a file writes it: an on or off row as true and false.
fn written_row(row: &str, values: &[Data]) -> Vec<Data> {
    match kind_of(row) {
        RowKind::Toggle => values.iter().map(|value| Data::Bool(truthy(value))).collect(),
        _ => values.to_vec(),
    }
}

impl Pattern {
    /// A pattern from a file's data, its steps checked and its settings, and each row a list of a value a step.
    pub fn from_data(data: &Data) -> Result<Pattern, InvalidValue> {
        if !matches!(data, Data::Map(_)) {
            return Err(InvalidValue::new(errors::ERR_PATTERN_EXPECTED_SETTINGS.to_string()));
        }
        let data = passed_over(data, &|name| {
            name == PatternSetting::STEPS || in_table(PATTERN, name) || PATTERN_ROWS.contains(&name)
        });
        let steps = data
            .get(PatternSetting::STEPS)
            .and_then(Data::as_whole)
            .filter(|steps| *steps >= MIN_STEPS as i128);
        let Some(steps) = steps else {
            let found = data.get(PatternSetting::STEPS).cloned().unwrap_or(Data::Null);
            return Err(InvalidValue::new(named(
                errors::ERR_BAD_STEPS,
                &[("lowest", MIN_STEPS.into()), ("value", (&found).into())],
            )));
        };
        let settings = Holder::read(PATTERN, &data, None, &[])?;
        let mut rows = Vec::with_capacity(PATTERN_ROWS.len());
        for row in PATTERN_ROWS {
            let values = match data.get(row) {
                None | Some(Data::Null) => None,
                Some(Data::List(values)) if values.len() as i128 == steps => Some(read_row(row, values)),
                Some(found) => {
                    return Err(InvalidValue::new(named(
                        errors::ERR_ROW_WRONG_LENGTH,
                        &[("row", (*row).into()), ("steps", (steps as i64).into()), ("value", found.into())],
                    )));
                }
            };
            rows.push(values);
        }
        Ok(Pattern { steps, settings, rows })
    }

    pub fn get_steps(&self) -> i128 {
        self.steps
    }

    pub fn is_drum(&self) -> bool {
        self.settings.get(PatternSetting::DRUM).is_some_and(truthy)
    }

    pub fn get_written(&self, name: &str) -> Option<&Data> {
        self.settings.get(name)
    }

    /// A row's values, or None for a row the pattern doesn't have.
    pub fn row(&self, row: &str) -> Option<&[Data]> {
        let place = PATTERN_ROWS.iter().position(|name| *name == row)?;
        self.rows[place].as_deref()
    }

    /// Its steps, its settings and its rows, leaving out rows with nothing in them.
    pub fn to_data(&self) -> Data {
        let mut pairs = vec![(Data::text(PatternSetting::STEPS), Data::Whole(self.steps))];
        pairs.extend(self.settings.written());
        for (row, values) in PATTERN_ROWS.iter().zip(&self.rows) {
            if let Some(values) = values.as_ref().filter(|values| holds_something(row, values)) {
                pairs.push((Data::text(row), Data::List(written_row(row, values))));
            }
        }
        Data::Map(pairs)
    }
}
