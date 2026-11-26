// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The file format's tables whose values the generated constants cannot hold (the Python file_format.py's FIXED_CHORDS,
//! GATE_MODIFIERS and DOUBLED_NOTES), written by hand.

use llamatron_math::Rational;

/// Each fixed chord symbol with the half steps its notes stand above the root (the Python FIXED_CHORDS).
pub static FIXED_CHORDS: &[(&str, &[i64])] = &[
    ("M", &[4, 7]),
    ("m", &[3, 7]),
    ("sus2", &[2, 7]),
    ("sus4", &[5, 7]),
    ("dim", &[3, 6]),
    ("aug", &[4, 8]),
    ("pow", &[7]),
    ("M6", &[4, 7, 9]),
    ("m6", &[3, 7, 9]),
    ("dom7", &[4, 7, 10]),
    ("M7", &[4, 7, 11]),
    ("m7", &[3, 7, 10]),
    ("mM7", &[3, 7, 11]),
    ("dim7", &[3, 6, 9]),
    ("m7b5", &[3, 6, 10]),
    ("aug7", &[4, 8, 10]),
    ("augM7", &[4, 8, 11]),
    ("7sus4", &[5, 7, 10]),
    ("add9", &[4, 7, 14]),
    ("madd9", &[3, 7, 14]),
    ("dom9", &[4, 7, 10, 14]),
    ("M9", &[4, 7, 11, 14]),
    ("m9", &[3, 7, 10, 14]),
    ("dom11", &[4, 7, 10, 14, 17]),
    ("M11", &[4, 7, 11, 14, 17]),
    ("m11", &[3, 7, 10, 14, 17]),
    ("dom13", &[4, 7, 10, 14, 17, 21]),
    ("M13", &[4, 7, 11, 14, 17, 21]),
    ("m13", &[3, 7, 10, 14, 17, 21]),
    ("+P8", &[12]),
    ("+m3", &[3]),
    ("+M3", &[4]),
    ("+P4", &[5]),
    ("+m6", &[8]),
    ("+M6", &[9]),
];

/// What a step's gate is multiplied by when its Dot row makes it dotted or a triplet.
pub fn gate_modifier(symbol: &str) -> Option<Rational> {
    match symbol {
        "d" => Some(Rational::new(3, 2)),
        "t" => Some(Rational::new(2, 3)),
        _ => None,
    }
}

/// The notes a Double row plays again, as a slice of the notes by pitch from first to last (None for to the end), and the
/// octaves away it plays them.
pub fn doubled_notes(symbol: &str) -> Option<(isize, Option<isize>, i64)> {
    match symbol {
        "low_up" => Some((0, Some(1), 1)),
        "all_up" => Some((0, None, 1)),
        "all_down" => Some((0, None, -1)),
        "top_down" => Some((-1, None, -1)),
        _ => None,
    }
}

pub fn fixed_chord(symbol: &str) -> Option<&'static [i64]> {
    FIXED_CHORDS.iter().find(|(found, _)| *found == symbol).map(|(_, shape)| *shape)
}
