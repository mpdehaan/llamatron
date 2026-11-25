// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! What the pattern pages ask about a pattern (the Python model/objects/pattern_notes.py and the document's pattern_edits.py):
//! its values step by step, its notes as the steps they cover through ties or a gate, the scales it plays under and the
//! octaves the one track that plays it reaches.

use crate::uses::clip_slots_naming;
use llamatron_math::Rational;
use llamatron_model::file::data::Data;
use llamatron_model::objects::pattern::Pattern;
use llamatron_model::objects::setlist::{Item, Setlist};
use llamatron_model::objects::song::Song;
use llamatron_model::schema::checking::written_length;
use llamatron_model::schema::generated::file_format::{Row, Section, TrackSetting};
use llamatron_model::schema::generated::limits::{MAX_GATE, MAX_OCTAVE, MIN_OCTAVE};
use std::collections::BTreeMap;

/// A step's value in a row, None where the row or the step holds nothing.
pub fn value<'a>(pattern: &'a Pattern, row: &str, step: usize) -> Option<&'a Data> {
    pattern.row(row).and_then(|values| values.get(step)).filter(|value| !value.is_null())
}

fn truthy(value: Option<&Data>) -> bool {
    matches!(value, Some(Data::Bool(true)))
}

/// Whether a step plays something: a degree, or a grab.
pub fn has_sound(pattern: &Pattern, step: usize) -> bool {
    pattern.has_sound(step)
}

pub fn note_steps(pattern: &Pattern) -> Vec<usize> {
    (0..pattern.get_steps() as usize).filter(|step| has_sound(pattern, *step)).collect()
}

/// The step after the last tie following a note's step.
fn tied_end(pattern: &Pattern, step: usize) -> usize {
    let steps = pattern.get_steps() as usize;
    let mut end = step + 1;
    while end < steps && truthy(value(pattern, Row::TIE, end)) {
        end += 1;
    }
    end
}

/// How long a step's note sounds by its gate and Dot row, or None when the gate is blank.
pub fn gate_length(pattern: &Pattern, step: usize) -> Option<Rational> {
    let gate = value(pattern, Row::GATE, step)?;
    let length = written_length(gate, Rational::whole(MAX_GATE as i128)).ok()?;
    match value(pattern, Row::DOT, step).and_then(Data::as_str) {
        None => Some(length),
        Some(modifier) => Some(length * llamatron_engine::tables::gate_modifier(modifier).unwrap_or(Rational::whole(1))),
    }
}

/// How many whole steps a length takes, counting a part of a step as one.
fn whole_steps_up(length: Rational, step_size: Rational) -> usize {
    let steps = length / step_size;
    let whole = steps.numerator().div_euclid(steps.denominator());
    if whole * steps.denominator() == steps.numerator() {
        whole as usize
    } else {
        whole as usize + 1
    }
}

/// How many steps the note on a step covers on a piano roll: its ties, or its gate rounded up to whole steps, and any ties
/// right after that.
pub fn note_span(pattern: &Pattern, step: usize, step_size: Rational) -> usize {
    let steps = pattern.get_steps() as usize;
    let mut end = tied_end(pattern, step);
    if let Some(gate) = gate_length(pattern, step) {
        let reach = step + whole_steps_up(gate, step_size).max(1);
        end = end.max(reach.min(steps));
        while end < steps && truthy(value(pattern, Row::TIE, end)) {
            end += 1;
        }
    }
    end - step
}

/// The step of the note sounding through each step, by step, up to the next note.
pub fn covering_notes(pattern: &Pattern, step_size: Rational) -> BTreeMap<usize, usize> {
    let steps = pattern.get_steps() as usize;
    let mut covering = BTreeMap::new();
    for start in note_steps(pattern) {
        for step in start..(start + note_span(pattern, start, step_size)).min(steps) {
            if step != start && has_sound(pattern, step) {
                break;
            }
            covering.insert(step, start);
        }
    }
    covering
}

/// What part of a note's last cell its gate fills, where the gate ends inside a step, or None for a full cell.
pub fn partial_cell(pattern: &Pattern, step: usize, step_size: Rational) -> Option<Rational> {
    let gate = gate_length(pattern, step)?;
    let steps = gate / step_size;
    let whole = steps.numerator().div_euclid(steps.denominator());
    if whole * steps.denominator() == steps.numerator() || whole as usize + 1 != note_span(pattern, step, step_size) {
        return None;
    }
    Some(Rational::new(steps.numerator() - whole * steps.denominator(), steps.denominator()))
}

/// The scale each clip of the set that plays a pattern plays it in: the clip's own, else its scene's, else its song's.
pub fn scales_for_pattern(setlist: &Setlist, name: &str) -> Vec<String> {
    let mut names = Vec::new();
    for song_name in setlist.song_names() {
        let Some(song) = setlist.get_song(song_name) else { continue };
        for scene in song.scenes() {
            for (_, clip) in scene.clip_slots() {
                if !clip.get_pattern_names().iter().any(|pattern| pattern == name)
                    && clip
                        .get_written(llamatron_model::schema::generated::file_format::ClipSlotSetting::MORPH_TO)
                        .and_then(Data::as_str)
                        != Some(name)
                {
                    continue;
                }
                if let Some(scale) = clip.get_scale_name().or_else(|| scene.get_scale_name()).or_else(|| song.get_scale_name()) {
                    names.push(scale);
                }
            }
        }
    }
    names
}

/// The scales a pattern plays under: those of the clips that play it, or the current song's when none does.
pub fn scales_of_pattern(setlist: &Setlist, song: &Song, name: &str) -> Vec<String> {
    let names = if clip_slots_naming(setlist, Section::PATTERNS, name).is_empty() {
        song.get_scale_name().into_iter().collect()
    } else {
        scales_for_pattern(setlist, name)
    };
    let mut unique: Vec<String> = Vec::new();
    for scale in names {
        if !unique.contains(&scale) {
            unique.push(scale);
        }
    }
    unique
}

/// The one scale a pattern plays under, or None when its uses disagree or nothing says.
pub fn pattern_scale(setlist: &Setlist, song: &Song, name: &str) -> Option<String> {
    let scales = scales_of_pattern(setlist, song, name);
    (scales.len() == 1).then(|| scales[0].clone())
}

/// A named scale's shape in half steps, by its name.
pub fn scale_half_steps(setlist: &Setlist, name: &str) -> Vec<i64> {
    match setlist.get_item(Section::SCALES, name) {
        Some(Item::Scale(scale)) => scale
            .get_kind()
            .as_str()
            .and_then(llamatron_model::values::scale::ScaleType::named)
            .map_or(Vec::new(), |kind| kind.get_shape().to_vec()),
        _ => Vec::new(),
    }
}

pub fn scale_root(setlist: &Setlist, name: &str) -> String {
    match setlist.get_item(Section::SCALES, name) {
        Some(Item::Scale(scale)) => scale.get_root().as_str().unwrap_or("").to_string(),
        _ => String::new(),
    }
}

/// The largest scale a pattern can play in, which limits its degrees: the song's, and every one a clip plays it in.
pub fn degree_limit(setlist: &Setlist, song: &Song, name: &str) -> usize {
    let mut names: Vec<String> = song.get_scale_name().into_iter().collect();
    names.extend(scales_for_pattern(setlist, name));
    names
        .iter()
        .map(|scale| scale_half_steps(setlist, scale).len())
        .max()
        .unwrap_or(DEGREE_LIMIT_WITHOUT_A_SCALE)
}

/// How many degrees a pattern may hold where no scale says.
pub const DEGREE_LIMIT_WITHOUT_A_SCALE: usize = 7;

/// The lowest and highest octave of the one track that plays a pattern, or None where no one track does.
pub fn pattern_octave_range(setlist: &Setlist, name: &str) -> Option<(i64, i64)> {
    let mut plays: Vec<(String, String)> = clip_slots_naming(setlist, Section::PATTERNS, name)
        .into_iter()
        .map(|(song, _, _, track)| (song, track))
        .collect();
    plays.sort();
    plays.dedup();
    if plays.len() != 1 {
        return None;
    }
    let (song, track) = &plays[0];
    let track = setlist.get_song(song)?.get_track(track)?;
    let octave = |setting: &str, default: i64| track.get_written(setting).and_then(Data::as_whole).map_or(default, |whole| whole as i64);
    Some((
        octave(TrackSetting::LOWEST_OCTAVE, MIN_OCTAVE),
        octave(TrackSetting::HIGHEST_OCTAVE, MAX_OCTAVE),
    ))
}
