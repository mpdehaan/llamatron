// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Voice leading (the Python music_theory/fundamentals/voice_leading.py and pattern_munges.py's apply_voice_leading):
//! moving from one chord to the next with as little movement as the notes allow. A keyboard player going from C major to
//! F major keeps C, moves E up a half step to F and G up a whole step to A, rather than jumping the whole hand; voice
//! leading chooses, for each chord after the first, the inversion, and where asked the octave, whose notes move least
//! from the chord before. Pitches here are half steps.

use crate::chord_text::ChordScale;
use crate::chord_tones::{chord_tones, Tone};
use crate::patterns::value;
use llamatron_model::file::data::Data;
use llamatron_model::objects::pattern::Pattern;
use llamatron_model::schema::checking::InvalidValue;
use llamatron_model::schema::generated::file_format::Row;
use llamatron_model::schema::generated::limits::{INVERSIONS, MAX_OCTAVE, MIN_DEGREE, MIN_OCTAVE};

/// The octaves a chord may be moved by where voice leading may move one: none first, so that a tie keeps the octave
/// written.
const OCTAVE_SHIFTS: [i64; 3] = [0, -1, 1];

/// How far a voicing's notes move from the chord before: lowest to lowest where both have as many notes, and otherwise
/// each note to the nearest of the chord before.
fn movement(pitches: &[i64], before: &[i64]) -> i64 {
    let mut now = pitches.to_vec();
    now.sort_unstable();
    if now.len() == before.len() {
        return now.iter().zip(before).map(|(pitch, other)| (pitch - other).abs()).sum();
    }
    now.iter()
        .map(|pitch| before.iter().map(|other| (pitch - other).abs()).min().unwrap_or(0))
        .sum()
}

/// A chord's pitches, given lowest first, as an inversion plays them: so many of its lowest notes an octave up, never all.
fn inverted(pitches: &[i64], inversion: usize) -> Vec<i64> {
    let moved = inversion.min(pitches.len().saturating_sub(1));
    pitches
        .iter()
        .enumerate()
        .map(|(place, pitch)| if place < moved { pitch + 12 } else { *pitch })
        .collect()
}

/// A chord's pitches in an inversion, moved so many octaves.
fn voiced(pitches: &[i64], inversion: usize, shift: i64) -> Vec<i64> {
    inverted(pitches, inversion).into_iter().map(|pitch| pitch + shift * 12).collect()
}

/// A note, given as a degree, an octave and an accidental, as half steps in a scale.
fn half_steps_of(tone: &Tone, scale: &ChordScale) -> i64 {
    let (degree, octave, accidental) = tone;
    let length = scale.shape.len() as i64;
    let (octaves_up, place) = ((degree - MIN_DEGREE).div_euclid(length), (degree - MIN_DEGREE).rem_euclid(length));
    let shift = match accidental.as_deref() {
        Some("#") => 1,
        Some("b") => -1,
        _ => 0,
    };
    (octave + octaves_up) * 12 + scale.shape[place as usize] + shift
}

/// The octave a step's note plays in: its own, or the default where it has none.
fn octave_at(pattern: &Pattern, step: usize, default_octave: i64) -> i64 {
    value(pattern, Row::OCTAVE, step)
        .and_then(Data::as_whole)
        .map_or(default_octave, |octave| octave as i64)
}

/// A step's chord in root position as half steps, the root first and the notes above it in the order the chord is built,
/// or nothing for a step with no chord.
fn chord_pitches(pattern: &Pattern, step: usize, scale: &ChordScale, default_octave: i64) -> Result<Vec<i64>, InvalidValue> {
    let octave = octave_at(pattern, step, default_octave);
    let degree = value(pattern, Row::DEGREE, step).and_then(Data::as_whole).unwrap_or(1) as i64;
    let accidental = value(pattern, Row::ACCIDENTAL, step).and_then(Data::as_str).map(str::to_string);
    let mut rooted = pattern.clone();
    rooted.set_value(Row::INVERSION, step, None)?;
    let tones = chord_tones(&rooted, step, octave, Some(scale));
    if tones.is_empty() {
        return Ok(Vec::new());
    }
    let root: Tone = (degree, octave, accidental);
    Ok(std::iter::once(&root).chain(&tones).map(|tone| half_steps_of(tone, scale)).collect())
}

/// The inversion and octave shift that move a chord's pitches least from the chord before, root position and no shift
/// winning a tie, keeping the octave within range.
fn nearest_voicing(pitches: &[i64], octave: i64, octaves: bool, before: &[i64]) -> (usize, i64) {
    let shifts: &[i64] = if octaves { &OCTAVE_SHIFTS } else { &OCTAVE_SHIFTS[..1] };
    let inversions: Vec<usize> = std::iter::once(0).chain(INVERSIONS.iter().map(|inversion| *inversion as usize)).collect();
    let mut best: Option<(i64, usize, usize, i64)> = None;
    let mut place = 0;
    for shift in shifts {
        for inversion in &inversions {
            if *inversion < pitches.len() && (MIN_OCTAVE..=MAX_OCTAVE).contains(&(octave + shift)) {
                let moved = movement(&voiced(pitches, *inversion, *shift), before);
                let choice = (moved, place, *inversion, *shift);
                if best.is_none_or(|held| (choice.0, choice.1) < (held.0, held.1)) {
                    best = Some(choice);
                }
            }
            place += 1;
        }
    }
    best.map_or((0, 0), |(_, _, inversion, shift)| (inversion, shift))
}

/// Give every chord after the first the inversion that moves its notes the least from the chord before, and with octaves
/// the octave one lower or higher where that is nearer still; the first chord stays as written, and a chord's Inversion
/// cell is blanked where root position is nearest.
pub fn apply_voice_leading(pattern: &mut Pattern, scale: &ChordScale, default_octave: i64, octaves: bool) -> Result<(), InvalidValue> {
    let mut before: Option<Vec<i64>> = None;
    let written: Vec<usize> = (0..pattern.get_steps().max(0) as usize)
        .filter(|step| value(pattern, Row::DEGREE, *step).is_some())
        .collect();
    for step in written {
        let pitches = chord_pitches(pattern, step, scale, default_octave)?;
        if pitches.is_empty() {
            continue;
        }
        let Some(previous) = &before else {
            let inversion = value(pattern, Row::INVERSION, step).and_then(Data::as_whole).unwrap_or(0) as usize;
            let mut first = inverted(&pitches, inversion);
            first.sort_unstable();
            before = Some(first);
            continue;
        };
        let octave = octave_at(pattern, step, default_octave);
        let (inversion, shift) = nearest_voicing(&pitches, octave, octaves, previous);
        pattern.set_value(Row::INVERSION, step, (inversion != 0).then_some(Data::Whole(inversion as i128)))?;
        if shift != 0 {
            pattern.set_value(Row::OCTAVE, step, Some(Data::Whole((octave + shift) as i128)))?;
        }
        let mut next = voiced(&pitches, inversion, shift);
        next.sort_unstable();
        before = Some(next);
    }
    Ok(())
}
