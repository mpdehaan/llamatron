// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! How much of a sound is stray: the share of a steady tone's energy that falls between its harmonics, where aliasing
//! folds partials back down, measured by a spectrum, for the tests that hold the built-in synths to sounding clean.

use rustfft::num_complex::Complex;
use rustfft::FftPlanner;

/// The bins either side of a harmonic counted as the harmonic's own.
const HARMONIC_WIDTH: usize = 2;
/// Decibels to a power ratio: ten to a power of ten.
const DECIBELS_PER_POWER_DECADE: f64 = 10.0;

/// The stray energy of a second of a steady tone against its harmonics' energy, in decibels: the last `rate` samples
/// read with one bin a hertz, so that a whole-hertz fundamental's harmonics fall exactly on bins.
pub fn stray_decibels(samples: &[f32], rate: usize, fundamental: usize) -> f64 {
    let second = &samples[samples.len() - rate..];
    let mut bins: Vec<Complex<f64>> = second.iter().map(|sample| Complex::new(*sample as f64, 0.0)).collect();
    FftPlanner::new().plan_fft_forward(rate).process(&mut bins);
    let mut harmonic = 0.0;
    let mut stray = 0.0;
    for (hertz, bin) in bins.iter().enumerate().take(rate / 2).skip(1) {
        let nearest = (hertz + fundamental / 2) / fundamental * fundamental;
        let energy = bin.norm_sqr();
        if nearest > 0 && hertz.abs_diff(nearest) <= HARMONIC_WIDTH {
            harmonic += energy;
        } else {
            stray += energy;
        }
    }
    DECIBELS_PER_POWER_DECADE * (stray.max(1e-30) / harmonic.max(1e-30)).log10()
}
