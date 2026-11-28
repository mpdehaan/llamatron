// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! What the backend's tests share: the sample rate they play at, a second's and half a second's samples at it, and
//! the tones they play through a part.

use std::f64::consts::TAU;

/// The sample rate the tests play at, in hertz, and a second, half, a quarter and a tenth of one of its samples.
pub const RATE: f64 = 48000.0;
pub const SECOND: usize = 48000;
pub const HALF_SECOND: usize = 24000;
pub const QUARTER_SECOND: usize = 12000;
pub const TENTH_SECOND: usize = 4800;
/// Two seconds of samples, long enough for a filter to settle and a tone's harmonics to be read.
pub const TWO_SECONDS: usize = 96000;

/// A sine at a frequency and a level, at a sample of the tests' rate.
pub fn sine(hertz: f64, level: f64, place: usize) -> f64 {
    level * (TAU * hertz * place as f64 / RATE).sin()
}

/// The decibels of an amplitude.
pub fn decibels(amplitude: f64) -> f64 {
    super::DECIBELS_A_DECADE * amplitude.log10()
}
