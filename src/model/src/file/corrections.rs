// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The corrections offered when a set file holds a value that cannot be used but has an allowed value near it.
//!
//! A whole number outside its range has the nearest end of the range, a length that is too long has the longest allowed,
//! a choice outside its list has its default, and a pattern's row of numbers or degrees has each step that needs it
//! brought within the row's limits. Anything else wrong with a file, such as a name that names nothing or text where a
//! number belongs, has no such value, and the file is refused as always.
//!
//! Reading a file stays strict. Only where it is refused does the program ask for the file corrected: the corrector
//! walks the file's data, laid out as the objects are, with each part's table of settings, puts the nearest allowed value
//! in place of each that cannot be used, and says what it changed, for the tracker's dialog or the command line to show
//! before anything opens. Nothing here changes a file.

use crate::file::data::Data;
use crate::file::layout::OBJECT_SCENE_TRACKS;
use crate::objects::named::plugin_table;
use crate::objects::step_checks::{check_step, nearest_step};
use crate::schema::checking::{check, NearestValue};
use crate::schema::generated::file_format::{FileLayout, PatternSetting, Section, PATTERN_ROWS};
use crate::schema::generated::plugins::PLUGINS;
use crate::schema::generated::settings::{Setting, CHAIN, CLIP_SLOT, DRAW, GROOVE, INSTRUMENT, NAMED_SCALE, PATTERN, SCENE, SETLIST, SONG, TRACK};
use llamatron_names::file_format;
use llamatron_names::fill;
use llamatron_names::words;
use llamatron_strings::{errors, messages, named, names};

/// One value of a file that cannot be used, and what is used in its place: where it is, what a message calls it, what was
/// found, what is used, None for the setting's default, and for a pattern's row, how many of its steps change.
#[derive(Clone, Debug, PartialEq)]
pub struct Correction {
    pub place: String,
    pub name: String,
    pub found: Data,
    pub used: Option<Data>,
    pub count: Option<usize>,
}

impl Correction {
    /// One line saying where the value is, what was found and what is used in its place.
    pub fn described(&self) -> String {
        let place = self.place.as_str();
        let name = self.name.as_str();
        if let Some(count) = self.count {
            return named(
                messages::MSG_CORRECTED_SEVERAL,
                &[
                    (words::WHERE, place.into()),
                    (file_format::FileLayout::NAME, name.into()),
                    (words::COUNT, (count as i64).into()),
                ],
            );
        }
        match &self.used {
            None => named(
                messages::MSG_CORRECTED_TO_DEFAULT,
                &[
                    (words::WHERE, place.into()),
                    (file_format::FileLayout::NAME, name.into()),
                    (words::FOUND, (&self.found).into()),
                ],
            ),
            Some(used) => named(
                messages::MSG_CORRECTED,
                &[
                    (words::WHERE, place.into()),
                    (file_format::FileLayout::NAME, name.into()),
                    (words::FOUND, (&self.found).into()),
                    (words::USED, used.into()),
                ],
            ),
        }
    }
}

/// A file's data, laid out as the objects are, with every value that cannot be used but has an allowed value near it
/// changed to that value, and the corrections made.
pub fn corrected(data: &Data) -> (Data, Vec<Correction>) {
    let mut data = data.clone();
    let mut corrections = Vec::new();
    correct_settings(&mut data, SETLIST, names::MSG_THE_FILE, &mut corrections);
    let mut sections: Vec<&str> = vec![Section::SCALES, Section::PATTERNS, Section::CHAINS, Section::GROOVES, Section::INSTRUMENTS];
    sections.extend(PLUGINS.iter().map(|plugin| plugin.section));
    for section in sections {
        let table = table_of(section);
        each_named(&mut data, section, |name, item| {
            let place = placed(section, name);
            correct_settings(item, table, &place, &mut corrections);
            if section == Section::PATTERNS {
                correct_rows(item, &place, &mut corrections);
            }
        });
    }
    each_named(&mut data, Section::SONGS, |name, song| {
        correct_song(song, &placed(Section::SONGS, name), &mut corrections)
    });
    (data, corrections)
}

/// The table of settings of the items of a section.
fn table_of(section: &str) -> &'static [Setting] {
    match section {
        Section::SCALES => NAMED_SCALE,
        Section::PATTERNS => PATTERN,
        Section::CHAINS => CHAIN,
        Section::GROOVES => GROOVE,
        Section::INSTRUMENTS => INSTRUMENT,
        other => PLUGINS
            .iter()
            .find(|plugin| plugin.section == other)
            .and_then(|plugin| plugin_table(plugin.name))
            .unwrap_or(&[]),
    }
}

/// A place in the file as a refusal names it: the section's word and the item's name.
fn placed(section: &str, name: &str) -> String {
    format!("{section} ({name})")
}

/// A place inside another, as a refusal joins them.
fn within(place: &str, part: &str) -> String {
    named(errors::ERR_WHERE_IN_ROW, &[(fill::WHERE, place.into()), (fill::ROW, part.into())])
}

/// Each item of a part of the data that keeps its items by name, changed in place.
fn each_named(data: &mut Data, key: &str, mut change: impl FnMut(&str, &mut Data)) {
    let Data::Map(pairs) = data else { return };
    let Some((_, Data::Map(items))) = pairs.iter_mut().find(|(found, _)| found.as_str() == Some(key)) else {
        return;
    };
    for (name, item) in items.iter_mut() {
        change(&name.python_str(), item);
    }
}

/// A song's own settings corrected, then its tracks', its draws', its scenes' and their clips'.
fn correct_song(song: &mut Data, place: &str, corrections: &mut Vec<Correction>) {
    correct_settings(song, SONG, place, corrections);
    each_named(song, Section::TRACKS, |name, track| {
        correct_settings(track, TRACK, &within(place, &placed(Section::TRACKS, name)), corrections)
    });
    each_named(song, Section::DRAWS, |name, draw| {
        correct_settings(draw, DRAW, &within(place, &placed(Section::DRAWS, name)), corrections)
    });
    let Data::Map(pairs) = song else { return };
    let Some((_, Data::List(scenes))) = pairs.iter_mut().find(|(key, _)| key.as_str() == Some(Section::SCENES)) else {
        return;
    };
    for scene in scenes.iter_mut() {
        let name = scene.get(FileLayout::NAME).map(Data::python_str).unwrap_or_default();
        let scene_place = within(place, &placed(Section::SCENES, &name));
        correct_settings(scene, SCENE, &scene_place, corrections);
        each_named(scene, OBJECT_SCENE_TRACKS, |track, clip| {
            correct_settings(clip, CLIP_SLOT, &within(&scene_place, &placed(Section::TRACKS, track)), corrections);
        });
    }
}

/// The settings of one part of the data with each that cannot be used changed to its nearest allowed value, or taken out
/// for its default.
fn correct_settings(item: &mut Data, table: &'static [Setting], place: &str, corrections: &mut Vec<Correction>) {
    let Data::Map(pairs) = item else { return };
    let mut left_out = Vec::new();
    for (key, value) in pairs.iter_mut() {
        let Some(setting) = table.iter().find(|setting| key.as_str() == Some(setting.name)) else {
            continue;
        };
        if value.is_null() {
            continue;
        }
        let Err(refusal) = check(setting, value, None) else { continue };
        let used = match refusal.nearest {
            NearestValue::None => continue,
            NearestValue::LeftOut => None,
            NearestValue::Value(nearest) => Some(nearest),
        };
        corrections.push(Correction {
            place: place.to_string(),
            name: setting.name.to_string(),
            found: value.clone(),
            used: used.clone(),
            count: None,
        });
        match used {
            Some(nearest) => *value = nearest,
            None => left_out.push(setting.name),
        }
    }
    pairs.retain(|(key, _)| !key.as_str().is_some_and(|name| left_out.contains(&name)));
}

/// A pattern's rows with each step that cannot be used brought within its row's limits, a row at once; a row holding a
/// step with no allowed value near it is left for the file to refuse.
fn correct_rows(pattern: &mut Data, place: &str, corrections: &mut Vec<Correction>) {
    let drum = pattern.get(PatternSetting::DRUM) == Some(&Data::Bool(true));
    let Data::Map(pairs) = pattern else { return };
    for (key, values) in pairs.iter_mut() {
        let Some(row) = key.as_str().filter(|name| PATTERN_ROWS.contains(name)) else {
            continue;
        };
        let Data::List(steps) = values else { continue };
        if steps.iter().all(|value| check_step(row, value, drum).is_ok()) {
            continue;
        }
        let used: Option<Vec<Data>> = steps
            .iter()
            .map(|value| {
                if check_step(row, value, drum).is_ok() {
                    Some(value.clone())
                } else {
                    nearest_step(row, value, drum)
                }
            })
            .collect();
        let Some(used) = used else { continue };
        let count = steps.iter().zip(&used).filter(|(before, after)| before != after).count();
        corrections.push(Correction {
            place: place.to_string(),
            name: row.to_string(),
            found: values.clone(),
            used: Some(Data::List(used.clone())),
            count: Some(count),
        });
        *values = Data::List(used);
    }
}
