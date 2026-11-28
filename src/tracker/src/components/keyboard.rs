// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A two-octave keyboard drawn in text (the Python components/keyboard.py), showing which keys a scale uses: the black keys
//! on a row above the white keys, the scale's keys filled and the rest hatched, and the names beneath bracketing the root.

use llamatron_model::values::generated::note::SHARP_NAMES;
use llamatron_model::values::note::semitones_above_c;
use llamatron_names::fill;
use llamatron_strings::{marks, named};

const WHITE_KEYS: [i64; 7] = [0, 2, 4, 5, 7, 9, 11];
const BLACK_KEY_AFTER: [(i64, i64); 5] = [(0, 1), (2, 3), (5, 6), (7, 8), (9, 10)];
const OCTAVES: usize = 2;
const KEY_WIDTH: usize = 3;
const KEY_GAP: usize = 1;
const KEY_STRIDE: usize = KEY_WIDTH + KEY_GAP;
const WHITE_ROW_INDENT: usize = 4;
const BLACK_KEY_SHIFT: usize = 2;

pub struct Keyboard {
    pub root: String,
    pub half_steps: Vec<i64>,
    /// The keys a chord's notes are, numbered from the lowest C, which rows() draws apart.
    pub chord: Vec<i64>,
}

/// What a key of the keyboard is when a chord is drawn on it: a key of the chord, of the scale, or outside the scale.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum KeyKind {
    Chord,
    Scale,
    Outside,
}

/// A line of a keyboard as pieces, each a text and the kind of key it is, or None for what is no key.
pub type KeyRow = Vec<(String, Option<KeyKind>)>;

/// How many keys the keyboard has, numbered from its lowest C.
const KEY_COUNT: i64 = OCTAVES as i64 * 12;

/// The keys of the keyboard a chord's notes are, as numbers from the lowest C: the root in the first octave and each note
/// after it the next key up of its name, an inversion's lowest notes an octave higher, and a note past the last key an
/// octave lower, so that every note of the chord has a key.
pub fn chord_keys(note_names: &[String], inversion: Option<usize>, doubling: Option<&str>) -> Vec<i64> {
    let mut keys: Vec<i64> = Vec::new();
    let mut last = -1;
    for name in note_names {
        let mut key = semitones_above_c(name).unwrap_or(0).rem_euclid(12);
        while key <= last {
            key += 12;
        }
        last = key;
        keys.push(key);
    }
    let raised = inversion.unwrap_or(0).min(keys.len());
    for key in keys.iter_mut().take(raised) {
        *key += 12;
    }
    if let Some(doubling) = doubling {
        keys = doubled_keys(&keys, doubling);
    }
    let mut shown: Vec<i64> = keys.into_iter().map(|key| if key < KEY_COUNT { key } else { key % 12 + 12 }).collect();
    shown.sort_unstable();
    shown.dedup();
    shown
}

/// A chord's keys with those its Double row plays again an octave away, as the Realizer plays them, the whole moved up an
/// octave where a note doubled down would fall below the keyboard's lowest C.
fn doubled_keys(keys: &[i64], doubling: &str) -> Vec<i64> {
    let Some(&(_, first, last, octaves)) = crate::generated::tables::DOUBLED_NOTES.iter().find(|(name, ..)| *name == doubling) else {
        return keys.to_vec();
    };
    let mut by_pitch = keys.to_vec();
    by_pitch.sort_unstable();
    let count = by_pitch.len() as i64;
    // The places are a slice's, a negative one counted from the end.
    let at = |place: i64| if place < 0 { (count + place).max(0) } else { place.min(count) } as usize;
    let (from, to) = (at(first), last.map_or(by_pitch.len(), at));
    let added: Vec<i64> = by_pitch[from..to.max(from)].iter().map(|key| key + octaves * 12).collect();
    let mut every: Vec<i64> = keys.iter().chain(&added).copied().collect();
    every.sort_unstable();
    every.dedup();
    if every.first().is_some_and(|lowest| *lowest < 0) {
        every = every.into_iter().map(|key| key + 12).collect();
    }
    every
}

/// The three lines of one octave of keys, one key filled and its name bracketed: the keyswitch note picker's keys.
pub fn one_octave_rows(pitch_class: i64) -> Vec<KeyRow> {
    let keyboard = Keyboard {
        root: SHARP_NAMES[pitch_class.rem_euclid(12) as usize].to_string(),
        half_steps: Vec::new(),
        chord: vec![pitch_class.rem_euclid(12)],
    };
    let rows = keyboard.rows();
    let pieces = 1 + WHITE_KEYS.len() * 2;
    let width = WHITE_ROW_INDENT + WHITE_KEYS.len() * KEY_STRIDE;
    let names: String = rows[2][0].0.chars().take(width).collect();
    vec![
        rows[0][..pieces].to_vec(),
        rows[1][..pieces].to_vec(),
        vec![(names.trim_end().to_string(), None)],
    ]
}

fn black_after(pitch_class: i64) -> Option<i64> {
    BLACK_KEY_AFTER.iter().find(|(white, _)| *white == pitch_class).map(|(_, black)| *black)
}

/// Text centred as Python's str.center centres it.
fn centred(text: &str, width: usize) -> String {
    crate::drawing::fit_aligned(text, width, crate::drawing::Align::Center)
}

impl Keyboard {
    fn root_pitch_class(&self) -> i64 {
        semitones_above_c(&self.root).unwrap_or(0).rem_euclid(12)
    }

    fn pitch_classes(&self) -> Vec<i64> {
        let root = self.root_pitch_class();
        self.half_steps.iter().map(|step| (root + step).rem_euclid(12)).collect()
    }

    fn key_text(&self, pitch_class: i64) -> &'static str {
        if self.pitch_classes().contains(&pitch_class) {
            marks::MSG_KEY_IN_SCALE
        } else {
            marks::MSG_KEY_OUT_OF_SCALE
        }
    }

    fn white_keys(&self) -> Vec<(i64, usize)> {
        let mut keys = Vec::new();
        for octave in 0..OCTAVES {
            for (place, pitch_class) in WHITE_KEYS.iter().enumerate() {
                keys.push((*pitch_class, WHITE_ROW_INDENT + (octave * WHITE_KEYS.len() + place) * KEY_STRIDE));
            }
        }
        keys
    }

    fn black_row(&self) -> String {
        let mut line = " ".repeat(WHITE_ROW_INDENT + BLACK_KEY_SHIFT);
        for (pitch_class, _) in self.white_keys() {
            match black_after(pitch_class) {
                Some(black) => line.push_str(self.key_text(black)),
                None => line.push_str(&" ".repeat(KEY_WIDTH)),
            }
            line.push_str(&" ".repeat(KEY_GAP));
        }
        line.trim_end().to_string()
    }

    fn white_row(&self) -> String {
        let mut line = " ".repeat(WHITE_ROW_INDENT);
        for (pitch_class, _) in self.white_keys() {
            line.push_str(self.key_text(pitch_class));
            line.push_str(&" ".repeat(KEY_GAP));
        }
        line.trim_end().to_string()
    }

    fn names_row(&self) -> String {
        let root = self.root_pitch_class();
        let keys = self.white_keys();
        let mut characters: Vec<char> = " ".repeat(WHITE_ROW_INDENT + keys.len() * KEY_STRIDE).chars().collect();
        let put = |characters: &mut Vec<char>, start: usize, text: &str| {
            for (offset, character) in text.chars().enumerate() {
                if start + offset < characters.len() {
                    characters[start + offset] = character;
                } else {
                    characters.push(character);
                }
            }
        };
        for (place, (pitch_class, column)) in keys.iter().enumerate() {
            let note_name = SHARP_NAMES[*pitch_class as usize];
            let mut name = if *pitch_class == root {
                named(marks::MSG_ROOT_KEY_NAME, &[(fill::NAME, note_name.into())])
            } else {
                centred(note_name, KEY_WIDTH)
            };
            if black_after(*pitch_class) == Some(root) || (place > 0 && black_after(keys[place - 1].0) == Some(root)) {
                name = String::new();
            }
            put(&mut characters, *column, &name);
        }
        for (pitch_class, column) in &keys {
            if black_after(*pitch_class) == Some(root) {
                let name = named(marks::MSG_ROOT_KEY_NAME, &[(fill::NAME, self.root.as_str().into())]);
                let start = (*column as i64 + BLACK_KEY_SHIFT as i64 + (KEY_WIDTH as i64 - name.chars().count() as i64).div_euclid(2)) as usize;
                put(&mut characters, start, &name);
            }
        }
        characters.into_iter().collect::<String>().trim_end().to_string()
    }

    pub fn lines(&self) -> Vec<String> {
        vec![self.black_row(), self.white_row(), self.names_row()]
    }

    /// What a key is, by its number from the lowest C.
    fn key_kind(&self, key: i64) -> KeyKind {
        if self.chord.contains(&key) {
            KeyKind::Chord
        } else if self.pitch_classes().contains(&key.rem_euclid(12)) {
            KeyKind::Scale
        } else {
            KeyKind::Outside
        }
    }

    /// A key as a piece: a chord's key filled, a scale's outlined and one outside the scale hatched.
    fn key_piece(&self, key: i64) -> (String, Option<KeyKind>) {
        let kind = self.key_kind(key);
        let text = match kind {
            KeyKind::Chord => marks::MSG_KEY_IN_CHORD,
            KeyKind::Scale => marks::MSG_KEY_OF_SCALE_OUTLINED,
            KeyKind::Outside => marks::MSG_KEY_OUT_OF_SCALE,
        };
        (text.to_string(), Some(kind))
    }

    /// The keyboard's three lines as pieces: the black keys, the white keys, and the names, with the chord's keys told apart
    /// from the scale's.
    pub fn rows(&self) -> Vec<KeyRow> {
        let mut black: KeyRow = vec![(" ".repeat(WHITE_ROW_INDENT + BLACK_KEY_SHIFT), None)];
        let mut white: KeyRow = vec![(" ".repeat(WHITE_ROW_INDENT), None)];
        for octave in 0..OCTAVES as i64 {
            for pitch_class in WHITE_KEYS {
                let first = octave * 12;
                match black_after(pitch_class) {
                    Some(after) => black.push(self.key_piece(first + after)),
                    None => black.push((" ".repeat(KEY_WIDTH), None)),
                }
                black.push((" ".repeat(KEY_GAP), None));
                white.push(self.key_piece(first + pitch_class));
                white.push((" ".repeat(KEY_GAP), None));
            }
        }
        vec![black, white, vec![(self.names_row(), None)]]
    }
}

/// A keyboard's rows drawn, each piece in the style its kind of key is given, or plain.
pub fn keyboard_lines(rows: &[KeyRow], style_of: &dyn Fn(Option<KeyKind>) -> &'static str) -> Vec<crate::text::Text> {
    rows.iter()
        .map(|row| {
            let mut line = crate::text::Text::default();
            for (text, kind) in row {
                line.append(text, style_of(*kind));
            }
            line
        })
        .collect()
}
