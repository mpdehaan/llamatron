// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! How much of a sound is stray: the share of a steady tone's energy that falls between its harmonics, where aliasing
//! folds partials back down, measured by a spectrum, for the tests that hold the built-in synths to sounding clean.

use rustfft::num_complex::Complex;
use rustfft::FftPlanner;

/// Halves, by which a spectrum's top is half its rate and a harmonic's band half a fundamental either side; and the
/// smallest energy a ratio is taken of, so that silence divides by nothing.
const HALVES: usize = 2;
const SMALLEST_ENERGY: f64 = 1e-30;

/// The bins either side of a harmonic counted as the harmonic's own.
const HARMONIC_WIDTH: usize = 2;
/// Decibels to a power ratio: ten to a power of ten.
const DECIBELS_PER_POWER_DECADE: f64 = 10.0;

/// The stray energy of a second of a steady tone against its harmonics' energy, in decibels: the last `rate` samples
/// read with one bin a hertz, so that a whole-hertz fundamental's harmonics fall exactly on bins.
pub fn stray_decibels(samples: &[f32], rate: usize, fundamental: usize) -> f64 {
    stray_decibels_under(samples, rate, fundamental, rate / HALVES)
}

/// The stray energy under a frequency, as `stray_decibels` measures it, against all the harmonics' energy: what is
/// heard of the aliasing, leaving out what falls in the top octave's last few kilohertz.
pub fn stray_decibels_under(samples: &[f32], rate: usize, fundamental: usize, top_hertz: usize) -> f64 {
    let second = &samples[samples.len() - rate..];
    let mut bins: Vec<Complex<f64>> = second.iter().map(|sample| Complex::new(*sample as f64, 0.0)).collect();
    FftPlanner::new().plan_fft_forward(rate).process(&mut bins);
    let mut harmonic = 0.0;
    let mut stray = 0.0;
    for (hertz, bin) in bins.iter().enumerate().take(rate / HALVES).skip(1) {
        let nearest = (hertz + fundamental / HALVES) / fundamental * fundamental;
        let energy = bin.norm_sqr();
        if nearest > 0 && hertz.abs_diff(nearest) <= HARMONIC_WIDTH {
            harmonic += energy;
        } else if hertz < top_hertz {
            stray += energy;
        }
    }
    DECIBELS_PER_POWER_DECADE * (stray.max(SMALLEST_ENERGY) / harmonic.max(SMALLEST_ENERGY)).log10()
}

/// The level of one harmonic of a second of a steady tone against the fundamental's, in decibels, read as
/// `stray_decibels` reads the spectrum.
pub fn harmonic_decibels(samples: &[f32], rate: usize, fundamental: usize, harmonic: usize) -> f64 {
    let second = &samples[samples.len() - rate..];
    let mut bins: Vec<Complex<f64>> = second.iter().map(|sample| Complex::new(*sample as f64, 0.0)).collect();
    FftPlanner::new().plan_fft_forward(rate).process(&mut bins);
    let energy_near = |hertz: usize| -> f64 { (hertz - HARMONIC_WIDTH..=hertz + HARMONIC_WIDTH).map(|bin| bins[bin].norm_sqr()).sum() };
    DECIBELS_PER_POWER_DECADE * (energy_near(fundamental * harmonic).max(SMALLEST_ENERGY) / energy_near(fundamental).max(SMALLEST_ENERGY)).log10()
}
