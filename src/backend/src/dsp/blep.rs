// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Band-limited waves made from a phase, every sample: the saw's, the square's and the pulse's jumps smoothed over two
//! samples either side by a polyBLEP whose kernel is the cubic B-spline, and the triangle's corners rounded alike by the
//! matching polyBLAMP, so that a wave stays clean wherever its pitch goes, under glide, vibrato and audio-rate FM, with
//! no table to choose. Above a quarter of the rate, where two samples either side would overlap the next jump, the
//! two-sample polyBLEP takes over. The sine needs nothing. Used by Basic, the SID's pulse and Asheville; the LFOs use
//! the two-sample polyBLEP alone. A hard-synced wave, whose jump falls between samples at the master's reset, is smoothed by the
//! one-sample-delayed form instead, a correction in this sample and the next.
//!
//! After stmlib's ThisBlepSample and NextBlepSample (stmlib/dsp/polyblep.h) and the oscillators of Mutable Instruments'
//! Plaits (plaits/dsp/oscillator/), by Emilie Gillet, MIT; and, for the four-sample corrections, after the
//! B-spline polyBLEP and polyBLAMP of Välimäki, Pekonen and Nam, "Perceptually informed synthesis of bandlimited
//! classical waveforms using integrated polynomial interpolation" (JASA 2012), and Esqueda, Välimäki and Bilbao,
//! "Rounding corners with BLAMP" (DAFx 2016). The residuals are integrated here from the cubic B-spline; the
//! implementation is our own.

/// The widest step a sample at which the four-sample corrections fit: beyond it, two samples either side of one jump
/// would reach the next.
const WIDE_STEP: f64 = 0.25;

/// The two-sided polyBLEP's correction near a jump of two at a cycle's start, at a place in the cycle and a step a sample.
#[inline]
pub fn blep(place: f64, step: f64) -> f64 {
    if step <= 0.0 || step >= 0.5 {
        return 0.0;
    }
    if place < step {
        let t = place / step;
        2.0 * t - t * t - 1.0
    } else if place > 1.0 - step {
        let t = (place - 1.0) / step;
        t * t + 2.0 * t + 1.0
    } else {
        0.0
    }
}

/// The integrated cubic B-spline's distance from a unit step, at some samples from the step on its near side: what a
/// band-limited step still lacks before it, and, negated, what it still has to come down after.
#[inline]
fn spline_step_residual(samples: f64) -> f64 {
    if samples >= 2.0 {
        0.0
    } else if samples >= 1.0 {
        (2.0 - samples).powi(4) / 24.0
    } else {
        0.5 + (-4.0 * samples + 2.0 * samples.powi(3) - 0.75 * samples.powi(4)) / 6.0
    }
}

/// The integrated residual's own integral, the band-limited ramp's distance from a corner of unit change of slope a
/// sample, some samples from the corner on either side.
#[inline]
fn spline_ramp_residual(samples: f64) -> f64 {
    let samples = samples.abs();
    if samples >= 2.0 {
        0.0
    } else if samples >= 1.0 {
        (2.0 - samples).powi(5) / 120.0
    } else {
        1.0 / 120.0 + 0.225 - 0.5 * samples + (2.0 * samples.powi(2) - 0.5 * samples.powi(4) + 0.15 * samples.powi(5)) / 6.0
    }
}

/// The correction near a jump of two at a cycle's start, at a place in the cycle and a step a sample: four samples wide
/// where they fit, else two.
#[inline]
pub fn wide_blep(place: f64, step: f64) -> f64 {
    if step <= 0.0 || step >= WIDE_STEP {
        return blep(place, step);
    }
    let reach = 2.0 * step;
    if place < reach {
        -2.0 * spline_step_residual(place / step)
    } else if place > 1.0 - reach {
        2.0 * spline_step_residual((1.0 - place) / step)
    } else {
        0.0
    }
}

/// The correction near a corner at a cycle's start whose slope rises by some amount a cycle, at a place and a step:
/// four samples wide where they fit, none where they do not, as a corner aliases far less than a jump.
#[inline]
fn wide_blamp(place: f64, step: f64, rise: f64) -> f64 {
    if step <= 0.0 || step >= WIDE_STEP {
        return 0.0;
    }
    let from_corner = if place < 0.5 { place } else { place - 1.0 };
    rise * step * spline_ramp_residual(from_corner / step)
}

/// A rising saw from -1 to 1.
#[inline]
pub fn saw(place: f64, step: f64) -> f64 {
    2.0 * place - 1.0 - wide_blep(place, step)
}

/// A pulse high for the first share of its cycle its width gives, low for the rest.
#[inline]
pub fn pulse(place: f64, step: f64, width: f64) -> f64 {
    let level = if place < width { 1.0 } else { -1.0 };
    level + wide_blep(place, step) - wide_blep((place - width).rem_euclid(1.0), step)
}

/// The triangle's slope, four a cycle up and four down, which turns by eight at each corner.
const TRIANGLE_TURN: f64 = 8.0;

/// A triangle, its two corners rounded: the bottom at the cycle's start, where the slope turns up, and the top at its
/// middle, where it turns down.
#[inline]
pub fn triangle(place: f64, step: f64) -> f64 {
    let bottom = wide_blamp(place, step, TRIANGLE_TURN);
    let top = wide_blamp((place + 0.5).fract(), step, -TRIANGLE_TURN);
    naive_triangle(place) + bottom + top
}

/// A triangle with sharp corners, for a hard-synced wave whose corrections are its own.
#[inline]
pub fn naive_triangle(place: f64) -> f64 {
    1.0 - 4.0 * (place - 0.5).abs()
}

/// A sine.
#[inline]
pub fn sine(place: f64) -> f64 {
    (2.0 * std::f64::consts::PI * place).sin()
}

/// The one-sample-delayed BLEP's share of a jump falling a fraction of a sample before this sample's end, in this sample.
// After stmlib's ThisBlepSample (stmlib/dsp/polyblep.h, Emilie Gillet, MIT).
#[inline]
pub fn this_sample(fraction: f64) -> f64 {
    0.5 * fraction * fraction
}

/// Its share in the next sample.
// After stmlib's NextBlepSample (stmlib/dsp/polyblep.h, Emilie Gillet, MIT).
#[inline]
pub fn next_sample(fraction: f64) -> f64 {
    let rest = 1.0 - fraction;
    -0.5 * rest * rest
}

#[cfg(test)]
mod tests {
    use super::*;

    const RATE: usize = 48_000;

    /// Two seconds of a wave at a whole number of hertz.
    fn played(hertz: usize, wave: impl Fn(f64, f64) -> f64) -> Vec<f32> {
        let step = hertz as f64 / RATE as f64;
        (0..2 * RATE).map(|sample| wave((sample as f64 * step).fract(), step) as f32).collect()
    }

    /// The band-limited waves stay clean on a high note: at 3 kHz the saw's stray tones lie 35 dB and the triangle's 50 dB
    /// under their harmonics, and near the top of the band, at 13 kHz, the saw's still lie 10 dB under.
    #[test]
    fn the_band_limited_waves_stay_clean_on_high_notes() {
        use crate::dsp::spectrum::stray_decibels;
        let (high, highest) = (2_999, 13_001);
        let saw_stray = stray_decibels(&played(high, saw), RATE, high);
        assert!(saw_stray < -35.0, "saw at 3 kHz: {saw_stray:.1} dB");
        let triangle_stray = stray_decibels(&played(high, triangle), RATE, high);
        assert!(triangle_stray < -50.0, "triangle at 3 kHz: {triangle_stray:.1} dB");
        let top_stray = stray_decibels(&played(highest, saw), RATE, highest);
        assert!(top_stray < -10.0, "saw at 13 kHz: {top_stray:.1} dB");
    }
}
