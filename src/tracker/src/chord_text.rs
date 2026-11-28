// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A chord in words (the Python interface/tracker/chord_text.py, with the spelling of model/values/chords.py): its name,
//! such as Am, its long name, such as A Minor, and its notes spelled in its scale, such as A C E.

use llamatron_engine::tables::FIXED_CHORDS;
use llamatron_model::schema::generated::file_format::{ChordSymbol, ACCIDENTALS, SCALE_CHORDS, TENSIONS};
use llamatron_model::values::generated::note::{FLAT_NAMES, SHARP_NAMES};
use llamatron_model::values::note::semitones_above_c;
use llamatron_model::values::scale::ScaleType;
use llamatron_names::file_format;
use llamatron_names::fill;
use llamatron_strings::{labels, marks, messages, named};

const HALF_STEPS_PER_OCTAVE: i64 = 12;
const HALF_OCTAVE: i64 = 6;
const LETTERS: &str = "CDEFGAB";
const MOST_SIGNS: i64 = 1;
const ROOT_WITHOUT_A_SCALE: &str = "C";
const SHAPE_WITHOUT_A_SCALE: [i64; 7] = [0, 2, 4, 5, 7, 9, 11];
const PLACED_SCALE_SIZE: usize = 7;
const FLAT: &str = file_format::Accidental::FLAT;
/// How many letters a note above the root stands past it, by its half steps within the octave, and past the octave.
const LETTER_STEPS_WITHIN_THE_OCTAVE: [usize; 12] = [0, 1, 1, 2, 2, 3, 4, 4, 4, 5, 6, 6];
const LETTER_STEPS_PAST_THE_OCTAVE: [(i64, usize); 7] = [(1, 1), (2, 1), (3, 1), (5, 3), (6, 3), (8, 5), (9, 5)];

/// A scale a chord is spelled in: its root's name, its kind's name in a file and its shape in half steps.
#[derive(Clone, Debug)]
pub struct ChordScale {
    pub root: String,
    pub kind: String,
    pub shape: Vec<i64>,
}

impl ChordScale {
    pub fn new(root: &str, kind: &str) -> Option<ChordScale> {
        let shape = ScaleType::named(kind)?.get_shape().to_vec();
        Some(ChordScale {
            root: root.to_string(),
            kind: kind.to_string(),
            shape,
        })
    }
}

/// A chord spelled: its root, its name, its long name and its notes.
pub struct SpelledChord {
    pub root: String,
    pub name: String,
    pub long_name: String,
    pub notes: Vec<String>,
}

/// Text in title case as Python makes it: each letter after one that is not a letter in capitals, the rest in lower case.
pub fn python_title(text: &str) -> String {
    let mut result = String::new();
    let mut after_letter = false;
    for character in text.chars() {
        if character.is_alphabetic() {
            if after_letter {
                result.extend(character.to_lowercase());
            } else {
                result.extend(character.to_uppercase());
            }
            after_letter = true;
        } else {
            result.push(character);
            after_letter = false;
        }
    }
    result
}

/// The scale with another kind on the same root, as a chord borrows it, or the scale itself where the kind is none.
pub fn borrowed(scale: Option<&ChordScale>, kind: Option<&str>) -> Option<ChordScale> {
    match (scale, kind) {
        (Some(scale), Some(kind)) => ChordScale::new(&scale.root, kind).or_else(|| Some(scale.clone())),
        (scale, _) => scale.cloned(),
    }
}

/// A scale as a sentence names it, such as C Major.
pub fn scale_shown(scale: &ChordScale) -> String {
    named(
        marks::MSG_SCALE_NAMED,
        &[
            (fill::ROOT, scale.root.as_str().into()),
            (fill::KIND, python_title(&scale.kind.replace('_', " ")).as_str().into()),
        ],
    )
}

/// A degree as a sentence names it, its accidental's mark in front.
pub fn degree_shown(degree: i64, accidental: Option<&str>) -> String {
    let mark = accidental
        .and_then(|accidental| marks::MSG_ACCIDENTAL_MARKS.iter().find(|(found, _)| *found == accidental))
        .map_or("", |(_, mark)| mark);
    format!("{mark}{degree}")
}

/// A scale's half steps from its root, or the major scale's where there is none.
pub fn shape_of(scale: Option<&ChordScale>) -> Vec<i64> {
    scale.map_or(SHAPE_WITHOUT_A_SCALE.to_vec(), |scale| scale.shape.clone())
}

fn semitones(name: &str) -> i64 {
    semitones_above_c(name).unwrap_or(0)
}

fn letter_steps(half_steps: i64) -> usize {
    let within = half_steps.rem_euclid(HALF_STEPS_PER_OCTAVE);
    if half_steps > HALF_STEPS_PER_OCTAVE {
        if let Some((_, steps)) = LETTER_STEPS_PAST_THE_OCTAVE.iter().find(|(found, _)| *found == within) {
            return *steps;
        }
    }
    LETTER_STEPS_WITHIN_THE_OCTAVE[within as usize]
}

fn letter_at(place: usize) -> char {
    LETTERS.chars().nth(place % LETTERS.len()).unwrap_or('C')
}

fn letter_place(name: &str) -> usize {
    name.chars().next().and_then(|first| LETTERS.find(first)).unwrap_or(0)
}

fn signs_between(pitch: i64, letter: char) -> i64 {
    (pitch - semitones(&letter.to_string()) + HALF_OCTAVE).rem_euclid(HALF_STEPS_PER_OCTAVE) - HALF_OCTAVE
}

fn with_signs(letter: char, signs: i64) -> String {
    if signs > 0 {
        format!("{letter}{}", marks::MSG_SHARP_SPELLED.repeat(signs as usize))
    } else {
        format!("{letter}{}", marks::MSG_FLAT_SPELLED.repeat((-signs) as usize))
    }
}

fn pitch_name(pitch: i64, flat: bool) -> String {
    let place = pitch.rem_euclid(HALF_STEPS_PER_OCTAVE) as usize;
    if flat { FLAT_NAMES[place] } else { SHARP_NAMES[place] }.to_string()
}

fn spelled_note(root: &str, half_steps: i64) -> String {
    let letter = letter_at(letter_place(root) + letter_steps(half_steps));
    let pitch = (semitones(root) + half_steps).rem_euclid(HALF_STEPS_PER_OCTAVE);
    let signs = signs_between(pitch, letter);
    if signs.abs() > MOST_SIGNS {
        return pitch_name(pitch, root.contains(marks::MSG_FLAT_SPELLED));
    }
    with_signs(letter, signs)
}

/// The name of the note on a degree of a scale, an accidental raising or lowering it.
pub fn root_name(scale: Option<&ChordScale>, degree: i64, accidental: Option<&str>) -> String {
    let root = scale.map_or(ROOT_WITHOUT_A_SCALE, |scale| scale.root.as_str());
    let shape = shape_of(scale);
    let place = (degree - 1).rem_euclid(shape.len() as i64) as usize;
    let raised = accidental
        .and_then(|accidental| ACCIDENTALS.iter().find(|(found, _)| *found == accidental))
        .map_or(0, |(_, half_steps)| *half_steps);
    let pitch = (semitones(root) + shape[place] + raised).rem_euclid(HALF_STEPS_PER_OCTAVE);
    let flat = accidental == Some(FLAT);
    if shape.len() != PLACED_SCALE_SIZE {
        return pitch_name(pitch, flat || root.contains(marks::MSG_FLAT_SPELLED));
    }
    let letter = letter_at(letter_place(root) + place);
    let signs = signs_between(pitch, letter);
    if signs.abs() > MOST_SIGNS {
        return pitch_name(pitch, flat);
    }
    with_signs(letter, signs)
}

fn scale_chord_half_steps(scale: Option<&ChordScale>, degree: i64, places: &[i64]) -> Vec<i64> {
    let shape = shape_of(scale);
    let length = shape.len() as i64;
    let start = (degree - 1).rem_euclid(length);
    places
        .iter()
        .map(|above| {
            let (octaves, place) = ((start + above).div_euclid(length), (start + above).rem_euclid(length));
            octaves * HALF_STEPS_PER_OCTAVE + shape[place as usize] - shape[start as usize]
        })
        .collect()
}

fn fixed(symbol: Option<&str>) -> Option<&'static [i64]> {
    symbol
        .and_then(|symbol| FIXED_CHORDS.iter().find(|(found, _)| *found == symbol))
        .map(|(_, half_steps)| *half_steps)
}

fn own_half_steps(scale: Option<&ChordScale>, degree: i64, symbol: Option<&str>, own_degree: Option<i64>) -> Vec<i64> {
    if let Some(half_steps) = fixed(symbol) {
        return half_steps.to_vec();
    }
    let wanted = symbol.unwrap_or(ChordSymbol::SCALE_TRIAD);
    let places: Vec<i64> = SCALE_CHORDS
        .iter()
        .find(|(found, _)| *found == wanted)
        .map_or(Vec::new(), |(_, places)| places.iter().copied().filter(|place| *place != 0).collect());
    scale_chord_half_steps(scale, own_degree.unwrap_or(degree), &places)
}

/// The half steps a chord's notes stand above its root, its tensions after.
pub fn chord_half_steps(scale: Option<&ChordScale>, degree: i64, symbol: Option<&str>, tensions: &[String], own_degree: Option<i64>) -> Vec<i64> {
    let mut half_steps = own_half_steps(scale, degree, symbol, own_degree);
    for tension in tensions {
        if let Some((_, added)) = TENSIONS.iter().find(|(found, _)| found == tension) {
            if !half_steps.contains(added) {
                half_steps.push(*added);
            }
        }
    }
    half_steps
}

fn first_chord_name(symbol: &str) -> String {
    let names = labels::MSG_CHORD_NAMES
        .iter()
        .find(|(found, _)| *found == symbol)
        .map_or("", |(_, names)| names);
    python_title(names.split(',').next().unwrap_or(""))
}

/// A chord on a degree of a scale, spelled: its root's name, its symbol's or the scale's own chord, and its tensions.
pub fn spelled_chord(
    scale: Option<&ChordScale>,
    degree: i64,
    accidental: Option<&str>,
    kind: Option<&str>,
    symbol: Option<&str>,
    tensions: &[String],
    own_degree: Option<i64>,
) -> SpelledChord {
    let drawn_from = borrowed(scale, kind);
    let root = root_name(drawn_from.as_ref(), degree, accidental);
    let own = own_half_steps(drawn_from.as_ref(), degree, symbol, own_degree);
    let mut symbol_named = FIXED_CHORDS
        .iter()
        .find(|(_, half_steps)| *half_steps == own.as_slice())
        .map(|(found, _)| *found);
    if fixed(symbol).is_some() {
        symbol_named = symbol;
    }
    let added: Vec<&str> = TENSIONS
        .iter()
        .filter(|(tension, half_steps)| tensions.iter().any(|found| found == tension) && !own.contains(half_steps))
        .map(|(tension, _)| *tension)
        .collect();
    let shown_tensions = if added.is_empty() {
        String::new()
    } else {
        named(
            marks::MSG_CHORD_TENSIONS_SHOWN,
            &[(fill::TENSIONS, added.join(marks::MSG_TENSION_SEPARATOR).as_str().into())],
        )
    };
    let (suffix, mut long_name) = match symbol_named {
        Some(symbol) => {
            let suffix = marks::MSG_CHORD_SUFFIXES
                .iter()
                .find(|(found, _)| *found == symbol)
                .map_or("", |(_, suffix)| suffix);
            (suffix.to_string(), format!("{root} {}", first_chord_name(symbol)))
        }
        None => (marks::MSG_UNNAMED_CHORD_SUFFIX.to_string(), root.clone()),
    };
    let mut notes = vec![root.clone()];
    for half_steps in &own {
        notes.push(spelled_note(&root, *half_steps));
    }
    for tension in &added {
        if let Some((_, half_steps)) = TENSIONS.iter().find(|(found, _)| found == tension) {
            notes.push(spelled_note(&root, *half_steps));
        }
    }
    long_name = format!("{long_name} {shown_tensions}").trim().to_string();
    SpelledChord {
        name: format!("{root}{suffix}{shown_tensions}"),
        root,
        long_name,
        notes,
    }
}

/// A chord in words, on a degree of a scale, with what changes it.
pub struct ChordInWords {
    pub scale: Option<ChordScale>,
    pub degree: i64,
    pub accidental: Option<String>,
    pub kind: Option<String>,
    pub symbol: Option<String>,
    pub tensions: Vec<String>,
    pub own_degree: Option<i64>,
    /// Whether a chord with no symbol is one note, as a pattern's step is, where a progression's chord with no quality is
    /// the scale's triad.
    pub single_note: bool,
    /// What a pattern's step plays again an octave away (its Double row), or None.
    pub doubling: Option<String>,
}

impl ChordInWords {
    /// Whether the chord is one note: a pattern's step with no chord symbol.
    fn is_one_note(&self) -> bool {
        self.single_note && self.symbol.is_none()
    }

    /// The names of the chord's notes from its root up, or of its one note, or none where no scale is known.
    pub fn note_names(&self) -> Vec<String> {
        if self.scale.is_none() {
            return Vec::new();
        }
        if self.is_one_note() {
            return vec![self.name()];
        }
        self.spelled(self.kind.as_deref()).notes
    }

    /// What the Chord dialog says under its lists: the chord in its scale, the chord in the clip's own scale when it
    /// borrows another, and its notes, with what it doubles.
    pub fn sentences(&self) -> Vec<String> {
        let Some(scale) = &self.scale else {
            return vec![messages::MSG_CHORD_NO_SCALE_KNOWN.to_string()];
        };
        let degree = degree_shown(self.degree, self.accidental.as_deref());
        let drawn_from = borrowed(Some(scale), self.kind.as_deref()).unwrap_or_else(|| scale.clone());
        let doubled: Vec<String> = self
            .doubling
            .iter()
            .map(|doubling| {
                let said = messages::MSG_DOUBLINGS_SAID
                    .iter()
                    .find(|(each, _)| each == doubling)
                    .map_or("", |(_, said)| *said);
                named(messages::MSG_DOUBLED_SENTENCE, &[(fill::DOUBLED, said.into())])
            })
            .collect();
        let shown = scale_shown(&drawn_from);
        if self.is_one_note() {
            let mut lines = vec![named(
                messages::MSG_NOTE_SENTENCE,
                &[
                    (fill::SCALE, shown.as_str().into()),
                    (fill::DEGREE, degree.as_str().into()),
                    (fill::NAME, self.name().as_str().into()),
                ],
            )];
            lines.extend(doubled);
            return lines;
        }
        let long_name = self.spelled(self.kind.as_deref()).long_name;
        let mut lines = vec![named(
            messages::MSG_CHORD_SENTENCE,
            &[
                (fill::SCALE, shown.as_str().into()),
                (fill::DEGREE, degree.as_str().into()),
                (fill::NAME, long_name.as_str().into()),
            ],
        )];
        if self.kind.is_some() {
            lines.push(named(
                messages::MSG_CHORD_OWN_SENTENCE,
                &[
                    (fill::SCALE, scale_shown(scale).as_str().into()),
                    (fill::NAME, self.spelled(None).long_name.as_str().into()),
                ],
            ));
        }
        lines.push(named(messages::MSG_CHORD_NOTES, &[(fill::NOTES, self.notes().as_str().into())]));
        lines.extend(doubled);
        lines
    }

    fn spelled(&self, kind: Option<&str>) -> SpelledChord {
        spelled_chord(
            self.scale.as_ref(),
            self.degree,
            self.accidental.as_deref(),
            kind,
            self.symbol.as_deref(),
            &self.tensions,
            self.own_degree,
        )
    }

    /// The chord's short name, such as A7(b9), or its one note's name.
    pub fn name(&self) -> String {
        if self.is_one_note() {
            return root_name(
                borrowed(self.scale.as_ref(), self.kind.as_deref()).as_ref(),
                self.degree,
                self.accidental.as_deref(),
            );
        }
        self.spelled(self.kind.as_deref()).name
    }

    /// The names of the chord's notes from its root up, as one line.
    pub fn notes(&self) -> String {
        if self.is_one_note() {
            return self.name();
        }
        self.spelled(self.kind.as_deref()).notes.join(marks::MSG_NOTES_SEPARATOR)
    }

    /// What the status line says of the chord at rest, where, or nothing for one note or a scale that isn't known.
    pub fn resting(&self, place: &str) -> String {
        let Some(scale) = &self.scale else { return String::new() };
        if self.is_one_note() {
            return String::new();
        }
        let drawn_from = borrowed(Some(scale), self.kind.as_deref()).unwrap_or_else(|| scale.clone());
        let mut text = named(
            messages::MSG_CHORD_RESTING,
            &[
                (fill::WHERE, place.into()),
                (fill::SCALE, scale_shown(&drawn_from).as_str().into()),
                (fill::DEGREE, degree_shown(self.degree, self.accidental.as_deref()).as_str().into()),
                (fill::NAME, self.spelled(self.kind.as_deref()).long_name.as_str().into()),
                (fill::NOTES, self.notes().as_str().into()),
            ],
        );
        if self.kind.is_some() {
            text.push_str(&named(
                messages::MSG_CHORD_RESTING_OWN,
                &[
                    (fill::SCALE, scale_shown(scale).as_str().into()),
                    (fill::NAME, self.spelled(None).long_name.as_str().into()),
                ],
            ));
        }
        text
    }
}
