// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! llamatron's model: the set as stored, its values, its objects, its schema and its file, the layer the engine renders
//! and the tracker edits.

pub mod file;
pub mod fundamentals;
pub mod objects;
pub mod schema;
pub mod values;

/// A value the model refuses, with the message the Python program gives for it.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ValueError(pub String);

impl std::fmt::Display for ValueError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter) -> std::fmt::Result {
        formatter.write_str(&self.0)
    }
}
