// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A two-octave keyboard drawn in text (the Python components/keyboard.py), showing which keys a scale uses: the black keys
//! on a row above the white keys, the scale's keys filled and the rest hatched, and the names beneath bracketing the root.

use llamatron_model::values::generated::note::SHARP_NAMES;
use llamatron_model::values::note::semitones_above_c;
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
                named(marks::MSG_ROOT_KEY_NAME, &[("name", note_name.into())])
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
                let name = named(marks::MSG_ROOT_KEY_NAME, &[("name", self.root.as_str().into())]);
                let start = (*column as i64 + BLACK_KEY_SHIFT as i64 + (KEY_WIDTH as i64 - name.chars().count() as i64).div_euclid(2)) as usize;
                put(&mut characters, start, &name);
            }
        }
        characters.into_iter().collect::<String>().trim_end().to_string()
    }

    pub fn lines(&self) -> Vec<String> {
        vec![self.black_row(), self.white_row(), self.names_row()]
    }
}
