// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The set's own settings as the pages read them, each with its default where the file leaves it out (the Python Setlist's
//! getters).

use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::Setlist;
use llamatron_model::schema::generated::defaults;
use llamatron_model::schema::generated::file_format::{SetlistSetting, OCTAVE_LABEL_OFFSETS};

pub fn text_of(setlist: &Setlist, name: &str) -> String {
    setlist.get_written(name).and_then(Data::as_str).unwrap_or("").to_string()
}

pub fn bool_of(setlist: &Setlist, name: &str, default: bool) -> bool {
    match setlist.get_written(name) {
        Some(Data::Bool(value)) => *value,
        _ => default,
    }
}

pub fn whole_of(setlist: &Setlist, name: &str, default: i64) -> i64 {
    setlist.get_written(name).and_then(Data::as_whole).map_or(default, |whole| whole as i64)
}

pub fn choice_of(setlist: &Setlist, name: &str, default: &str) -> String {
    setlist.get_written(name).and_then(Data::as_str).unwrap_or(default).to_string()
}

pub fn octave_labels(setlist: &Setlist) -> String {
    choice_of(setlist, SetlistSetting::OCTAVE_LABELS, defaults::DEFAULT_OCTAVE_LABELS)
}

/// An octave as the set's octave labels show it: two lower with Live's.
pub fn shown_octave(setlist: &Setlist, octave: i64) -> i64 {
    let labels = octave_labels(setlist);
    octave - OCTAVE_LABEL_OFFSETS.iter().find(|(name, _)| *name == labels).map_or(0, |(_, offset)| *offset)
}

/// The modes the visualizer key leaves out, in the modes' order.
pub fn hidden_visualizers(setlist: &Setlist) -> Vec<String> {
    let hidden: Vec<String> = setlist
        .get_written(SetlistSetting::HIDDEN_VISUALIZERS)
        .and_then(Data::as_list)
        .unwrap_or(&[])
        .iter()
        .filter_map(|name| name.as_str().map(str::to_string))
        .collect();
    llamatron_model::schema::generated::file_format::VISUALIZER_NAMES
        .iter()
        .filter(|name| hidden.iter().any(|each| each == *name))
        .map(|name| name.to_string())
        .collect()
}

/// A visualizer mode's name on screen.
pub fn mode_name(name: &str) -> String {
    crate::generated::tables::VISUALIZER_MODE_NAMES
        .iter()
        .find(|(found, _)| *found == name)
        .map_or(name, |(_, shown)| shown)
        .to_string()
}

/// A name of a fixed list's words, by its value.
pub fn named_in(names: &[(&str, &str)], value: &str) -> String {
    names.iter().find(|(found, _)| *found == value).map_or(value, |(_, name)| name).to_string()
}

/// An exact number as text: a whole number as one, and otherwise as a decimal, as a tempo is shown.
pub fn number_text(value: &Data) -> String {
    match llamatron_model::schema::checking::number(value) {
        Ok(rational) if rational.denominator() == 1 => rational.numerator().to_string(),
        Ok(rational) => llamatron_strings::fill::python_float(rational.to_float()),
        Err(_) => String::new(),
    }
}

/// Names in the order a picker shows them: by name ignoring case, a number at a name's end read as a number.
pub fn sorted_names(names: &[String]) -> Vec<String> {
    let mut sorted = names.to_vec();
    sorted.sort_by_key(|name| llamatron_model::objects::naming::name_order(name));
    sorted
}

/// A song's own setting, or None where the file leaves it out.
pub fn song_text(song: &llamatron_model::objects::song::Song, name: &str) -> Option<String> {
    song.get_written(name).and_then(Data::as_str).map(str::to_string)
}
