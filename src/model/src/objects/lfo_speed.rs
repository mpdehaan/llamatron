// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! An LFO's Speed and Rate, after the range switch of a modular synthesizer's LFO: the Speed chooses a span of rates, Low,
//! Medium, High or Very High, the last at audio rate, and the Rate, 0 to 100%, sweeps across it evenly in octaves, so that
//! each step is a like change at any speed. Its Key ratio sets the rate as a multiple of the note's own frequency instead.

/// Each Speed's name in the file and the span of hertz its Rate sweeps, from 0% to 100%.
pub const SPEEDS: &[(&str, f64, f64)] = &[("low", 0.01, 1.0), ("medium", 0.1, 20.0), ("high", 1.0, 100.0), ("very_high", 20.0, 5000.0)];
/// The Speeds by name, slowest first, as their picker lists them.
pub const SPEED_NAMES: &[&str] = &["low", "medium", "high", "very_high"];
/// The Speed a new LFO has, and the only one a Key ratio is offered at.
pub const DEFAULT_SPEED: &str = "medium";
pub const AUDIO_SPEED: &str = "very_high";
pub const MOST_PERCENT: f64 = 100.0;
/// The ratios to the note a Key LFO offers, as the file writes them, and the one a new one has.
pub const RATIOS: &[&str] = &["1:4", "1:2", "1:1", "3:2", "2:1", "3:1", "4:1", "5:1", "6:1", "7:1", "8:1"];
pub const DEFAULT_RATIO: &str = "1:1";

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

/// The Speed and whole Rate percent nearest a rate in hertz: Medium where it holds the rate, else the nearest span that
/// does, from Low up, so that an older file's LFO keeps its sound.
pub fn speed_of(rate: f64) -> (&'static str, i64) {
    let holds = |(_, low, high): &&(&str, f64, f64)| (*low..=*high).contains(&rate);
    let chosen = SPEEDS
        .iter()
        .find(|speed| speed.0 == DEFAULT_SPEED && holds(speed))
        .or_else(|| SPEEDS.iter().find(holds))
        .unwrap_or(if rate < SPEEDS[0].1 { &SPEEDS[0] } else { &SPEEDS[SPEEDS.len() - 1] });
    let (name, low, high) = *chosen;
    let percent = (MOST_PERCENT * (rate.clamp(low, high) / low).ln() / (high / low).ln()).round() as i64;
    (name, percent)
}

/// A ratio's multiple of the note's frequency, such as 1.5 for 3:2, or 1 for text that is not one.
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

    /// A rate becomes the Speed and percent that give it again within a step's width, and Medium is chosen first.
    #[test]
    fn a_rate_finds_its_speed_and_percent_and_comes_back() {
        let vibrato = 5.0;
        let (speed, percent) = speed_of(vibrato);
        assert_eq!(speed, DEFAULT_SPEED);
        let again = hertz(speed, percent as f64);
        assert!((again / vibrato - 1.0).abs() < 0.03, "{again}");
        assert_eq!(speed_of(2000.0).0, AUDIO_SPEED);
        assert_eq!(speed_of(0.02).0, "low");
        assert_eq!(ratio_multiple("3:2"), 1.5);
    }
}
