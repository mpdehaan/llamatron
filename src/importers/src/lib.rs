// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! llamatron's importers: a MIDI file made into a song of a set, with the patterns, scales and instruments it needs.

pub mod chord_naming;
pub mod cutting;
pub mod import;
pub mod keys;
pub mod reading;
pub mod steps;
pub mod voices;
pub mod writing;

/// Python's float sum, which adds with Neumaier's compensation since Python 3.12, so that a sum comes out as Python's does.
pub fn python_sum(values: impl IntoIterator<Item = f64>) -> f64 {
    let mut total = 0.0f64;
    let mut compensation = 0.0f64;
    for value in values {
        let sum = total + value;
        if total.abs() >= value.abs() {
            compensation += (total - sum) + value;
        } else {
            compensation += (value - sum) + total;
        }
        total = sum;
    }
    if compensation != 0.0 && compensation.is_finite() {
        total += compensation;
    }
    total
}
