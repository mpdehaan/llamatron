// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Band-limited waves made from a phase, every sample: the saw's, the square's and the pulse's jumps smoothed by a
//! two-sample polyBLEP, the triangle and the sine left as they are, so that a wave stays bright and clean wherever its
//! pitch goes, under glide, vibrato and audio-rate FM, with no table to choose. Used by the LFOs, Basic, the SID's pulse
//! and Asheville. A hard-synced wave, whose jump falls between samples at the master's reset, is smoothed by the
//! one-sample-delayed form instead, a correction in this sample and the next.
//!
//! After stmlib's ThisBlepSample and NextBlepSample (stmlib/dsp/polyblep.h) and the oscillators of Mutable Instruments'
//! Plaits (plaits/dsp/oscillator/), by Emilie Gillet, MIT; the implementation here is our own.

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

/// A rising saw from -1 to 1.
#[inline]
pub fn saw(place: f64, step: f64) -> f64 {
    2.0 * place - 1.0 - blep(place, step)
}

/// A pulse high for the first share of its cycle its width gives, low for the rest.
#[inline]
pub fn pulse(place: f64, step: f64, width: f64) -> f64 {
    let level = if place < width { 1.0 } else { -1.0 };
    level + blep(place, step) - blep((place - width).rem_euclid(1.0), step)
}

/// A triangle, whose corners alias little enough to leave as they are.
#[inline]
pub fn triangle(place: f64) -> f64 {
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

    /// A smoothed saw stays within its bounds and is continuous across its jump: no two samples further apart than the
    /// jump the naive saw makes.
    #[test]
    fn a_smoothed_saw_eases_its_jump() {
        let step = 0.05;
        let values: Vec<f64> = (0..200).map(|sample| saw((sample as f64 * step).fract(), step)).collect();
        let most_jump = values.windows(2).map(|pair| (pair[1] - pair[0]).abs()).fold(0.0, f64::max);
        assert!(most_jump < 2.0, "{most_jump}");
        assert!(values.iter().all(|value| value.abs() <= 1.0 + 1e-9));
    }
}
