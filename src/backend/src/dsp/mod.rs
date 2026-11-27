// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Small pieces of signal processing every part shares: a biquad section and its designs (Butterworth low and high
//! passes, a band pass by centre and Q), and a seeded random source, so that a drum hit renders the same every time.

#[cfg(test)]
pub mod spectrum;

use std::f64::consts::PI;

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
    fn normalized(b: [f64; 3], a: [f64; 3]) -> Biquad {
        Biquad {
            b0: b[0] / a[0],
            b1: b[1] / a[0],
            b2: b[2] / a[0],
            a1: a[1] / a[0],
            a2: a[2] / a[0],
            s1: 0.0,
            s2: 0.0,
        }
    }

    /// A low pass at a cutoff and Q, by the bilinear transform with its cutoff prewarped; Q of 1/√2 is Butterworth.
    pub fn low_pass(cutoff: f64, quality: f64, rate: f64) -> Biquad {
        let (cosine, alpha) = angle(cutoff, quality, rate);
        Biquad::normalized(
            [(1.0 - cosine) / 2.0, 1.0 - cosine, (1.0 - cosine) / 2.0],
            [1.0 + alpha, -2.0 * cosine, 1.0 - alpha],
        )
    }

    /// A high pass at a cutoff and Q.
    pub fn high_pass(cutoff: f64, quality: f64, rate: f64) -> Biquad {
        let (cosine, alpha) = angle(cutoff, quality, rate);
        Biquad::normalized(
            [(1.0 + cosine) / 2.0, -(1.0 + cosine), (1.0 + cosine) / 2.0],
            [1.0 + alpha, -2.0 * cosine, 1.0 - alpha],
        )
    }

    /// A band pass of unit gain at its centre, its width the centre over its Q.
    pub fn band_pass(centre: f64, quality: f64, rate: f64) -> Biquad {
        let (cosine, alpha) = angle(centre, quality, rate);
        Biquad::normalized([alpha, 0.0, -alpha], [1.0 + alpha, -2.0 * cosine, 1.0 - alpha])
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

fn angle(frequency: f64, quality: f64, rate: f64) -> (f64, f64) {
    let frequency = frequency.clamp(1.0, HIGHEST_SHARE * rate);
    let w = 2.0 * PI * frequency / rate;
    (w.cos(), w.sin() / (2.0 * quality))
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

/// A band pass as the drum recipes ask for it: two sections of a centre and Q, steeper than one, as a fourth-order band
/// pass is.
pub fn band_pass_pair(centre: f64, quality: f64, rate: f64) -> [Biquad; 2] {
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
        self.state = self.state.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut value = self.state;
        value = (value ^ (value >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        value = (value ^ (value >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        value ^ (value >> 31)
    }

    /// A uniform number from 0 up to 1.
    pub fn uniform(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 / (1u64 << 53) as f64
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
        let first = self.uniform().max(1e-300);
        let second = self.uniform();
        let radius = (-2.0 * first.ln()).sqrt();
        let angle = 2.0 * PI * second;
        self.spare = Some(radius * angle.sin());
        radius * angle.cos()
    }
}

/// The CRC-32 of some bytes, as zlib computes it, to seed a drum hit by what it is.
pub fn crc32(bytes: &[u8]) -> u32 {
    let mut crc = !0u32;
    for byte in bytes {
        crc ^= *byte as u32;
        for _ in 0..8 {
            let mask = (crc & 1).wrapping_neg();
            crc = (crc >> 1) ^ (0xEDB8_8320 & mask);
        }
    }
    !crc
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_butterworth_low_pass_halves_the_power_at_its_cutoff() {
        let rate = 48000.0;
        let mut section = Biquad::low_pass(1000.0, BUTTERWORTH_Q, rate);
        let mut peak: f64 = 0.0;
        for place in 0..48000 {
            let out = section.process((2.0 * PI * 1000.0 * place as f64 / rate).sin());
            if place > 24000 {
                peak = peak.max(out.abs());
            }
        }
        assert!((peak - std::f64::consts::FRAC_1_SQRT_2).abs() < 0.01);
    }

    #[test]
    fn crc32_matches_zlib() {
        assert_eq!(crc32(b"123456789"), 0xCBF4_3926);
    }
}
