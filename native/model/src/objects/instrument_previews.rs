// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! An instrument's preview pattern (the Python model/objects/instrument_previews.py): a pattern of its own for designing
//! its sound before any music exists, which the Instrument page's Preview pattern button opens and Listen plays.
//!
//! Each instrument holds its own preview, written inside it under `preview`, so that it is renamed, copied and deleted with
//! the instrument, and it is never one of the set's patterns, so that no list of patterns, picker or chain shows one. The
//! pattern editor reaches one by a key made from the instrument's name, which only the set's pattern lookups resolve, so
//! that every edit, munge and undo works on it as on any pattern. A tonal instrument's preview plays under a hidden
//! chromatic scale on C, reached by a key of its own, so that any note can be written without choosing a key; a drum
//! instrument's under none.

use crate::file::data::Data;
use crate::objects::named::NamedScale;
use crate::schema::generated::file_format::{PatternSetting, Row, ScaleSetting};
use std::sync::OnceLock;

/// What a preview's key starts with: a character no name typed or read from a file holds, so that no pattern of the set
/// is ever taken for a preview.
const PREVIEW_MARK: char = '\u{1}';
/// The key of the hidden chromatic scale on C a tonal preview plays under.
pub const PREVIEW_SCALE_KEY: &str = "\u{1}chromatic on C";
const PREVIEW_STEPS: usize = 16;
const PREVIEW_STEP_SIZE: &str = "1/16";
const PREVIEW_OCTAVE: i128 = 5;
/// A run up and down C major, as degrees of the chromatic scale counted from 1.
const MAJOR_STEPS: [i128; 16] = [1, 3, 5, 6, 8, 10, 12, 13, 13, 12, 10, 8, 6, 5, 3, 1];
const STEPS_IN_AN_OCTAVE: i128 = 12;
const QUARTER_STEPS: usize = 4;
const PREVIEW_ROOT: &str = "C";
const CHROMATIC: &str = "chromatic";

/// The key the pattern editor reaches an instrument's preview pattern by, in place of a pattern's name.
pub fn preview_key(instrument: &str) -> String {
    format!("{PREVIEW_MARK}{instrument}")
}

/// The instrument whose preview a key reaches, or None for a pattern's name.
pub fn preview_instrument(key: &str) -> Option<&str> {
    key.strip_prefix(PREVIEW_MARK).filter(|_| key != PREVIEW_SCALE_KEY)
}

/// Whether a pattern's name is a preview's key rather than a pattern of the set's.
pub fn is_preview(key: &str) -> bool {
    preview_instrument(key).is_some()
}

/// The hidden chromatic scale on C a tonal preview plays under.
pub fn preview_scale() -> &'static NamedScale {
    static SCALE: OnceLock<NamedScale> = OnceLock::new();
    SCALE.get_or_init(|| {
        let data = Data::Map(vec![
            (Data::text(ScaleSetting::ROOT), Data::text(PREVIEW_ROOT)),
            (Data::text(ScaleSetting::TYPE), Data::text(CHROMATIC)),
        ]);
        NamedScale::from_data(&data).expect("the chromatic scale on C is a scale")
    })
}

/// A new preview pattern's data: a drum's C on each quarter in the set's default drum octave, or a sixteenth-note run up
/// and down C major on the chromatic scale.
pub fn starting_preview(drum: bool) -> Data {
    let mut data = Data::Map(Vec::new());
    data.set(PatternSetting::STEPS, Data::Whole(PREVIEW_STEPS as i128));
    data.set(PatternSetting::STEP_SIZE, Data::text(PREVIEW_STEP_SIZE));
    if drum {
        // No octave written, so each C plays in the set's default drum octave, the very C the built-in drums play at their
        // own pitch on.
        let degrees = (0..PREVIEW_STEPS)
            .map(|step| if step % QUARTER_STEPS == 0 { Data::text(PREVIEW_ROOT) } else { Data::Null })
            .collect();
        data.set(PatternSetting::DRUM, Data::Bool(true));
        data.set(Row::DEGREE, Data::List(degrees));
        return data;
    }
    let degrees = MAJOR_STEPS.iter().map(|step| Data::Whole((step - 1) % STEPS_IN_AN_OCTAVE + 1)).collect();
    let octaves = MAJOR_STEPS
        .iter()
        .map(|step| Data::Whole(PREVIEW_OCTAVE + (step - 1) / STEPS_IN_AN_OCTAVE))
        .collect();
    data.set(PatternSetting::SCALE_LENGTH, Data::Whole(STEPS_IN_AN_OCTAVE));
    data.set(Row::DEGREE, Data::List(degrees));
    data.set(Row::OCTAVE, Data::List(octaves));
    data
}
