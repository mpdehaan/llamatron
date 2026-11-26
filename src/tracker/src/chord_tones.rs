// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The notes a step's chord adds above its own note (the Python pattern_notes.py's chord_tones), each a degree, an octave
//! and a sharp or flat in the scale the pattern plays under: the piano roll draws them as thin lines, and voice leading
//! measures chords by them.

use crate::chord_text::{borrowed, chord_half_steps, ChordScale};
use crate::patterns::value;
use llamatron_model::file::data::Data;
use llamatron_model::fundamentals::role_of;
use llamatron_model::objects::pattern::Pattern;
use llamatron_model::schema::generated::file_format::{Row, BASS_NOTES, OMITTED_ROLES, SCALE_CHORDS};
use llamatron_model::schema::generated::limits::MIN_DEGREE;

/// A note as the roll places one: its degree, its octave and its sharp or flat.
pub type Tone = (i64, i64, Option<String>);

/// What a scale chord's notes are to the chord, by how many scale steps above its root they are, for its Omit row.
const SCALE_CHORD_ROLES: [(i64, &str); 2] = [(2, "third"), (4, "fifth")];
/// The notes of a scale where the roll's scale isn't known, which a Bass counts in.
const DIATONIC_NOTES: i64 = 7;
const SHARP: &str = "#";
const FLAT: &str = "b";

/// The half steps a sharp or flat moves a note.
fn accidental_steps(accidental: Option<&str>) -> i64 {
    match accidental {
        Some(SHARP) => 1,
        Some(FLAT) => -1,
        _ => 0,
    }
}

/// The degree, octave and accidental of the note so many half steps above a degree of a scale: a note on a scale note is
/// that degree; one a half step above a scale note is that degree sharpened, or the next degree flattened where it is a
/// half step below that; and a note that is neither, in a scale with a wide gap, is None, since no row can show it.
pub fn degree_above(scale: &ChordScale, degree: i64, octave: i64, accidental: Option<&str>, half_steps: i64) -> Option<Tone> {
    let steps = &scale.shape;
    let length = steps.len() as i64;
    let (octaves_up, place) = ((degree - MIN_DEGREE).div_euclid(length), (degree - MIN_DEGREE).rem_euclid(length));
    let total = (octave + octaves_up) * 12 + steps[place as usize] + accidental_steps(accidental) + half_steps;
    let (tone_octave, within) = (total.div_euclid(12), total.rem_euclid(12));
    let below = steps.iter().rposition(|step| *step <= within).unwrap_or(0);
    if steps[below] == within {
        return Some((below as i64 + MIN_DEGREE, tone_octave, None));
    }
    if within - steps[below] == 1 {
        return Some((below as i64 + MIN_DEGREE, tone_octave, Some(SHARP.to_string())));
    }
    let above = steps.get(below + 1).copied().unwrap_or(12);
    if above - within == 1 {
        let (octaves_more, place_above) = ((below as i64 + 1).div_euclid(length), (below as i64 + 1).rem_euclid(length));
        return Some((place_above + MIN_DEGREE, tone_octave + octaves_more, Some(FLAT.to_string())));
    }
    None
}

/// A step's value as text, a number written as one.
fn text(pattern: &Pattern, row: &str, step: usize) -> Option<String> {
    match value(pattern, row, step)? {
        Data::Text(text) => Some(text.clone()),
        Data::Whole(whole) => Some(whole.to_string()),
        _ => None,
    }
}

/// The notes a step's chord adds above its own note. A scale chord's tones are scale degrees above the step's, whatever
/// the scale; a named chord's are half steps from the note, placed in the scale the pattern plays under, and with no scale
/// known there are none. The octave is the step's, or the pattern's default where the step has none.
pub fn chord_tones(pattern: &Pattern, step: usize, octave: i64, scale: Option<&ChordScale>) -> Vec<Tone> {
    let Some(degree) = value(pattern, Row::DEGREE, step).and_then(Data::as_whole) else {
        return Vec::new();
    };
    if pattern.is_drum() {
        return Vec::new();
    }
    let degree = degree as i64;
    let accidental = text(pattern, Row::ACCIDENTAL, step);
    let root: Tone = (degree, octave, accidental.clone());
    let omit = text(pattern, Row::OMIT, step);
    let omitted: &[&str] = omit
        .as_deref()
        .and_then(|omit| OMITTED_ROLES.iter().find(|(name, _)| *name == omit))
        .map_or(&[], |(_, roles)| roles);
    let inversion = value(pattern, Row::INVERSION, step)
        .and_then(Data::as_whole)
        .map_or(0, |inversion| inversion as usize);
    let (tones, inverted) = match text(pattern, Row::CHORD, step) {
        None => (Vec::new(), false),
        Some(symbol) => {
            let Some(tones) = tones_above(pattern, step, &root, &symbol, scale, omitted) else {
                return Vec::new();
            };
            if omitted.contains(&"root") {
                // A rootless chord sounds as its tones alone, which its inversion and doubling then voice.
                (inverted_rootless(&tones, inversion), true)
            } else {
                // An inversion moves a chord's lowest notes, never all, so a chord of two notes or more is inverted wherever it asks.
                let inverted = inversion > 0 && !tones.is_empty();
                (inverted_tones(&root, &tones, inversion), inverted)
            }
        }
    };
    let tones = doubled_tones(&root, tones, inverted, text(pattern, Row::DOUBLE, step).as_deref());
    let bass = bass_tones(pattern, step, &root, scale);
    with_bass_tones(&root, tones, inverted, &bass)
}

/// The tones a step's chord adds above its root, its Omit row's roles left out, or None where the scale a named chord needs
/// isn't known.
fn tones_above(pattern: &Pattern, step: usize, root: &Tone, symbol: &str, scale: Option<&ChordScale>, omitted: &[&str]) -> Option<Vec<Tone>> {
    let (degree, octave, accidental) = root.clone();
    let tensions: Vec<String> = value(pattern, Row::TENSION, step).and_then(Data::as_list).map_or(Vec::new(), |tensions| {
        tensions.iter().filter_map(|tension| tension.as_str().map(str::to_string)).collect()
    });
    let kind = text(pattern, Row::CHORD_SCALE, step);
    if let (Some(scale), true) = (scale, !tensions.is_empty() || kind.is_some()) {
        return Some(tones_leaving_the_scale(scale, root, symbol, &tensions, kind.as_deref(), omitted));
    }
    if let Some((_, places)) = SCALE_CHORDS.iter().find(|(name, _)| *name == symbol) {
        let role = |above: i64| SCALE_CHORD_ROLES.iter().find(|(steps, _)| *steps == above).map(|(_, role)| *role);
        return Some(
            places
                .iter()
                .filter(|above| **above != 0 && role(**above).is_none_or(|role| !omitted.contains(&role)))
                .map(|above| (degree + above, octave, accidental.clone()))
                .collect(),
        );
    }
    let scale = scale?;
    let half_steps = llamatron_engine::tables::fixed_chord(symbol)?;
    Some(
        half_steps
            .iter()
            .filter(|steps| role_of(**steps).is_none_or(|role| !omitted.contains(&role)))
            .filter_map(|steps| degree_above(scale, degree, octave, accidental.as_deref(), *steps))
            .collect(),
    )
}

/// The tones of a chord with tensions or a borrowed scale type, placed in the scale the roll draws: the chord is worked out
/// in the scale it borrows, as half steps from that scale's first note, and each note placed among the roll's own scale's
/// degrees, sharpened or flattened where it lies between two. A borrowed root that is not the note drawn is a tone too.
fn tones_leaving_the_scale(scale: &ChordScale, root: &Tone, symbol: &str, tensions: &[String], kind: Option<&str>, omitted: &[&str]) -> Vec<Tone> {
    let (degree, octave, accidental) = root.clone();
    let source = borrowed(Some(scale), kind).unwrap_or_else(|| scale.clone());
    let at = |shape: &[i64]| {
        let length = shape.len() as i64;
        (degree - MIN_DEGREE).div_euclid(length) * 12 + shape[(degree - MIN_DEGREE).rem_euclid(length) as usize] + accidental_steps(accidental.as_deref())
    };
    let root_steps = at(&source.shape);
    let own = chord_half_steps(Some(&source), degree, Some(symbol), &[], None).len();
    let mut above: Vec<i64> = chord_half_steps(Some(&source), degree, Some(symbol), tensions, None)
        .into_iter()
        .enumerate()
        .filter(|(place, steps)| *place >= own || role_of(*steps).is_none_or(|role| !omitted.contains(&role)))
        .map(|(_, steps)| steps)
        .collect();
    if root_steps != at(&scale.shape) {
        above.insert(0, 0);
    }
    above
        .iter()
        .filter_map(|steps| degree_above(scale, MIN_DEGREE, octave, None, root_steps + steps))
        .collect()
}

/// The tones of a chord whose root is left out, as its inversion plays them: its lowest tones an octave up, never all.
fn inverted_rootless(tones: &[Tone], inversion: usize) -> Vec<Tone> {
    let moved = inversion.min(tones.len().saturating_sub(1));
    if moved == 0 {
        return tones.to_vec();
    }
    let lifted = tones[..moved]
        .iter()
        .map(|(degree, octave, accidental)| (*degree, octave + 1, accidental.clone()));
    tones[moved..].iter().cloned().chain(lifted).collect()
}

/// A chord's tones above its root as an inversion plays them: its lowest notes, the root first, an octave up.
fn inverted_tones(root: &Tone, tones: &[Tone], inversion: usize) -> Vec<Tone> {
    if inversion == 0 {
        return tones.to_vec();
    }
    let notes: Vec<Tone> = std::iter::once(root.clone()).chain(tones.iter().cloned()).collect();
    let moved = inversion.min(notes.len() - 1);
    if moved == 0 {
        return tones.to_vec();
    }
    let lifted = notes[..moved]
        .iter()
        .map(|(degree, octave, accidental)| (*degree, octave + 1, accidental.clone()));
    notes[moved..].iter().cloned().chain(lifted).collect()
}

/// The tones with those a step's Double row plays again an octave away, a tone already sounding left out.
fn doubled_tones(root: &Tone, tones: Vec<Tone>, inverted: bool, doubling: Option<&str>) -> Vec<Tone> {
    let Some(&(_, first, last, octaves)) = doubling.and_then(|doubling| crate::generated::tables::DOUBLED_NOTES.iter().find(|(name, ..)| *name == doubling))
    else {
        return tones;
    };
    let sounding: Vec<Tone> = if inverted {
        tones.clone()
    } else {
        std::iter::once(root.clone()).chain(tones.iter().cloned()).collect()
    };
    let count = sounding.len() as i64;
    let at = |place: i64| if place < 0 { (count + place).max(0) } else { place.min(count) } as usize;
    let (from, to) = (at(first), last.map_or(sounding.len(), at));
    let mut added: Vec<Tone> = Vec::new();
    for (degree, octave, accidental) in &sounding[from..to.max(from)] {
        let tone = (*degree, octave + octaves, accidental.clone());
        if !sounding.contains(&tone) && !added.contains(&tone) {
            added.push(tone);
        }
    }
    tones.into_iter().chain(added).collect()
}

/// A step's Bass as the tones the roll draws for it: the bass, and with Bass Octave the octave below it.
fn bass_tones(pattern: &Pattern, step: usize, root: &Tone, scale: Option<&ChordScale>) -> Vec<Tone> {
    let Some(bass) = text(pattern, Row::BASS, step) else { return Vec::new() };
    let Some((_, note)) = BASS_NOTES.iter().find(|(name, _)| *name == bass) else {
        return Vec::new();
    };
    let (steps, half_steps) = (note[0], note[1]);
    let size = scale.map_or(DIATONIC_NOTES, |scale| scale.shape.len() as i64);
    let (degree, octave, _) = root;
    let total = degree - MIN_DEGREE + steps;
    let accidental = match half_steps {
        -1 => Some(FLAT.to_string()),
        1 => Some(SHARP.to_string()),
        _ => None,
    };
    let tone = (total.rem_euclid(size) + MIN_DEGREE, octave + total.div_euclid(size), accidental);
    if matches!(value(pattern, Row::BASS_OCTAVE, step), Some(Data::Bool(true))) {
        let lower = (tone.0, tone.1 - 1, tone.2.clone());
        return vec![tone, lower];
    }
    vec![tone]
}

/// A chord's tones with its bass tones moved to the nearest octave below the chord's lowest, the bass's octave the octave
/// below that.
fn with_bass_tones(root: &Tone, tones: Vec<Tone>, inverted: bool, bass: &[Tone]) -> Vec<Tone> {
    let Some((degree, octave, accidental)) = bass.first().cloned() else {
        return tones;
    };
    let sounding: Vec<Tone> = if inverted {
        tones.clone()
    } else {
        std::iter::once(root.clone()).chain(tones.iter().cloned()).collect()
    };
    let lowest = sounding.iter().map(|(degree, octave, _)| (*octave, *degree)).min().unwrap_or((octave, degree));
    let mut octave = octave;
    while (octave, degree) >= lowest {
        octave -= 1;
    }
    while (octave + 1, degree) < lowest {
        octave += 1;
    }
    let mut placed = vec![(degree, octave, accidental.clone())];
    if bass.len() > 1 {
        placed.push((degree, octave - 1, accidental));
    }
    tones.into_iter().chain(placed).collect()
}
