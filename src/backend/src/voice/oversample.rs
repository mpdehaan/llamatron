// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Twice the sample rate for a part whose curve or saturating loop makes harmonics above half the rate, so that they are
//! filtered away rather than folded back down as aliasing: each sample is made two by a halfband interpolator, the part
//! runs on both, and the two are made one again by a halfband decimator.
//!
//! The halfband is a polyphase pair of all-pass chains, each sample of the lower rate one pass through both: about 77 dB
//! down from just over half the lower rate, flat across the band, and only some four samples of delay, though its phase
//! is not linear, which no one hears in a filter's or a curve's output. Its coefficients are those of Laurent de Soras's
//! hiir library's design for eight coefficients and a transition of 0.04 of the rate (WTFPL); the implementation is our
//! own, after hiir's Upsampler2x and Downsampler2x.
//!
//! Where a part's output is a curve near full scale, such as Drive, whose jumps a phase that is not linear would push
//! higher, the linear-phase halfband keeps their shape, at twice the cost and more delay.

use std::f64::consts::PI;

/// The all-pass coefficients, the even ones for one chain and the odd ones for the other, from hiir's design by its
/// elliptic method for eight coefficients and a transition band of 0.04 of the rate.
const COEFFICIENTS: [f64; 8] = [
    0.040633460924,
    0.150505129023,
    0.300757055992,
    0.460774504961,
    0.609524314896,
    0.738503841119,
    0.849223810392,
    0.949742783705,
];

/// One direction's two all-pass chains: each stage's last input and output, in the coefficients' order.
#[derive(Clone, Copy, Debug, Default)]
struct Chains {
    inputs: [f64; 8],
    outputs: [f64; 8],
}

impl Chains {
    /// Two samples through the two chains, the first through the even coefficients and the second through the odd, each
    /// stage a first-order all-pass in the doubled rate's square.
    #[inline]
    fn run(&mut self, mut first: f64, mut second: f64) -> (f64, f64) {
        for stage in (0..COEFFICIENTS.len()).step_by(2) {
            let next_first = (first - self.outputs[stage]) * COEFFICIENTS[stage] + self.inputs[stage];
            let next_second = (second - self.outputs[stage + 1]) * COEFFICIENTS[stage + 1] + self.inputs[stage + 1];
            self.inputs[stage] = first;
            self.inputs[stage + 1] = second;
            self.outputs[stage] = crate::dsp::flushed(next_first);
            self.outputs[stage + 1] = crate::dsp::flushed(next_second);
            first = next_first;
            second = next_second;
        }
        (first, second)
    }
}

/// What one part's oversampling keeps: the interpolator's chains and the decimator's.
#[derive(Clone, Copy, Debug, Default)]
pub struct Halfband {
    up_chains: Chains,
    down_chains: Chains,
}

impl Halfband {
    /// A sample made two at twice the rate, in order of time.
    #[inline]
    pub fn up(&mut self, input: f64) -> (f64, f64) {
        self.up_chains.run(input, input)
    }

    /// Two samples at twice the rate, in order of time, made one at the rate: the later through one chain, the earlier
    /// through the other, averaged.
    #[inline]
    pub fn down(&mut self, first: f64, second: f64) -> f64 {
        let (later, earlier) = self.down_chains.run(second, first);
        0.5 * (later + earlier)
    }
}

/// The taps beside the centre on each side that are not zero, the odd ones: the filter is 4 * SIDE_TAPS - 1 long.
const SIDE_TAPS: usize = 12;
/// The Kaiser window's shape, which sets how far down the stopband is against how wide the transition.
const KAISER_BETA: f64 = 8.0;
/// The odd taps in order, nearest the centre first, for a halfband of unity gain: the centre is a half.
const CENTRE: f64 = 0.5;

/// The odd taps of the halfband, from the centre outward, each the windowed sinc at its distance.
fn odd_taps() -> [f64; SIDE_TAPS] {
    let half_length = (2 * SIDE_TAPS) as f64;
    std::array::from_fn(|place| {
        let distance = (2 * place + 1) as f64;
        let sinc = (PI * distance / 2.0).sin() / (PI * distance / 2.0);
        let x = distance / half_length;
        let window = bessel_i0(KAISER_BETA * (1.0 - x * x).max(0.0).sqrt()) / bessel_i0(KAISER_BETA);
        CENTRE * sinc * window
    })
}

/// The modified Bessel function of the first kind, order zero, by its series, for the Kaiser window.
fn bessel_i0(x: f64) -> f64 {
    let (mut sum, mut term, mut k) = (1.0, 1.0, 1.0);
    while term > 1e-12 * sum {
        term *= (x / (2.0 * k)).powi(2);
        sum += term;
        k += 1.0;
    }
    sum
}

/// Twice the taps' reach, the length of each ring of past samples: a sample is written twice, at its place and that
/// place a ring on, so that a run of taps is always read without wrapping.
const RING: usize = 2 * SIDE_TAPS;

/// The linear-phase halfband, a windowed sinc whose every other tap but the centre is zero, run as two phases: about
/// 80 dB down by a fifth of the rate and some twelve samples of delay, its phase linear so that a curve's jumps keep their
/// shape and peak no higher than a band-limited jump must. Textbook design, our own implementation.
///
/// What one part's linear-phase oversampling keeps: the taps, and the last inputs of the interpolator and the decimator, each in a
/// ring written twice over so that reading needs no wrapping.
#[derive(Clone, Copy, Debug)]
pub struct LinearHalfband {
    taps: [f64; SIDE_TAPS],
    /// The interpolator's last low-rate inputs.
    up: [f64; 2 * RING],
    /// The decimator's last high-rate samples of the phase between the centre's.
    down_odd: [f64; 2 * RING],
    /// The decimator's samples on the centre's phase, waiting the delay that lines them up with the rest.
    down_even: [f64; 2 * RING],
    /// Where the newest sample of each ring sits.
    place: usize,
}

impl Default for LinearHalfband {
    fn default() -> Self {
        LinearHalfband {
            taps: odd_taps(),
            up: [0.0; 2 * RING],
            down_odd: [0.0; 2 * RING],
            down_even: [0.0; 2 * RING],
            place: 0,
        }
    }
}

/// A sample written into a ring at a place, and a ring on, so that the ring reads straight from any place; flushed of a
/// value too small to matter as it goes in, so that a dying tail costs no denormal arithmetic.
#[inline]
fn written(ring: &mut [f64; 2 * RING], place: usize, value: f64) {
    let value = crate::dsp::flushed(value);
    ring[place] = value;
    ring[place + RING] = value;
}

impl LinearHalfband {
    /// The ring's sample an age back from the newest, 0 the newest.
    #[inline]
    fn back(&self, ring: &[f64; 2 * RING], age: usize) -> f64 {
        ring[self.place + RING - age]
    }

    /// The odd taps across a ring, each pair of samples around the centre: the samples nearest it first.
    #[inline]
    fn between(&self, ring: &[f64; 2 * RING]) -> f64 {
        let mut sum = 0.0;
        for (place, tap) in self.taps.iter().enumerate() {
            sum += tap * (self.back(ring, SIDE_TAPS - 1 - place) + self.back(ring, SIDE_TAPS + place));
        }
        sum
    }

    /// A sample made two at twice the rate: the first an input delayed to the centre, the second the taps between it and
    /// the input after it.
    #[inline]
    pub fn up(&mut self, input: f64) -> (f64, f64) {
        self.place = (self.place + 1) % RING;
        written(&mut self.up, self.place, input);
        // At twice the gain, so that the two samples carry the one's level.
        (self.back(&self.up, SIDE_TAPS), 2.0 * self.between(&self.up))
    }

    /// Two samples at twice the rate made one at the rate: the centre's phase halved, the other phase through the odd taps.
    #[inline]
    pub fn down(&mut self, first: f64, second: f64) -> f64 {
        written(&mut self.down_odd, self.place, second);
        written(&mut self.down_even, self.place, first);
        CENTRE * self.back(&self.down_even, SIDE_TAPS - 1) + self.between(&self.down_odd)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Up then down passes a low sine at its level, delayed, and a tone near the top of the band is kept out of the
    /// doubled rate's upper half.
    #[test]
    fn up_then_down_passes_a_low_sine_at_its_level() {
        let rate = 48_000.0;
        // The level by the settled stretch's RMS, since a sine of few samples a cycle rarely lands one on its peak.
        let level = |frequency: f64| {
            let mut halfband = Halfband::default();
            let samples = 9600;
            let mut power = 0.0;
            for place in 0..samples {
                let input = (2.0 * PI * frequency * place as f64 / rate).sin();
                let (first, second) = halfband.up(input);
                let out = halfband.down(first, second);
                if place >= samples / 2 {
                    power += out * out;
                }
            }
            (2.0 * power / (samples / 2) as f64).sqrt()
        };
        assert!((level(1_000.0) - 1.0).abs() < 0.01, "{}", level(1_000.0));
        assert!((level(8_000.0) - 1.0).abs() < 0.02, "{}", level(8_000.0));
        assert!((level(20_000.0) - 1.0).abs() < 0.02, "{}", level(20_000.0));
    }

    /// The interpolator's image of a tone, mirrored into the doubled rate's upper half, is far down.
    #[test]
    fn the_interpolators_image_is_far_down() {
        let rate = 48_000.0;
        let frequency = 3_000.0;
        let mut halfband = Halfband::default();
        let mut high = Vec::new();
        for place in 0..4800 {
            let (first, second) = halfband.up((2.0 * PI * frequency * place as f64 / rate).sin());
            high.push(first);
            high.push(second);
        }
        // The image sits at the rate less the tone, mirrored about the rate's half, measured over the settled stretch.
        let image = rate - frequency;
        let doubled = 2.0 * rate;
        let (mut real, mut imaginary, mut tone_real, mut tone_imaginary) = (0.0, 0.0, 0.0, 0.0);
        for (place, value) in high.iter().enumerate().skip(1000) {
            let t = place as f64 / doubled;
            real += value * (2.0 * PI * image * t).cos();
            imaginary += value * (2.0 * PI * image * t).sin();
            tone_real += value * (2.0 * PI * frequency * t).cos();
            tone_imaginary += value * (2.0 * PI * frequency * t).sin();
        }
        let below_db = 20.0 * ((real * real + imaginary * imaginary).sqrt() / (tone_real * tone_real + tone_imaginary * tone_imaginary).sqrt()).log10();
        assert!(below_db < -60.0, "{below_db}");
    }

    /// The linear-phase halfband passes a low sine through up and down at its level.
    #[test]
    fn the_linear_phase_halfband_passes_a_low_sine() {
        let rate = 48_000.0;
        let mut halfband = LinearHalfband::default();
        let samples = 9600;
        let mut power = 0.0;
        for place in 0..samples {
            let (first, second) = halfband.up((2.0 * PI * 1_000.0 * place as f64 / rate).sin());
            let out = halfband.down(first, second);
            if place >= samples / 2 {
                power += out * out;
            }
        }
        let level = (2.0 * power / (samples / 2) as f64).sqrt();
        assert!((level - 1.0).abs() < 0.01, "{level}");
    }
}
