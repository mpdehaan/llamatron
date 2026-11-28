// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! An LFO's Speed and Rate, after the range switch of a modular synthesizer's LFO: the Speed chooses a span of rates, Low,
//! Medium, High or Very High, the last at audio rate, and the Rate, 0 to 100%, sweeps across it evenly in octaves, so that
//! each step is a like change at any speed. Its Key ratio sets the rate as a multiple of the note's own frequency instead.
//! An LFO+ adds the Tempo speed, its Rate a division of the beat that follows the song's tempo.

/// Each Speed's name in the file and the span of hertz its Rate sweeps, from 0% to 100%.
pub const SPEEDS: &[(&str, f64, f64)] = &[("low", 0.01, 1.0), ("medium", 0.1, 20.0), ("high", 1.0, 100.0), ("very_high", 20.0, 5000.0)];
/// The Speeds by name, slowest first, as their picker lists them.
pub const SPEED_NAMES: &[&str] = &["low", "medium", "high", "very_high"];
/// The Speed a new LFO has, and the only one a Key ratio is offered at.
pub const DEFAULT_SPEED: &str = spec::MEDIUM;
pub const AUDIO_SPEED: &str = words::VERY_HIGH;
pub const MOST_PERCENT: f64 = 100.0;
/// The ratios to the note a Key LFO offers, as the file writes them, and the one a new one has.
pub const RATIOS: &[&str] = &["1:4", "1:2", "1:1", "3:2", "2:1", "3:1", "4:1", "5:1", "6:1", "7:1", "8:1"];
pub const DEFAULT_RATIO: &str = "1:1";
/// The LFO+'s own Speed, which follows the song's tempo, and the Speeds an LFO+ offers, the Tempo last.
/// The divisions of the beat a Tempo LFO's cycle lasts, as the file writes them, longest first: a note value, dotted
/// (half as long again) or a triplet (two thirds as long), from sixteen bars down to a sixty-fourth; and the one a synced
/// LFO starts on.
pub const DIVISIONS: &[&str] = &[
    "16/1", "8/1", "4/1", "2/1", "1/1", "1/2", "1/2d", "1/2t", "1/4", "1/4d", "1/4t", "1/8", "1/8d", "1/8t", "1/16", "1/16d", "1/16t", "1/32", "1/32d",
    "1/32t", "1/64", "1/64d", "1/64t",
];
pub const DEFAULT_DIVISION: &str = "1/4";
/// The quarter notes in a whole, and how much longer a dotted and a triplet division last than their note.
const QUARTERS_PER_WHOLE: f64 = 4.0;
const DOTTED: f64 = 1.5;
const TRIPLET: f64 = 2.0 / 3.0;

/// How many quarter notes a division's cycle lasts, such as 0.75 for a dotted eighth, or a quarter's for text that is
/// not one.
pub fn quarters_of(division: &str) -> f64 {
    let (note, length) = match division.strip_suffix('d') {
        Some(note) => (note, DOTTED),
        None => match division.strip_suffix('t') {
            Some(note) => (note, TRIPLET),
            None => (division, 1.0),
        },
    };
    let Some((above, below)) = note.split_once('/') else { return 1.0 };
    match (above.parse::<f64>(), below.parse::<f64>()) {
        (Ok(above), Ok(below)) if below > 0.0 => QUARTERS_PER_WHOLE * above / below * length,
        _ => 1.0,
    }
}

/// A Speed's span, Medium's for a name it does not know.
fn span(speed: &str) -> (f64, f64) {
    let named = |wanted: &str| SPEEDS.iter().find(|(name, ..)| *name == wanted).map(|(_, low, high)| (*low, *high));
    named(speed).or_else(|| named(DEFAULT_SPEED)).expect("Medium is a Speed")
}

/// The hertz a Rate percent gives at a Speed.
pub fn hertz(speed: &str, percent: f64) -> f64 {
    let (low, high) = span(speed);
    low * (high / low).powf(percent.clamp(0.0, MOST_PERCENT) / MOST_PERCENT)
}

/// A ratio's multiple of the note's frequency, such as 1.5 for 3:2, or 1 for text that is not one.
use llamatron_names::spec;
use llamatron_names::words;
pub fn ratio_multiple(ratio: &str) -> f64 {
    let Some((above, below)) = ratio.split_once(':') else { return 1.0 };
    match (above.trim().parse::<f64>(), below.trim().parse::<f64>()) {
        (Ok(above), Ok(below)) if below > 0.0 => above / below,
        _ => 1.0,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A division's cycle in quarter notes: a quarter one, a dotted eighth three quarters of one, an eighth triplet a third.
    #[test]
    fn a_division_lasts_its_quarter_notes() {
        assert_eq!(quarters_of("1/4"), 1.0);
        assert_eq!(quarters_of("1/8d"), 0.75);
        assert!((quarters_of("1/8t") - 1.0 / 3.0).abs() < 1e-12);
        assert_eq!(quarters_of("4/1"), 16.0);
        assert!(DIVISIONS.contains(&DEFAULT_DIVISION));
    }
}
