// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Time signatures, like 4/4 or 6/8 (the Python model/values/time_signature.py): how many beats make a bar, and which note
//! counts as a beat.

use crate::values::generated::time_signature::{COMPOUND_GROUP, MAX_BEATS, MIN_BEATS, SMALLEST_COMPOUND, UNITS, UNITS_LISTED};
use crate::ValueError;
use llamatron_math::Rational;
use llamatron_strings::errors;
use llamatron_strings::named;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct TimeSignature {
    beats: i64,
    unit: i64,
}

/// The beats and unit a text writes, like 6/8, or None for any other text.
fn parsed(text: &str) -> Option<(i64, i64)> {
    let (beats, unit) = text.split_once('/')?;
    if beats.is_empty() || unit.is_empty() || !beats.chars().chain(unit.chars()).all(|digit| digit.is_ascii_digit()) {
        return None;
    }
    let (beats, unit) = (beats.parse().ok()?, unit.parse().ok()?);
    ((MIN_BEATS..=MAX_BEATS).contains(&beats) && UNITS.contains(&unit)).then_some((beats, unit))
}

impl TimeSignature {
    pub fn new(beats: i64, unit: i64) -> Result<TimeSignature, ValueError> {
        TimeSignature::from_text(&format!("{beats}/{unit}"))
    }

    pub fn from_text(text: &str) -> Result<TimeSignature, ValueError> {
        let Some((beats, unit)) = parsed(text) else {
            return Err(ValueError(named(
                errors::ERR_BAD_TIME_SIGNATURE,
                &[
                    ("lowest", MIN_BEATS.into()),
                    ("highest", MAX_BEATS.into()),
                    ("units", UNITS_LISTED.into()),
                    ("value", text.into()),
                ],
            )));
        };
        Ok(TimeSignature { beats, unit })
    }

    pub fn get_beats(&self) -> i64 {
        self.beats
    }

    pub fn get_unit(&self) -> i64 {
        self.unit
    }

    pub fn to_text(&self) -> String {
        format!("{}/{}", self.beats, self.unit)
    }

    /// Whether the beat is a dotted note, as in 6/8, where the bar is counted in two.
    pub fn is_compound(&self) -> bool {
        self.beats >= SMALLEST_COMPOUND && self.beats % COMPOUND_GROUP == 0
    }

    pub fn beat_length(&self) -> Rational {
        let notes = if self.is_compound() { COMPOUND_GROUP } else { 1 };
        Rational::new(notes as i128, self.unit as i128)
    }

    pub fn bar_length(&self) -> Rational {
        Rational::new(self.beats as i128, self.unit as i128)
    }

    /// Whether a time from a bar's start falls exactly on a beat.
    pub fn starts_a_beat(&self, time: Rational) -> bool {
        (time / self.beat_length()).is_whole()
    }
}
