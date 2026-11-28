// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Small pieces of signal processing every part shares: a biquad section and its designs (Butterworth low and high
//! passes, a band pass by centre and Q), and a seeded random source, so that a drum hit renders the same every time.

pub mod blep;
pub mod one_pole;
pub mod oversample;
pub mod saturation;

#[cfg(test)]
pub mod spectrum;
#[cfg(test)]
pub mod testing;

use std::f64::consts::TAU;

/// The ratio an octave multiplies a frequency by.
pub const OCTAVE: f64 = 2.0;
/// Decibels as an amplitude: twenty of them a tenfold.
pub const DECIBELS_A_DECADE: f64 = 20.0;
/// Twice, as a biquad's cosine and Q are doubled in its coefficients, and half, as its zeros are halved.
const TWICE: f64 = 2.0;
/// A biquad's coefficients, three a side.
const COEFFICIENTS: usize = 3;
/// The golden ratio's bits, SplitMix64's step: every seeded source in the backend steps or mixes by it.
pub const GOLDEN_GAMMA: u64 = 0x9E37_79B9_7F4A_7C15;
/// SplitMix64's three shifts and two multipliers, and the shift and bits by which a draw's top 53 bits become a share
/// from 0 to 1.
pub const SPLITMIX_SHIFTS: [u32; 3] = [30, 27, 31];
pub const SPLITMIX_MULTIPLIERS: [u64; 2] = [0xBF58_476D_1CE4_E5B9, 0x94D0_49BB_1331_11EB];
pub const SPLITMIX_LAST: usize = 2;
pub const SHARE_SHIFT: u32 = 11;
pub const SHARE_BITS: u32 = 53;
/// The smallest uniform draw Box and Muller's transform takes the logarithm of, so that it never takes zero's.
const SMALLEST_DRAW: f64 = 1e-300;
/// The bits of a byte, which CRC-32 shifts through one at a time, and its reversed polynomial, zlib's.
const BITS_A_BYTE: usize = 8;
const CRC32_POLYNOMIAL: u32 = 0xEDB8_8320;

/// Below this a filter's state is flushed to zero, so that a decaying tail never falls into denormal numbers, which are slow.
pub const TINY: f64 = 1e-20;
/// The highest share of the sample rate a cutoff may reach.
pub const HIGHEST_SHARE: f64 = 0.45;

/// One second-order section in transposed direct form II, its coefficients normalized so that a0 is 1.
#[derive(Clone, Copy, Debug, Default)]
pub struct Biquad {
    pub b0: f64,
    pub b1: f64,
    pub b2: f64,
    pub a1: f64,
    pub a2: f64,
    pub s1: f64,
    pub s2: f64,
}

impl Biquad {
    fn normalized(b: [f64; COEFFICIENTS], a: [f64; COEFFICIENTS]) -> Biquad {
        Biquad {
            b0: b[0] / a[0],
            b1: b[1] / a[0],
            b2: b[COEFFICIENTS - 1] / a[0],
            a1: a[1] / a[0],
            a2: a[COEFFICIENTS - 1] / a[0],
            s1: 0.0,
            s2: 0.0,
        }
    }

    /// A low pass at a cutoff and Q, by the bilinear transform with its cutoff prewarped; Q of 1/√2 is Butterworth.
    pub fn low_pass(cutoff: f64, quality: f64, rate: f64) -> Biquad {
        let (cosine, alpha) = angle(cutoff, quality, rate);
        Biquad::normalized(
            [(1.0 - cosine) / TWICE, 1.0 - cosine, (1.0 - cosine) / TWICE],
            [1.0 + alpha, -TWICE * cosine, 1.0 - alpha],
        )
    }

    /// A high pass at a cutoff and Q.
    pub fn high_pass(cutoff: f64, quality: f64, rate: f64) -> Biquad {
        let (cosine, alpha) = angle(cutoff, quality, rate);
        Biquad::normalized(
            [(1.0 + cosine) / TWICE, -(1.0 + cosine), (1.0 + cosine) / TWICE],
            [1.0 + alpha, -TWICE * cosine, 1.0 - alpha],
        )
    }

    /// A band pass of unit gain at its centre, its width the centre over its Q.
    pub fn band_pass(centre: f64, quality: f64, rate: f64) -> Biquad {
        let (cosine, alpha) = angle(centre, quality, rate);
        Biquad::normalized([alpha, 0.0, -alpha], [1.0 + alpha, -TWICE * cosine, 1.0 - alpha])
    }

    /// One sample through the section.
    #[inline]
    pub fn process(&mut self, input: f64) -> f64 {
        let out = self.b0 * input + self.s1;
        self.s1 = self.b1 * input - self.a1 * out + self.s2;
        self.s2 = self.b2 * input - self.a2 * out;
        out
    }

    /// Flush a state too small to hear, and clear one not finite.
    #[inline]
    pub fn flush(&mut self) {
        self.s1 = flushed(self.s1);
        self.s2 = flushed(self.s2);
    }

    /// Back to rest.
    pub fn reset(&mut self) {
        self.s1 = 0.0;
        self.s2 = 0.0;
    }
}

/// A biquad's cosine of its frequency's angle a sample, and its alpha, the sine over twice its Q.
fn angle(frequency: f64, quality: f64, rate: f64) -> (f64, f64) {
    let frequency = frequency.clamp(1.0, HIGHEST_SHARE * rate);
    let w = TAU * frequency / rate;
    (w.cos(), w.sin() / (TWICE * quality))
}

/// A filter's state flushed to zero when too small to hear or not a number at all.
#[inline]
pub fn flushed(value: f64) -> f64 {
    if value.abs() >= TINY {
        value
    } else {
        0.0
    }
}

/// The Q of a second-order Butterworth section.
pub const BUTTERWORTH_Q: f64 = std::f64::consts::FRAC_1_SQRT_2;
/// The Qs of a fourth-order Butterworth's two sections.
pub const BUTTERWORTH_FOUR_Q: [f64; 2] = [0.541_196_100_146_197, 1.306_562_964_876_376_5];

/// A whole signal through a cascade of sections, from rest.
pub fn filtered(sections: &mut [Biquad], signal: &mut [f64]) {
    for section in sections.iter_mut() {
        section.reset();
        for sample in signal.iter_mut() {
            *sample = section.process(*sample);
        }
    }
}

/// The sections of a pair.
const PAIR: usize = 2;

/// A band pass as the drum recipes ask for it: two sections of a centre and Q, steeper than one, as a fourth-order band
/// pass is.
pub fn band_pass_pair(centre: f64, quality: f64, rate: f64) -> [Biquad; PAIR] {
    let section = Biquad::band_pass(centre, quality * std::f64::consts::SQRT_2, rate);
    [section, section]
}

/// A seeded random source, splitmix64, giving uniform and normal numbers, the same every time for one seed.
pub struct Random {
    state: u64,
    spare: Option<f64>,
}

impl Random {
    pub fn new(seed: u64) -> Random {
        Random { state: seed, spare: None }
    }

    pub fn next_u64(&mut self) -> u64 {
        self.state = self.state.wrapping_add(GOLDEN_GAMMA);
        let mut value = self.state;
        value = (value ^ (value >> SPLITMIX_SHIFTS[0])).wrapping_mul(SPLITMIX_MULTIPLIERS[0]);
        value = (value ^ (value >> SPLITMIX_SHIFTS[1])).wrapping_mul(SPLITMIX_MULTIPLIERS[1]);
        value ^ (value >> SPLITMIX_SHIFTS[SPLITMIX_LAST])
    }

    /// A uniform number from 0 up to 1.
    pub fn uniform(&mut self) -> f64 {
        (self.next_u64() >> SHARE_SHIFT) as f64 / (1u64 << SHARE_BITS) as f64
    }

    /// A uniform number between two bounds.
    pub fn between(&mut self, low: f64, high: f64) -> f64 {
        low + (high - low) * self.uniform()
    }

    /// A standard normal number, by Box and Muller's transform, two at a time.
    pub fn normal(&mut self) -> f64 {
        if let Some(spare) = self.spare.take() {
            return spare;
        }
        let first = self.uniform().max(SMALLEST_DRAW);
        let second = self.uniform();
        let radius = (-TWICE * first.ln()).sqrt();
        let angle = TAU * second;
        self.spare = Some(radius * angle.sin());
        radius * angle.cos()
    }
}

/// The CRC-32 of some bytes, as zlib computes it, to seed a drum hit by what it is.
pub fn crc32(bytes: &[u8]) -> u32 {
    let mut crc = !0u32;
    for byte in bytes {
        crc ^= *byte as u32;
        for _ in 0..BITS_A_BYTE {
            let mask = (crc & 1).wrapping_neg();
            crc = (crc >> 1) ^ (CRC32_POLYNOMIAL & mask);
        }
    }
    !crc
}

#[cfg(test)]
mod tests {
    use super::*;

    use crate::dsp::testing::{sine, HALF_SECOND, RATE, SECOND};

    #[test]
    fn a_butterworth_low_pass_halves_the_power_at_its_cutoff() {
        let (cutoff, near) = (1000.0, 0.01);
        let mut section = Biquad::low_pass(cutoff, BUTTERWORTH_Q, RATE);
        let mut peak: f64 = 0.0;
        for place in 0..SECOND {
            let out = section.process(sine(cutoff, 1.0, place));
            if place > HALF_SECOND {
                peak = peak.max(out.abs());
            }
        }
        assert!((peak - std::f64::consts::FRAC_1_SQRT_2).abs() < near);
    }

    #[test]
    fn crc32_matches_zlib() {
        let (check_input, check_value): (&[u8], u32) = (b"123456789", 0xCBF4_3926);
        assert_eq!(crc32(check_input), check_value);
    }
}
