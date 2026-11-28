// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! What every stored object shares (the Python model/objects/llama_data.py, HoldsSettings): its settings, each a name of its
//! class's description table with the value the file writes for it, or nothing where the file leaves it out, checked as they
//! are read and written back in the table's order.

use crate::file::data::Data;
use crate::schema::checking::{check, Context, InvalidValue};
use crate::schema::generated::settings::Setting;
use llamatron_names::words;

/// A refusal of a file's data, with where in the file it was.
#[derive(Clone, Debug, PartialEq)]
pub struct SongFileError {
    pub message: String,
}

impl SongFileError {
    /// A value refused at a place in the file, as the Python's reading(where) says it.
    pub fn at(place: &str, problem: InvalidValue) -> SongFileError {
        let place = match &problem.within {
            Some(within) => llamatron_strings::named(
                llamatron_strings::errors::ERR_WHERE_IN_ROW,
                &[(words::WHERE, place.into()), (words::ROW, within.as_str().into())],
            ),
            None => place.to_string(),
        };
        SongFileError {
            message: llamatron_strings::named(
                llamatron_strings::errors::ERR_AT,
                &[(words::WHERE, place.into()), (words::PROBLEM, problem.message.into())],
            ),
        }
    }

    pub fn plain(message: String) -> SongFileError {
        SongFileError { message }
    }
}

/// A class's settings, in its table's order.
#[derive(Clone, Debug, PartialEq)]
pub struct Holder {
    table: &'static [Setting],
    values: Vec<Option<Data>>,
}

impl Holder {
    /// No setting written.
    pub fn empty(table: &'static [Setting]) -> Holder {
        Holder {
            table,
            values: vec![None; table.len()],
        }
    }

    /// Settings read from a file's data: every name the table has, checked, the rest passed over without a word, as a file
    /// from another version may hold them; leaving_out names the settings the class checks or reads itself.
    pub fn read(table: &'static [Setting], data: &Data, context: Option<&dyn Context>, leaving_out: &[&str]) -> Result<Holder, InvalidValue> {
        let mut holder = Holder::empty(table);
        for (key, value) in data.as_map().unwrap_or(&[]) {
            let Some(name) = key.as_str() else { continue };
            let Some(place) = table.iter().position(|setting| setting.name == name) else {
                continue;
            };
            if !leaving_out.contains(&name) {
                check(&table[place], value, context)?;
            }
            // A setting written as nothing is left out, as Python keeps None, so it is never written back.
            holder.values[place] = Some(value.clone()).filter(|value| !value.is_null());
        }
        Ok(holder)
    }

    pub fn get(&self, name: &str) -> Option<&Data> {
        let place = self.table.iter().position(|setting| setting.name == name)?;
        self.values[place].as_ref()
    }

    /// Store a value, or nothing to leave the setting out, without checking: the caller has.
    pub fn put(&mut self, name: &str, value: Option<Data>) {
        if let Some(place) = self.table.iter().position(|setting| setting.name == name) {
            self.values[place] = value;
        }
    }

    /// The settings a file writes: those holding a value, in the table's order.
    pub fn written(&self) -> Vec<(Data, Data)> {
        self.table
            .iter()
            .zip(&self.values)
            .filter_map(|(setting, value)| value.as_ref().map(|value| (Data::text(setting.name), value.clone())))
            .collect()
    }

    /// The settings a file writes, as a mapping.
    pub fn to_data(&self) -> Data {
        Data::Map(self.written())
    }
}

/// A file's data with every name not allowed taken out, as the Python's pass_over_unknown does.
pub fn passed_over(data: &Data, allowed: &dyn Fn(&str) -> bool) -> Data {
    match data {
        Data::Map(pairs) => Data::Map(pairs.iter().filter(|(key, _)| key.as_str().is_some_and(allowed)).cloned().collect()),
        other => other.clone(),
    }
}

/// Whether a name is one of a table's settings.
pub fn in_table(table: &[Setting], name: &str) -> bool {
    table.iter().any(|setting| setting.name == name)
}
