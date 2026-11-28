// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The migrations: each moves a set file's data from the layout before one breaking change to the layout after it, run
//! in order for a file saved before each, so that the reader only ever sees the layout written now. One is kept, Live's
//! octave numbers (before 1.0.30), as the mechanism a later breaking change adds its own migration to.

use crate::file::data::Data;
use crate::schema::generated::file_format::{Row, Section, SetlistSetting};

const VERSION: &str = "version";

/// What reading a file moved: whether any migration ran.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Conversion {
    pub moved: bool,
}

/// A version's three numbers, or None for text that is not one.
pub fn version_numbers(text: &str) -> Option<(u64, u64, u64)> {
    let parts: Vec<&str> = text.split('.').collect();
    if parts.len() != 3 || !parts.iter().all(|part| !part.is_empty() && part.chars().all(|digit| digit.is_ascii_digit())) {
        return None;
    }
    Some((parts[0].parse().ok()?, parts[1].parse().ok()?, parts[2].parse().ok()?))
}

/// The version a file was saved by, if it says.
fn saved_version(data: &Data) -> Option<(u64, u64, u64)> {
    data.get(VERSION).and_then(Data::as_str).and_then(version_numbers)
}

/// One breaking change of the layout: the version that first wrote the new layout, and the change itself.
struct Migration {
    since: &'static str,
    change: fn(Data) -> Data,
}

/// Every migration, oldest first.
const MIGRATIONS: [Migration; 1] = [Migration {
    since: "1.0.30",
    change: live_octaves,
}];

/// The data moved to the layout written now, with what moving it did.
pub fn migrated(data: Data) -> (Data, Conversion) {
    let mut conversion = Conversion::default();
    let mut data = data;
    for Migration { since, change } in MIGRATIONS {
        if !matches!(data, Data::Map(_)) {
            continue;
        }
        let due = saved_version(&data).is_some_and(|saved| version_numbers(since).is_some_and(|since| saved < since));
        if due {
            conversion.moved = true;
            data = change(data);
        }
    }
    (data, conversion)
}

/// Octaves numbered as Live labels them, two lower than from C0, moved up.
fn live_octaves(data: Data) -> Data {
    const OFFSET: i128 = 2;
    let mut moved = data;
    for name in [SetlistSetting::DEFAULT_OCTAVE, SetlistSetting::DEFAULT_DRUM_OCTAVE] {
        if let Some(Data::Whole(octave)) = moved.get(name).cloned() {
            moved.set(name, Data::Whole(octave + OFFSET));
        }
    }
    if let Some(Data::Map(patterns)) = moved.get(Section::PATTERNS).cloned() {
        let shifted = patterns
            .into_iter()
            .map(|(name, mut pattern)| {
                if let Some(Data::List(octaves)) = pattern.get(Row::OCTAVE).cloned() {
                    let raised = octaves
                        .into_iter()
                        .map(|octave| match octave {
                            Data::Whole(whole) => Data::Whole(whole + OFFSET),
                            other => other,
                        })
                        .collect();
                    pattern.set(Row::OCTAVE, Data::List(raised));
                }
                (name, pattern)
            })
            .collect();
        moved.set(Section::PATTERNS, Data::Map(shifted));
    }
    moved
}
