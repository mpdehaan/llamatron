// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The wavetables the built-in instruments read: one cycle of each waveform, band-limited for each octave, so that a note
//! never holds a harmonic above half the sample rate (the Python engine's `tables.py`, which this follows exactly).
//!
//! A table is `TABLE_SIZE` samples, a power of two, so that a read position wraps with a mask. Each waveform has a table
//! for each octave band, holding its harmonics up to the highest that stays under half the sample rate at the band's top
//! note; a note reads the table of its octave. Built when an instrument is compiled, never while playing.

use llamatron_names::spec;
use rustfft::num_complex::Complex;
use rustfft::FftPlanner;
use std::f64::consts::TAU;
use std::sync::Arc;

/// Half a cycle, where a square turns and a saw crosses zero; the second and third harmonics; and the organ's: the
/// second's and third's levels, and the peak of the three together, which scales it to full.
const HALF: f64 = 0.5;
const SECOND: f64 = 2.0;
const THIRD: f64 = 3.0;
const ORGAN_SECOND: f64 = 0.5;
const ORGAN_THIRD: f64 = 0.33;
const ORGAN_PEAK: f64 = 1.5;

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
            spec::SINE => Some(Waveform::Sine),
            spec::SAW => Some(Waveform::Saw),
            spec::PULSE => Some(Waveform::Pulse),
            spec::SQUARE => Some(Waveform::Square),
            spec::TRIANGLE => Some(Waveform::Triangle),
            _ => None,
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

/// The highest harmonic a band keeps at a sample rate.
fn highest_in_band(band: usize, rate: f64) -> usize {
    let top = LOWEST_FREQUENCY * 2f64.powi(band as i32 + 1);
    (rate / 2.0 / top) as usize
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
        spec::SAW => drawn(|x| (x - HALF) / HALF),
        spec::SQUARE => drawn(|x| if x < HALF { 1.0 } else { -1.0 }),
        spec::SINE => drawn(|x| (TAU * x).sin()),
        spec::ORGAN => drawn(|x| ((TAU * x).sin() + ORGAN_SECOND * (SECOND * TAU * x).sin() + ORGAN_THIRD * (THIRD * TAU * x).sin()) / ORGAN_PEAK),
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

/// The bits of the SID-style chip's waveform DAC, and its R-2R ladder's resistor ratio and leakage on the 6581: its 2R
/// resistors are about 2.2 times its R ones rather than 2, and bit 0 has no termination resistor, so the lower bits run
/// together and the higher ones step unevenly; a switched-off transistor still leaks a little.
const SID_DAC_BITS: usize = 12;
const SID_TWO_R_OVER_R: f64 = 2.20;
const SID_LEAKAGE: f64 = 0.0075;

// The 6581's waveform DAC, after reSID's build_dac_table (dac.cc, Dag Lem, 2010, GPL-2.0-or-later): each bit's voltage
// worked out through the unterminated R-2R ladder by parallel substitution and source transformation, and every word's
// output the superposition of its bits' voltages. The implementation is our own.
/// The DAC's output for every 12-bit word, from 0 to 1.
fn sid_dac() -> Vec<f64> {
    let (r, two_r) = (1.0, SID_TWO_R_OVER_R);
    let mut bit_voltages = [0.0; SID_DAC_BITS];
    for (set_bit, voltage) in bit_voltages.iter_mut().enumerate() {
        // The ladder's tail below the bit, with no termination at bit 0.
        let mut tail = f64::INFINITY;
        for _ in 0..set_bit {
            tail = if tail.is_infinite() { r + two_r } else { r + two_r * tail / (two_r + tail) };
        }
        let mut level = 1.0;
        if tail.is_infinite() {
            tail = two_r;
        } else {
            tail = two_r * tail / (two_r + tail);
            level *= tail / two_r;
        }
        // Carried up the ladder to the output.
        for _ in (set_bit + 1)..SID_DAC_BITS {
            tail += r;
            let current = level / tail;
            tail = two_r * tail / (two_r + tail);
            level = tail * current;
        }
        *voltage = level;
    }
    let most: f64 = bit_voltages.iter().sum();
    (0..1usize << SID_DAC_BITS)
        .map(|word| {
            let sum: f64 = bit_voltages
                .iter()
                .enumerate()
                .map(|(bit, voltage)| if word >> bit & 1 == 1 { *voltage } else { SID_LEAKAGE * voltage })
                .sum();
            sum / most
        })
        .collect()
}

/// The SID-style chip's saw and triangle as its oscillator makes them: the 12 top bits of its phase accumulator, the
/// triangle those bits folded by the top one, each through the 6581's uneven DAC, then band-limited as every table is.
pub fn sid_wave_tables(rate: f64) -> (Tables, Tables) {
    let dac = sid_dac();
    let top = (1usize << SID_DAC_BITS) - 1;
    let words = |place: usize| place * (1 << SID_DAC_BITS) / TABLE_SIZE;
    let level = |word: usize| 2.0 * dac[word & top] - 1.0;
    let saw: Vec<f64> = (0..TABLE_SIZE).map(|place| level(words(place))).collect();
    let triangle: Vec<f64> = (0..TABLE_SIZE)
        .map(|place| {
            let word = words(place);
            let folded = if word >> (SID_DAC_BITS - 1) == 1 { !word } else { word };
            level(folded << 1)
        })
        .collect();
    (cycle_tables(&without_offset(saw), rate), cycle_tables(&without_offset(triangle), rate))
}

/// A cycle with its average taken out, so that an uneven DAC adds no offset.
fn without_offset(cycle: Vec<f64>) -> Vec<f64> {
    let average = cycle.iter().sum::<f64>() / cycle.len() as f64;
    cycle.into_iter().map(|value| value - average).collect()
}

/// The SID-style chip's noise: its 23-bit shift register's values in turn, each read as an eight-bit word of its bits into
/// the top of its waveform DAC, -1 to 1, as the chip outputs it.
pub fn sid_noise() -> Arc<Vec<f32>> {
    let dac = sid_dac();
    let noise_shift = SID_DAC_BITS - 8;
    let mut register: u32 = 0x7FFFF8;
    let mut values = Vec::with_capacity(SID_NOISE_STEPS);
    for _ in 0..SID_NOISE_STEPS {
        let bit = ((register >> 22) ^ (register >> 17)) & 1;
        register = ((register << 1) | bit) & 0x7FFFFF;
        let bit_of = |place: u32, to: u32| ((register >> place) & 1) << to;
        let word = bit_of(20, 7) | bit_of(18, 6) | bit_of(14, 5) | bit_of(11, 4) | bit_of(9, 3) | bit_of(5, 2) | bit_of(2, 1) | (register & 1);
        values.push((2.0 * dac[(word as usize) << noise_shift] - 1.0) as f32);
    }
    Arc::new(values)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A cycle's tables, one an octave band, peak at one, and the top band holds only a few harmonics.
    #[test]
    fn a_table_peaks_at_one_and_the_top_band_holds_few_harmonics() {
        let cycle: Vec<f64> = (0..32).map(|step| if step < 16 { 1.0 } else { -1.0 }).collect();
        let tables = cycle_tables(&cycle, 44100.0);
        assert_eq!(tables.len(), OCTAVE_BANDS);
        let peak = tables[0].iter().fold(0.0_f32, |most, sample| most.max(sample.abs()));
        assert!((peak - 1.0).abs() < 1e-6);
        assert!(highest_in_band(OCTAVE_BANDS - 1, 44100.0) < 4);
    }

    #[test]
    fn the_long_noise_repeats_after_32767_steps_and_the_short_after_127() {
        assert_eq!(shift_register_noise(false).len(), 32767);
        assert_eq!(shift_register_noise(true).len(), 127);
    }

    /// The 6581's DAC is uneven as the chip's is: with no termination resistor, bit 0 alone gives what bit 1 alone gives,
    /// and every bit set reaches the top.
    #[test]
    fn the_sid_dac_runs_its_lowest_bits_together() {
        let dac = sid_dac();
        let (bit_0, bit_1) = (dac[1], dac[2]);
        assert!((bit_0 - bit_1).abs() < bit_1 * 0.05, "bit 0 {bit_0} is about bit 1 {bit_1}");
        assert!((dac[dac.len() - 1] - 1.0).abs() < 1e-9);
    }
}
