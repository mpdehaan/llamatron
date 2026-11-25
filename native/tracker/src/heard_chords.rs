// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The chord heard on each beat of some music, from every note sounding in the beat (the Python
//! music_theory/harmony/heard_chords.py), as Scene View shows it. Each note is counted by how long it sounds in the beat:
//! every note of a chord symbol must sound, up to two others may sound besides as passing notes, and the chord that sounds
//! longest wins, named and numbered in the scale, with the bass after a slash when it isn't the root. The drums are left
//! out.

use crate::chord_text::ChordScale;
use llamatron_engine::tables::FIXED_CHORDS;
use llamatron_math::Rational;
use llamatron_model::schema::generated::file_format::{ChordSymbol, Quality, INTERVAL_CHORDS};
use llamatron_model::values::generated::note::{FLAT_NAMES, SHARP_NAMES};
use llamatron_model::values::note::semitones_above_c;
use llamatron_strings::{marks, named};

/// How many pitch classes may sound in a beat besides its chord, as a melody's passing notes, and the share of the beat a
/// note of the chord sounds through beyond, so that a passing note can't be one.
const MOST_OUTSIDE: usize = 2;
const HELD_SHARE: (i128, i128) = (1, 4);
/// The letters of the notes from C, and the Roman numerals.
const LETTERS: [char; 7] = ['C', 'D', 'E', 'F', 'G', 'A', 'B'];
const ROMAN_NUMERALS: [&str; 7] = ["I", "II", "III", "IV", "V", "VI", "VII"];
/// A chord's third and fifth, as half steps, which say its quality.
const MINOR_THIRD: i64 = 3;
const DIMINISHED_FIFTH: i64 = 6;
const AUGMENTED_FIFTH: i64 = 8;
/// How many letters above a chord's root each of its notes is spelled, by its half steps above it, where they alone decide.
const LETTERS_BY_STEP: [(i64, usize); 10] = [(0, 0), (1, 1), (2, 1), (3, 2), (4, 2), (5, 3), (7, 4), (9, 5), (10, 6), (11, 6)];
const TRITONE: i64 = 6;
const RAISED_FIFTH: i64 = 8;
const PERFECT_FIFTH: i64 = 7;
const MAJOR_SIXTH: i64 = 9;
const MINOR_SEVENTH: i64 = 10;
const MAJOR_SEVENTH: i64 = 11;
const SHARP_ELEVENTH_LETTERS: usize = 3;
const FIFTH_LETTERS: usize = 4;
const SIXTH_LETTERS: usize = 5;
const SEVENTH_LETTERS: usize = 6;

/// The chord heard on a beat: when the beat starts, the chord's name and its Roman numeral in the scale.
#[derive(Clone, Debug, PartialEq)]
pub struct BeatChord {
    pub start: Rational,
    pub name: String,
    pub numeral: String,
}

/// A note sounding: its start and end in whole notes, its MIDI pitch, and whether it is a drum's.
pub struct HeardNote {
    pub start: Rational,
    pub end: Rational,
    pub pitch: i64,
    pub drum: bool,
}

/// How a chord symbol is shown: a major triad as its root alone, a dominant chord by its number alone and a power chord as
/// 5, as lead sheets write them, and any other as llamatron writes it.
fn plain_symbol(symbol: &str) -> &str {
    match symbol {
        ChordSymbol::MAJOR => "",
        ChordSymbol::DOMINANT7 => "7",
        ChordSymbol::DOMINANT9 => "9",
        ChordSymbol::DOMINANT11 => "11",
        ChordSymbol::DOMINANT13 => "13",
        ChordSymbol::POWER => "5",
        other => other,
    }
}

/// A pitch class of a note's name.
fn class_of(name: &str) -> i64 {
    semitones_above_c(name).unwrap_or(0).rem_euclid(12)
}

/// Each fixed chord symbol with its notes as half steps above the root within one octave, the root among them, but for the
/// intervals, which are two notes played together rather than a chord a beat could be heard as.
fn chord_shapes() -> Vec<(&'static str, Vec<i64>)> {
    FIXED_CHORDS
        .iter()
        .filter(|(symbol, _)| !INTERVAL_CHORDS.contains(symbol))
        .map(|(symbol, steps)| {
            let mut shape: Vec<i64> = std::iter::once(0).chain(steps.iter().map(|step| step.rem_euclid(12))).collect();
            shape.sort_unstable();
            shape.dedup();
            (*symbol, shape)
        })
        .collect()
}

fn shape_of(symbol: &str) -> Vec<i64> {
    chord_shapes()
        .into_iter()
        .find(|(found, _)| *found == symbol)
        .map(|(_, shape)| shape)
        .unwrap_or_default()
}

/// A chord a beat might be heard as: how it ranks, its root, its symbol and its notes' pitch classes.
type Candidate = ((Rational, usize, usize, bool), i64, &'static str, Vec<i64>);

/// The chord heard in a beat, as its root's pitch class, its symbol and its bass's pitch class where it isn't the root:
/// weights are the share of the beat each pitch class sounds through; the chord whose notes sound longest wins, then the one
/// with the fewest notes besides it, then the smallest, then the one whose root is the bass.
fn chord_of(weights: &[(i64, Rational)], bass: Option<i64>) -> Option<(i64, &'static str, Option<i64>)> {
    if weights.len() < 2 {
        return None;
    }
    let weight = |class: i64| weights.iter().find(|(found, _)| *found == class).map_or(Rational::ZERO, |(_, weight)| *weight);
    let share = Rational::new(HELD_SHARE.0, HELD_SHARE.1);
    let mut held: Vec<i64> = weights.iter().filter(|(_, weight)| *weight > share).map(|(class, _)| *class).collect();
    held.sort_unstable();
    let shapes = chord_shapes();
    let mut best: Option<Candidate> = None;
    for root in &held {
        for (symbol, shape) in &shapes {
            let members: Vec<i64> = shape.iter().map(|step| (root + step).rem_euclid(12)).collect();
            let outside = weights.iter().filter(|(class, _)| !members.contains(class)).count();
            if !members.iter().all(|member| held.contains(member)) || outside > MOST_OUTSIDE {
                continue;
            }
            let sounded = members.iter().fold(Rational::ZERO, |total, member| total + weight(*member));
            let rank = (Rational::ZERO - sounded, outside, shape.len(), Some(*root) != bass);
            let better = match &best {
                None => true,
                Some((held_rank, ..)) => rank < *held_rank,
            };
            if better {
                best = Some((rank, *root, symbol, members));
            }
        }
    }
    let (_, root, symbol, members) = best?;
    let bass = bass.filter(|bass| Some(root) != Some(*bass) && members.contains(bass));
    Some((root, symbol, bass))
}

/// A chord's quality from its notes above the root: minor or diminished on a minor third, augmented on a raised fifth,
/// major otherwise.
fn quality_of_shape(shape: &[i64]) -> &'static str {
    if shape.contains(&MINOR_THIRD) {
        return if shape.contains(&DIMINISHED_FIFTH) && !shape.contains(&(AUGMENTED_FIFTH - 1)) {
            Quality::DIMINISHED
        } else {
            Quality::MINOR
        };
    }
    if shape.contains(&AUGMENTED_FIFTH) && !shape.contains(&(AUGMENTED_FIFTH - 1)) {
        Quality::AUGMENTED
    } else {
        Quality::MAJOR
    }
}

/// A pitch class's name on a letter, with one sharp or flat at most, or None where it needs more.
fn on_letter(pitch_class: i64, letter: char) -> Option<String> {
    SHARP_NAMES
        .iter()
        .chain(FLAT_NAMES.iter())
        .find(|name| name.starts_with(letter) && class_of(name) == pitch_class)
        .map(|name| name.to_string())
}

/// A seven-note scale's notes spelled as a key signature spells them, each degree on the next letter, or None for another
/// scale or one that would need a double sharp or flat.
fn letter_spelled(scale: &ChordScale) -> Option<Vec<String>> {
    if scale.shape.len() != LETTERS.len() {
        return None;
    }
    let first = scale.root.chars().next()?;
    let start = LETTERS.iter().position(|letter| *letter == first)?;
    let root = semitones_above_c(&scale.root)?;
    scale
        .shape
        .iter()
        .enumerate()
        .map(|(place, step)| on_letter((root + step).rem_euclid(12), LETTERS[(start + place) % LETTERS.len()]))
        .collect()
}

/// A scale's notes as spelled, a degree on each letter where it can be, or no notes for no scale.
fn scale_names(scale: Option<&ChordScale>) -> Vec<String> {
    let Some(scale) = scale else { return Vec::new() };
    letter_spelled(scale).unwrap_or_else(|| {
        crate::screens::set::scale_page::scale_notes(&scale.root, &scale.kind)
            .split(' ')
            .map(str::to_string)
            .collect()
    })
}

/// A pitch class's name as the scale spells it: its own note's name where the scale has it, and otherwise with flats where
/// the scale spells any note with one, or sharps.
fn spelled(pitch_class: i64, scale: Option<&ChordScale>) -> String {
    if scale.is_none() {
        return SHARP_NAMES[pitch_class as usize].to_string();
    }
    let names = scale_names(scale);
    if let Some(name) = names.iter().find(|name| class_of(name) == pitch_class) {
        return name.clone();
    }
    let flats = names
        .iter()
        .any(|name| FLAT_NAMES.contains(&name.as_str()) && !SHARP_NAMES.contains(&name.as_str()));
    (if flats { FLAT_NAMES } else { SHARP_NAMES })[pitch_class as usize].to_string()
}

/// An applied chord, leading to a chord of the key other than its first: its numeral, the degree it leads to, and how
/// many letters above that chord's root its own root is spelled.
struct Applied {
    numeral: String,
    degree: usize,
    letters: usize,
}

/// The triad a seven-note scale builds on one of its degrees, as half steps above the degree's note.
fn degree_triad(shape: &[i64], degree: usize) -> Vec<i64> {
    let length = shape.len();
    let third = (shape[(degree + 2) % length] - shape[degree]).rem_euclid(12);
    let fifth = (shape[(degree + 4) % length] - shape[degree]).rem_euclid(12);
    let mut triad = vec![0, third, fifth];
    triad.sort_unstable();
    triad.dedup();
    triad
}

/// How a chord leads to another chord of a seven-note scale, or None: a major or dominant seventh chord rooted a fifth
/// above it, or a diminished chord a half step below it, with a note outside the scale, leading to a degree whose chord is
/// major or minor, other than the first.
fn applied_chord(root: i64, symbol: &str, scale: Option<&ChordScale>) -> Option<Applied> {
    let scale = scale?;
    let (numeral, below, letters) = match symbol {
        ChordSymbol::MAJOR => (marks::MSG_DOMINANT_NUMERAL, 7, 4),
        ChordSymbol::DOMINANT7 => (marks::MSG_DOMINANT_SEVENTH_NUMERAL, 7, 4),
        ChordSymbol::DIMINISHED => (marks::MSG_LEADING_TONE_NUMERAL, -1, 6),
        ChordSymbol::DIMINISHED7 => (marks::MSG_LEADING_TONE_SEVENTH_NUMERAL, -1, 6),
        _ => return None,
    };
    if scale.shape.len() != ROMAN_NUMERALS.len() {
        return None;
    }
    let tonic = semitones_above_c(&scale.root)?;
    let in_scale = shape_of(symbol).iter().all(|step| scale.shape.contains(&(root + step - tonic).rem_euclid(12)));
    let target = (root - below - tonic).rem_euclid(12);
    if in_scale || !scale.shape.contains(&target) || target == 0 {
        return None;
    }
    let degree = scale.shape.iter().position(|step| *step == target)?;
    let quality = quality_of_shape(&degree_triad(&scale.shape, degree));
    if quality != Quality::MAJOR && quality != Quality::MINOR {
        return None;
    }
    let mut target_numeral = ROMAN_NUMERALS[degree].to_string();
    if quality == Quality::MINOR {
        target_numeral = target_numeral.to_lowercase();
    }
    Some(Applied {
        numeral: named(
            marks::MSG_SECONDARY_DOMINANT,
            &[("dominant", numeral.into()), ("target", target_numeral.as_str().into())],
        ),
        degree,
        letters,
    })
}

/// A chord's root as the key spells it: its note of the scale; an applied chord's on the letter its function gives it; any
/// other with a flat, as a chord borrowed from the minor is.
fn root_name(root: i64, applied: Option<&Applied>, scale: Option<&ChordScale>) -> String {
    let names = scale_names(scale);
    if let Some(name) = names.iter().find(|name| class_of(name) == root) {
        return name.clone();
    }
    if let Some(applied) = applied {
        if let Some(start) = names
            .get(applied.degree)
            .and_then(|name| name.chars().next())
            .and_then(|first| LETTERS.iter().position(|letter| *letter == first))
        {
            if let Some(found) = on_letter(root, LETTERS[(start + applied.letters) % LETTERS.len()]) {
                return found;
            }
        }
    }
    if scale.is_none() {
        return SHARP_NAMES[root as usize].to_string();
    }
    FLAT_NAMES[root as usize].to_string()
}

/// How many letters above a chord's root one of its notes is spelled, by its half steps above the root.
fn letters_above(step: i64, shape: &[i64]) -> usize {
    if step == TRITONE {
        return if shape.contains(&PERFECT_FIFTH) {
            SHARP_ELEVENTH_LETTERS
        } else {
            FIFTH_LETTERS
        };
    }
    if step == RAISED_FIFTH {
        return if shape.contains(&PERFECT_FIFTH) { SIXTH_LETTERS } else { FIFTH_LETTERS };
    }
    if step == MAJOR_SIXTH && shape.contains(&MINOR_THIRD) && shape.contains(&TRITONE) && !shape.contains(&MINOR_SEVENTH) && !shape.contains(&MAJOR_SEVENTH) {
        return SEVENTH_LETTERS;
    }
    LETTERS_BY_STEP.iter().find(|(found, _)| *found == step).map_or(0, |(_, letters)| *letters)
}

/// How a chord's notes are spelled, by pitch class: its root as the key spells it, and each other note on the letter its
/// interval gives it.
fn chord_tone_names(root: i64, symbol: &str, scale: Option<&ChordScale>) -> Vec<(i64, String)> {
    let root_spelling = root_name(root, applied_chord(root, symbol, scale).as_ref(), scale);
    let start = root_spelling
        .chars()
        .next()
        .and_then(|first| LETTERS.iter().position(|letter| *letter == first))
        .unwrap_or(0);
    let shape = shape_of(symbol);
    shape
        .iter()
        .map(|step| {
            let letter = LETTERS[(start + letters_above(*step, &shape)) % LETTERS.len()];
            let pitch_class = (root + step).rem_euclid(12);
            (pitch_class, on_letter(pitch_class, letter).unwrap_or_else(|| spelled(pitch_class, scale)))
        })
        .collect()
}

/// A chord's Roman numeral by its root's degree in the scale, a flat in front for a root between two of its notes, or
/// nothing for a root a flat can't place.
fn root_numeral(root: i64, symbol: &str, scale: &ChordScale) -> String {
    let shape = &scale.shape;
    let mut above = (root - semitones_above_c(&scale.root).unwrap_or(0)).rem_euclid(12);
    let mut accidental = String::new();
    if !shape.contains(&above) {
        above = (above + 1).rem_euclid(12);
        accidental = marks::MSG_ACCIDENTAL_MARKS
            .iter()
            .find(|(sign, _)| *sign == "b")
            .map_or(String::new(), |(_, mark)| mark.to_string());
        if !shape.contains(&above) {
            return String::new();
        }
    }
    let place = shape.iter().position(|step| *step == above).unwrap_or(0);
    let quality = quality_of_shape(&shape_of(symbol));
    let mut numeral = ROMAN_NUMERALS[place % ROMAN_NUMERALS.len()].to_string();
    if quality == Quality::MINOR || quality == Quality::DIMINISHED {
        numeral = numeral.to_lowercase();
    }
    let mark = marks::MSG_QUALITY_MARKS
        .iter()
        .find(|(found, _)| *found == quality)
        .map_or("", |(_, mark)| *mark);
    format!("{accidental}{numeral}{mark}")
}

/// A chord's name, its root spelled in the scale, its symbol, and its bass after a slash where it isn't the root, and its
/// Roman numeral in the scale: an applied chord's by the chord it leads to, as V7/V, any other's by its root.
pub fn chord_texts(root: i64, symbol: &str, scale: Option<&ChordScale>, bass: Option<i64>) -> (String, String) {
    let applied = applied_chord(root, symbol, scale);
    let mut name = format!("{}{}", root_name(root, applied.as_ref(), scale), plain_symbol(symbol));
    if let Some(bass) = bass {
        let tones = chord_tone_names(root, symbol, scale);
        let bass_name = tones
            .iter()
            .find(|(class, _)| *class == bass)
            .map_or_else(|| spelled(bass, scale), |(_, name)| name.clone());
        name = named(
            marks::MSG_SCENE_VIEW_SLASH_CHORD,
            &[("chord", name.as_str().into()), ("bass", bass_name.as_str().into())],
        );
    }
    let Some(scale) = scale else { return (name, String::new()) };
    match applied {
        Some(applied) => (name, applied.numeral),
        None => {
            let numeral = root_numeral(root, symbol, scale);
            (name, numeral)
        }
    }
}

/// How long a set of spans of time cover together, each moment counted once however many spans hold it.
fn covered(spans: &mut [(Rational, Rational)]) -> Rational {
    spans.sort();
    let mut total = Rational::ZERO;
    let mut reach: Option<Rational> = None;
    for (begin, finish) in spans.iter() {
        match reach {
            Some(held) if *begin <= held => {
                if *finish > held {
                    total = total + (*finish - held);
                    reach = Some(*finish);
                }
            }
            _ => {
                total = total + (*finish - *begin);
                reach = Some(*finish);
            }
        }
    }
    total
}

/// The chord on each beat of some music where one is heard, from every note sounding in the beat but the drums', each
/// counted by how long it sounds there.
pub fn beat_chords(notes: &[HeardNote], length: Rational, beat: Rational, scale: Option<&ChordScale>) -> Vec<BeatChord> {
    let mut chords = Vec::new();
    let mut start = Rational::ZERO;
    while start < length {
        let end = start + beat;
        let mut spans: Vec<(i64, Vec<(Rational, Rational)>)> = Vec::new();
        let mut lowest: Option<i64> = None;
        for note in notes {
            if note.drum || note.end <= start || note.start >= end {
                continue;
            }
            let class = note.pitch.rem_euclid(12);
            let span = (note.start.max(start), note.end.min(end));
            match spans.iter_mut().find(|(found, _)| *found == class) {
                Some((_, held)) => held.push(span),
                None => spans.push((class, vec![span])),
            }
            lowest = Some(lowest.map_or(note.pitch, |held: i64| held.min(note.pitch)));
        }
        let weights: Vec<(i64, Rational)> = spans.iter_mut().map(|(class, pieces)| (*class, covered(pieces) / beat)).collect();
        if let Some((root, symbol, bass)) = chord_of(&weights, lowest.map(|pitch| pitch.rem_euclid(12))) {
            let (name, numeral) = chord_texts(root, symbol, scale, bass);
            chords.push(BeatChord { start, name, numeral });
        }
        start = end;
    }
    chords
}
