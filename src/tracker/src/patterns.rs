// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! What the pattern pages ask about a pattern (the Python model/objects/pattern_notes.py and the document's pattern_edits.py):
//! its values step by step, its notes as the steps they cover through ties or a gate, the scales it plays under and the
//! octaves the one track that plays it reaches.

use crate::uses::clip_slots_naming;
use llamatron_math::Rational;
use llamatron_model::file::data::Data;
use llamatron_model::objects::instrument_previews;
use llamatron_model::objects::pattern::Pattern;
use llamatron_model::objects::setlist::Setlist;
use llamatron_model::objects::song::Song;
use llamatron_model::schema::checking::written_length;
use llamatron_model::schema::generated::file_format::{Row, Section, TrackSetting};
use llamatron_model::schema::generated::limits::{MAX_GATE, MAX_OCTAVE, MIN_OCTAVE};
use llamatron_names::fill;
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
    if instrument_previews::is_preview(name) {
        // A tonal preview plays under the hidden chromatic scale on C, a drum preview under none.
        if setlist.get_pattern(name).is_some_and(Pattern::is_drum) {
            return Vec::new();
        }
        return vec![instrument_previews::PREVIEW_SCALE_KEY.to_string()];
    }
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
    match setlist.get_named_scale(name) {
        Some(scale) => scale
            .get_kind()
            .as_str()
            .and_then(llamatron_model::values::scale::ScaleType::named)
            .map_or(Vec::new(), |kind| kind.get_shape().to_vec()),
        _ => Vec::new(),
    }
}

pub fn scale_root(setlist: &Setlist, name: &str) -> String {
    match setlist.get_named_scale(name) {
        Some(scale) => scale.get_root().as_str().unwrap_or("").to_string(),
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

// Changing the notes as the piano roll does (the Python pattern_notes.py's PatternNotes).

/// The rows a split note's new start takes from the note it held.
const SPLIT_ROWS: [&str; 5] = [Row::DEGREE, Row::ACCIDENTAL, Row::OCTAVE, Row::CHORD, Row::VELOCITY];
/// A note's sharp or flat in the order the roll's key steps it.
const ACCIDENTAL_CYCLE: [Option<&str>; 3] = [None, Some("#"), Some("b")];

/// What a note edit refuses with, the pattern's own words.
type Edited = Result<(), String>;

/// Write one value of a step, as the pattern refuses it.
fn put(pattern: &mut Pattern, row: &str, step: usize, value: Option<Data>) -> Edited {
    pattern.set_value(row, step, value).map_err(|problem| problem.message)
}

/// How many whole steps fit in a length, at least one, as an entry size is placed in ties.
fn whole_steps_down(length: Rational, step_size: Rational) -> usize {
    let steps = length / step_size;
    (steps.numerator().div_euclid(steps.denominator()) as usize).max(1)
}

/// The step of the note sounding through a step by ties: the step itself when it has a note, or the note the ties before
/// it lead back to, or None.
pub fn holding_note(pattern: &Pattern, step: usize) -> Option<usize> {
    let mut step = step as i64;
    while value(pattern, Row::DEGREE, step as usize).is_none() {
        if !value(pattern, Row::TIE, step as usize).is_some_and(|tie| matches!(tie, Data::Bool(true))) {
            return None;
        }
        step -= 1;
        if step < 0 {
            return None;
        }
    }
    Some(step as usize)
}

/// Make a tied step the start of a note of its own, at the pitch of the note it held, as the roll's knife does, and say
/// whether it did.
pub fn split_note(pattern: &mut Pattern, step: usize) -> Result<bool, String> {
    let Some(start) = holding_note(pattern, step).filter(|start| *start != step) else {
        return Ok(false);
    };
    for row in SPLIT_ROWS {
        let held = value(pattern, row, start).cloned();
        put(pattern, row, step, held)?;
    }
    put(pattern, Row::TIE, step, Some(Data::Bool(false)))?;
    Ok(true)
}

/// Put a note on a step and tie the steps it covers after it to it, whatever they held going, a note it lands inside cut
/// where the new one starts and carrying on past it as a note of its own.
fn place_note(pattern: &mut Pattern, step: usize, note: (Data, i64, Option<&str>), covered: usize, gate: Option<String>) -> Edited {
    let steps = pattern.get_steps() as usize;
    let end = step + covered;
    if end < steps && value(pattern, Row::TIE, end).is_some_and(|tie| matches!(tie, Data::Bool(true))) {
        split_note(pattern, end)?;
    }
    pattern.clear_sound(step).map_err(|problem| problem.message)?;
    let (degree, octave, accidental) = note;
    put(pattern, Row::DEGREE, step, Some(degree))?;
    put(pattern, Row::OCTAVE, step, Some(Data::Whole(octave as i128)))?;
    put(pattern, Row::GATE, step, gate.map(|gate| Data::text(&gate)))?;
    put(pattern, Row::ACCIDENTAL, step, accidental.map(Data::text))?;
    for later in step + 1..(step + covered).min(steps) {
        pattern.clear_sound(later).map_err(|problem| problem.message)?;
        put(pattern, Row::TIE, later, Some(Data::Bool(true)))?;
    }
    Ok(())
}

/// Shorten the gate of the note reaching over a step so that it ends where the step starts, as a note drawn there cuts it.
fn cut_gate_before(pattern: &mut Pattern, step: usize, step_size: Rational) -> Edited {
    let Some(start) = covering_notes(pattern, step_size).get(&step).copied().filter(|start| *start != step) else {
        return Ok(());
    };
    let Some(gate) = gate_length(pattern, start) else { return Ok(()) };
    if start + whole_steps_up(gate, step_size) <= step {
        return Ok(());
    }
    put(
        pattern,
        Row::GATE,
        start,
        Some(Data::text(&(step_size * Rational::whole((step - start) as i128)).to_string())),
    )?;
    put(pattern, Row::DOT, start, None)
}

/// Draw a note of a length on a step: in ties for each whole step it covers, or as a gate where it is shorter than a step,
/// cutting the note it lands in; on a chord's step the chord's root moves to the note and nothing else of the step changes.
pub fn draw_note(pattern: &mut Pattern, step: usize, note: (Data, i64, Option<&str>), length: Rational, step_size: Rational) -> Edited {
    let starts_chord = value(pattern, Row::DEGREE, step).is_some() && value(pattern, Row::CHORD, step).is_some();
    if starts_chord {
        let (degree, octave, accidental) = note;
        put(pattern, Row::DEGREE, step, Some(degree))?;
        put(pattern, Row::OCTAVE, step, Some(Data::Whole(octave as i128)))?;
        return put(pattern, Row::ACCIDENTAL, step, accidental.map(Data::text));
    }
    cut_gate_before(pattern, step, step_size)?;
    if length < step_size {
        return place_note(pattern, step, note, 1, Some(length.to_string()));
    }
    place_note(pattern, step, note, whole_steps_down(length, step_size), None)
}

/// Drag the end of the note starting on a step one step later, and say whether there was room: a note shorter than a step
/// becomes a whole one first, and otherwise a step is tied on unless the pattern ends there or the next note starts.
pub fn lengthen_note(pattern: &mut Pattern, start: usize, step_size: Rational) -> Result<bool, String> {
    if gate_length(pattern, start).is_some_and(|gate| gate < step_size) {
        put(pattern, Row::GATE, start, None)?;
        put(pattern, Row::DOT, start, None)?;
        return Ok(true);
    }
    let end = start + note_span(pattern, start, step_size);
    if end >= pattern.get_steps() as usize || has_sound(pattern, end) {
        return Ok(false);
    }
    put(pattern, Row::TIE, end, Some(Data::Bool(true)))?;
    Ok(true)
}

/// Take the last tie off the note starting on a step, or a step off its gate where it has no ties, and say whether it could:
/// a note of one step stays.
pub fn shorten_note(pattern: &mut Pattern, start: usize, step_size: Rational) -> Result<bool, String> {
    let last = start + note_span(pattern, start, step_size) - 1;
    if last > start && value(pattern, Row::TIE, last).is_some_and(|tie| matches!(tie, Data::Bool(true))) {
        put(pattern, Row::TIE, last, Some(Data::Bool(false)))?;
        return Ok(true);
    }
    let Some(written) = value(pattern, Row::GATE, start).and_then(Data::as_str).map(str::to_string) else {
        return Ok(false);
    };
    let Ok(gate) = written_length(&Data::text(&written), Rational::whole(MAX_GATE as i128)) else {
        return Ok(false);
    };
    if gate <= step_size {
        return Ok(false);
    }
    let shorter = gate - step_size;
    let gate = (shorter != step_size).then(|| Data::text(&shorter.to_string()));
    put(pattern, Row::GATE, start, gate)?;
    Ok(true)
}

/// Move the note starting on a step on to the next of natural, sharp and flat.
pub fn cycle_accidental(pattern: &mut Pattern, start: usize) -> Edited {
    let current = value(pattern, Row::ACCIDENTAL, start).and_then(Data::as_str).map(str::to_string);
    let place = ACCIDENTAL_CYCLE.iter().position(|each| each.map(str::to_string) == current).unwrap_or(0);
    let following = ACCIDENTAL_CYCLE[(place + 1) % ACCIDENTAL_CYCLE.len()];
    put(pattern, Row::ACCIDENTAL, start, following.map(Data::text))
}

/// A pattern's name as the pages show it: an instrument's preview pattern by its instrument, `preview (lead)`.
pub fn shown_pattern_name(name: &str) -> String {
    match instrument_previews::preview_instrument(name) {
        Some(instrument) => llamatron_strings::named(llamatron_strings::names::MSG_INSTRUMENT_PREVIEW_NAME, &[(fill::INSTRUMENT, instrument.into())]),
        None => name.to_string(),
    }
}

/// A scale's name as the pages show it: the hidden chromatic scale a preview plays under by what it is.
pub fn shown_scale_name(name: &str) -> String {
    if name == instrument_previews::PREVIEW_SCALE_KEY {
        return llamatron_strings::names::MSG_PREVIEW_SCALE_NAME.to_string();
    }
    name.to_string()
}
