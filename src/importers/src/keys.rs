// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The keys an import plays in (the Python importers/keys.py and music_theory/analysis/keys.py): a file's key signature
//! taken as a major or minor scale, or, where it says none, the key its notes are in by how long each note of the octave
//! sounds against the Krumhansl-Kessler profiles; and each note written as a degree of the key, a note outside it a degree
//! with a sharp or a flat, flats where the key's signature has them.

use crate::python_sum;
use crate::reading::PartNote;
use llamatron_math::Rational;
use llamatron_model::values::generated::note::{FLAT_NAMES, MAX_OCTAVE, MIN_OCTAVE, ROOT_NAMES, SHARP_NAMES};
use llamatron_names::file_format;

const MAJOR_PROFILE: [f64; 12] = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88];
const MINOR_PROFILE: [f64; 12] = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17];
const MAJOR_ROOTS: [&str; 12] = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];
const MINOR_ROOTS: [&str; 12] = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"];
const FLAT_KEYS: [&str; 5] = ["F", "Dm", "Gm", "Cm", "Fm"];
const MAJOR_STEPS: [i64; 7] = [0, 2, 4, 5, 7, 9, 11];
const MINOR_STEPS: [i64; 7] = [0, 2, 3, 5, 7, 8, 10];

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct MusicalKey {
    pub root: String,
    pub kind: String,
    pub flats: bool,
}

pub fn pitch_class_of(name: &str) -> i64 {
    SHARP_NAMES
        .iter()
        .chain(FLAT_NAMES)
        .position(|found| *found == name)
        .map(|place| place as i64 % 12)
        .unwrap_or(0)
}

impl MusicalKey {
    pub fn half_steps(&self) -> &'static [i64] {
        if self.kind == file_format::NamedProgression::MINOR {
            &MINOR_STEPS
        } else {
            &MAJOR_STEPS
        }
    }

    pub fn root_place(&self) -> i64 {
        pitch_class_of(&self.root)
    }

    /// The pitch classes of the key's scale.
    pub fn places(&self) -> Vec<i64> {
        let mut places: Vec<i64> = self.half_steps().iter().map(|steps| (self.root_place() + steps).rem_euclid(12)).collect();
        places.sort();
        places
    }
}

/// The key a key signature names, such as Bb or F#m.
pub fn key_of_signature(text: &str) -> MusicalKey {
    let minor = text.ends_with('m');
    let mut root = if minor { text[..text.len() - 1].to_string() } else { text.to_string() };
    let flats = root.ends_with('b') || FLAT_KEYS.contains(&text);
    if !ROOT_NAMES.contains(&root.as_str()) {
        root = SHARP_NAMES[(pitch_class_of(&root[..1]) - 1).rem_euclid(12) as usize].to_string();
    }
    MusicalKey {
        root,
        kind: if minor {
            file_format::NamedProgression::MINOR
        } else {
            file_format::Quality::MAJOR
        }
        .to_string(),
        flats,
    }
}

/// A span of a note heard, for working out a key.
pub trait Heard {
    fn start(&self) -> Rational;
    fn end(&self) -> Rational;
    fn pitch(&self) -> i64;
}

impl Heard for PartNote {
    fn start(&self) -> Rational {
        self.start
    }
    fn end(&self) -> Rational {
        self.end
    }
    fn pitch(&self) -> i64 {
        self.pitch
    }
}

fn correlation(first: &[f64; 12], second: &[f64; 12]) -> f64 {
    let first_mean = python_sum(first.iter().copied()) / 12.0;
    let second_mean = python_sum(second.iter().copied()) / 12.0;
    let together = python_sum(first.iter().zip(second).map(|(a, b)| (a - first_mean) * (b - second_mean)));
    let spread = (python_sum(first.iter().map(|a| (a - first_mean) * (a - first_mean)))
        * python_sum(second.iter().map(|b| (b - second_mean) * (b - second_mean))))
    .powf(0.5);
    if spread != 0.0 {
        together / spread
    } else {
        0.0
    }
}

/// The key some notes are in, by how long each note of the octave sounds against the profiles.
pub fn key_of_notes(notes: &[impl Heard]) -> MusicalKey {
    let mut weights = [0.0f64; 12];
    for note in notes {
        weights[note.pitch().rem_euclid(12) as usize] += (note.end() - note.start()).to_float();
    }
    let mut best = (0usize, false, -1.0f64);
    for tonic in 0..12 {
        let rotated: [f64; 12] = std::array::from_fn(|place| weights[(tonic + place) % 12]);
        for (minor, profile) in [(false, &MAJOR_PROFILE), (true, &MINOR_PROFILE)] {
            let fit = correlation(&rotated, profile);
            if fit > best.2 {
                best = (tonic, minor, fit);
            }
        }
    }
    let (tonic, minor, _) = best;
    let root = if minor { MINOR_ROOTS[tonic] } else { MAJOR_ROOTS[tonic] };
    MusicalKey {
        root: root.to_string(),
        kind: if minor {
            file_format::NamedProgression::MINOR
        } else {
            file_format::Quality::MAJOR
        }
        .to_string(),
        flats: root.ends_with('b'),
    }
}

/// A note written as a degree of a key, its accidental, and its octave, the octave whose root the degree counts up from;
/// or None outside the octaves.
pub fn degree_of(pitch: i64, key: &MusicalKey) -> Option<(i64, Option<&'static str>, i64)> {
    let steps = key.half_steps();
    let moved = pitch - key.root_place();
    let (octave, above) = (moved.div_euclid(12), moved.rem_euclid(12));
    let place = |half_steps: i64| steps.iter().position(|step| *step == half_steps).map(|place| place as i64 + 1);
    let (degree, accidental, octave) = if let Some(degree) = place(above) {
        (degree, None, octave)
    } else if let Some(degree) = place(above + 1).filter(|_| key.flats) {
        (degree, Some(file_format::Accidental::FLAT), octave)
    } else if let Some(degree) = place(above - 1) {
        (degree, Some("#"), octave)
    } else if above + 1 == 12 {
        (1, Some(file_format::Accidental::FLAT), octave + 1)
    } else {
        (place(above + 1).unwrap_or(1), Some(file_format::Accidental::FLAT), octave)
    };
    (MIN_OCTAVE..=MAX_OCTAVE).contains(&octave).then_some((degree, accidental, octave))
}

/// A drum's note: its letter, a sharp where it has one, and its octave.
pub fn drum_note_of(pitch: i64) -> (String, Option<&'static str>, i64) {
    let name = SHARP_NAMES[pitch.rem_euclid(12) as usize];
    let letter = &name[..1];
    (letter.to_string(), (name != letter).then_some("#"), pitch.div_euclid(12))
}
