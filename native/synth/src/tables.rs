// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The wavetables the built-in instruments read: one cycle of each waveform, band-limited for each octave, so that a note
//! never holds a harmonic above half the sample rate (the Python engine's `tables.py`, which this follows exactly).
//!
//! A table is `TABLE_SIZE` samples, a power of two, so that a read position wraps with a mask. Each waveform has a table
//! for each octave band, holding its harmonics up to the highest that stays under half the sample rate at the band's top
//! note; a note reads the table of its octave. Built when an instrument is compiled, never while playing.

use rustfft::num_complex::Complex;
use rustfft::FftPlanner;
use std::f64::consts::PI;
use std::sync::Arc;

pub const TABLE_SIZE: usize = 2048;
pub const TABLE_MASK: usize = TABLE_SIZE - 1;
/// How many steps of the SID-style chip's noise are kept.
pub const SID_NOISE_STEPS: usize = 32768;
/// The lowest note a band serves, as a frequency, and how many octave bands there are above it.
pub const LOWEST_FREQUENCY: f64 = 8.0;
pub const OCTAVE_BANDS: usize = 12;

/// One waveform's tables, a band each, lowest first.
pub type Tables = Arc<Vec<Vec<f32>>>;

/// The waveforms a table can hold.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Waveform {
    Sine,
    Saw,
    Pulse,
    Square,
    Triangle,
}

impl Waveform {
    /// The waveform a set names, or None for one it does not know.
    pub fn named(name: &str) -> Option<Waveform> {
        match name {
            "sine" => Some(Waveform::Sine),
            "saw" => Some(Waveform::Saw),
            "pulse" => Some(Waveform::Pulse),
            "square" => Some(Waveform::Square),
            "triangle" => Some(Waveform::Triangle),
            _ => None,
        }
    }
}

/// The amplitude of each harmonic from the first of a waveform's Fourier series; a pulse's are the saw's, since a pulse is
/// read as one saw less another shifted by its width.
fn harmonic_amplitude(waveform: Waveform, number: usize) -> f64 {
    let n = number as f64;
    match waveform {
        Waveform::Sine => {
            if number == 1 {
                1.0
            } else {
                0.0
            }
        }
        Waveform::Saw | Waveform::Pulse => {
            let sign = if number % 2 == 1 { 1.0 } else { -1.0 };
            2.0 / PI * sign / n
        }
        Waveform::Square => {
            if number % 2 == 1 {
                4.0 / (PI * n)
            } else {
                0.0
            }
        }
        Waveform::Triangle => {
            if number.is_multiple_of(2) {
                return 0.0;
            }
            let sign = if ((number - 1) / 2).is_multiple_of(2) { 1.0 } else { -1.0 };
            8.0 / (PI * PI) * sign / (n * n)
        }
    }
}

/// One table from a half spectrum, by the inverse real transform, scaled to peak at 1.
fn from_spectrum(planner: &mut FftPlanner<f64>, spectrum: &[Complex<f64>]) -> Vec<f32> {
    // The full Hermitian spectrum, so that a complex inverse transform gives the real signal numpy's irfft gives.
    let mut full = vec![Complex::new(0.0, 0.0); TABLE_SIZE];
    for (bin, value) in spectrum.iter().enumerate() {
        full[bin] = *value;
        if bin > 0 && bin < TABLE_SIZE / 2 {
            full[TABLE_SIZE - bin] = value.conj();
        }
    }
    planner.plan_fft_inverse(TABLE_SIZE).process(&mut full);
    let table: Vec<f64> = full.iter().map(|value| value.re / TABLE_SIZE as f64).collect();
    let peak = table.iter().fold(0.0_f64, |most, sample| most.max(sample.abs())).max(1e-9);
    table.iter().map(|sample| (sample / peak) as f32).collect()
}

/// One cycle of a waveform holding its harmonics up to the highest given, no more than a table can hold.
fn band_limited_table(planner: &mut FftPlanner<f64>, waveform: Waveform, highest_harmonic: usize) -> Vec<f32> {
    let count = highest_harmonic.clamp(1, TABLE_SIZE / 2 - 1);
    let mut spectrum = vec![Complex::new(0.0, 0.0); TABLE_SIZE / 2 + 1];
    for (number, bin) in spectrum.iter_mut().enumerate().skip(1).take(count) {
        // A sine of amplitude a at harmonic n is the bin -i * a * N / 2.
        *bin = Complex::new(0.0, -harmonic_amplitude(waveform, number) * TABLE_SIZE as f64 / 2.0);
    }
    from_spectrum(planner, &spectrum)
}

/// The highest harmonic a band keeps at a sample rate.
fn highest_in_band(band: usize, rate: f64) -> usize {
    let top = LOWEST_FREQUENCY * 2f64.powi(band as i32 + 1);
    (rate / 2.0 / top) as usize
}

/// A waveform's tables, one for each octave band, lowest first, at a sample rate.
pub fn waveform_tables(waveform: Waveform, rate: f64) -> Tables {
    let mut planner = FftPlanner::new();
    Arc::new(
        (0..OCTAVE_BANDS)
            .map(|band| band_limited_table(&mut planner, waveform, highest_in_band(band, rate)))
            .collect(),
    )
}

/// The octave band a frequency reads its table from.
pub fn band_of(frequency: f64) -> usize {
    if frequency <= LOWEST_FREQUENCY {
        return 0;
    }
    ((frequency / LOWEST_FREQUENCY).log2() as usize).min(OCTAVE_BANDS - 1)
}

/// The tables of any one cycle, such as a chip's duty pulse or its 32 steps of drawn wave: its harmonics measured by one
/// transform, then each band keeping those under half the rate, so that a stepped wave keeps its steps up to where they would
/// alias, and no further.
pub fn cycle_tables(cycle: &[f64], rate: f64) -> Tables {
    let mut planner = FftPlanner::new();
    let repeat = TABLE_SIZE / cycle.len();
    let mut signal: Vec<Complex<f64>> = cycle.iter().flat_map(|step| std::iter::repeat_n(Complex::new(*step, 0.0), repeat)).collect();
    planner.plan_fft_forward(TABLE_SIZE).process(&mut signal);
    let mut spectrum: Vec<Complex<f64>> = signal[..TABLE_SIZE / 2 + 1].to_vec();
    spectrum[0] = Complex::new(0.0, 0.0);
    Arc::new(
        (0..OCTAVE_BANDS)
            .map(|band| {
                let highest = highest_in_band(band, rate).clamp(1, TABLE_SIZE / 2 - 1);
                let kept: Vec<Complex<f64>> = spectrum
                    .iter()
                    .enumerate()
                    .map(|(bin, value)| if (1..=highest).contains(&bin) { *value } else { Complex::new(0.0, 0.0) })
                    .collect();
                from_spectrum(&mut planner, &kept)
            })
            .collect(),
    )
}

/// The tables of a chip's pulse of a duty, the share of its eight steps it is high.
pub fn duty_tables(duty: f64, rate: f64) -> Tables {
    let high = (duty * 8.0).round() as usize;
    let cycle: Vec<f64> = (0..8).map(|step| if step < high { 1.0 } else { -1.0 }).collect();
    cycle_tables(&cycle, rate)
}

/// The 32 steps of four bits a drawn wave of a shape holds, 0 to 15, as the chip's wave memory holds them.
fn drawn(function: fn(f64) -> f64) -> Vec<f64> {
    (0..32).map(|place| ((function(place as f64 / 32.0) + 1.0) * 7.5).round()).collect()
}

/// The tables of a drawn wave of 32 steps of four bits, by its shape's name; a triangle for a name it does not know.
pub fn shape_tables(shape: &str, rate: f64) -> Tables {
    let steps = match shape {
        "saw" => drawn(|x| 2.0 * x - 1.0),
        "square" => drawn(|x| if x < 0.5 { 1.0 } else { -1.0 }),
        "sine" => drawn(|x| (2.0 * PI * x).sin()),
        "organ" => drawn(|x| ((2.0 * PI * x).sin() + 0.5 * (4.0 * PI * x).sin() + 0.33 * (6.0 * PI * x).sin()) / 1.5),
        _ => drawn(|x| 1.0 - 4.0 * (x - 0.5).abs()),
    };
    let cycle: Vec<f64> = steps.iter().map(|step| step / 7.5 - 1.0).collect();
    cycle_tables(&cycle, rate)
}

/// A chip's noise as the values a shift register gives in turn, -1 or 1: 32767 of the long hiss from 15 bits, or 127 of the
/// short metallic buzz from 7, the register's two lowest bits made one by exclusive or and fed back at the top.
pub fn shift_register_noise(short: bool) -> Arc<Vec<f32>> {
    let width = if short { 7 } else { 15 };
    let mut register: u32 = (1 << width) - 1;
    let mut values = Vec::with_capacity((1 << width) - 1);
    for _ in 0..((1 << width) - 1) {
        let bit = (register ^ (register >> 1)) & 1;
        register = (register >> 1) | (bit << (width - 1));
        values.push(if register & 1 == 1 { 1.0 } else { -1.0 });
    }
    Arc::new(values)
}

/// The SID-style chip's noise: its 23-bit shift register's values in turn, each read as an eight-bit word of its bits, -1 to
/// 1, as the chip outputs it.
pub fn sid_noise() -> Arc<Vec<f32>> {
    let mut register: u32 = 0x7FFFF8;
    let mut values = Vec::with_capacity(SID_NOISE_STEPS);
    for _ in 0..SID_NOISE_STEPS {
        let bit = ((register >> 22) ^ (register >> 17)) & 1;
        register = ((register << 1) | bit) & 0x7FFFFF;
        let bit_of = |place: u32, to: u32| ((register >> place) & 1) << to;
        let word = bit_of(20, 7) | bit_of(18, 6) | bit_of(14, 5) | bit_of(11, 4) | bit_of(9, 3) | bit_of(5, 2) | bit_of(2, 1) | (register & 1);
        values.push((word as f64 / 127.5 - 1.0) as f32);
    }
    Arc::new(values)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_table_peaks_at_one_and_the_top_band_holds_few_harmonics() {
        let saw = waveform_tables(Waveform::Saw, 44100.0);
        assert_eq!(saw.len(), OCTAVE_BANDS);
        let peak = saw[0].iter().fold(0.0_f32, |most, sample| most.max(sample.abs()));
        assert!((peak - 1.0).abs() < 1e-6);
        assert!(highest_in_band(OCTAVE_BANDS - 1, 44100.0) < 4);
    }

    #[test]
    fn the_long_noise_repeats_after_32767_steps_and_the_short_after_127() {
        assert_eq!(shift_register_noise(false).len(), 32767);
        assert_eq!(shift_register_noise(true).len(), 127);
    }
}
