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

use std::f64::consts::{PI, TAU};

/// The all-pass coefficients, the even ones for one chain and the odd ones for the other, from hiir's design by its
/// elliptic method for eight coefficients and a transition band of 0.04 of the rate.
/// How many all-pass coefficients there are, alternating between the two chains; the chains, two, as the oversampling
/// doubles the rate; and each ring written twice over.
const COEFFICIENT_COUNT: usize = 8;
const CHAINS: usize = 2;
const FACTOR: f64 = 2.0;
const COPIES: usize = 2;
/// Half, the average of two samples and a band's middle.
const HALF: f64 = 0.5;
/// How small a term of the Bessel series is, against its sum, before the series stops; and the power each term's
/// share is raised to.
const BESSEL_PRECISION: f64 = 1e-12;
const SQUARED: i32 = 2;

const COEFFICIENTS: [f64; COEFFICIENT_COUNT] = [
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
    inputs: [f64; COEFFICIENT_COUNT],
    outputs: [f64; COEFFICIENT_COUNT],
}

impl Chains {
    /// Two samples through the two chains, the first through the even coefficients and the second through the odd, each
    /// stage a first-order all-pass in the doubled rate's square.
    #[inline]
    fn run(&mut self, mut first: f64, mut second: f64) -> (f64, f64) {
        for stage in (0..COEFFICIENTS.len()).step_by(CHAINS) {
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
        HALF * (later + earlier)
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
    let half_length = (CHAINS * SIDE_TAPS) as f64;
    std::array::from_fn(|place| {
        let distance = (CHAINS * place + 1) as f64;
        let sinc = (PI * distance / FACTOR).sin() / (PI * distance / FACTOR);
        let x = distance / half_length;
        let window = bessel_i0(KAISER_BETA * (1.0 - x * x).max(0.0).sqrt()) / bessel_i0(KAISER_BETA);
        CENTRE * sinc * window
    })
}

/// The modified Bessel function of the first kind, order zero, by its series, for the Kaiser window.
fn bessel_i0(x: f64) -> f64 {
    let (mut sum, mut term, mut k) = (1.0, 1.0, 1.0);
    while term > BESSEL_PRECISION * sum {
        term *= (x / (FACTOR * k)).powi(SQUARED);
        sum += term;
        k += 1.0;
    }
    sum
}

/// Twice the taps' reach, the length of each ring of past samples: a sample is written twice, at its place and that
/// place a ring on, so that a run of taps is always read without wrapping.
const RING: usize = CHAINS * SIDE_TAPS;

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
    up: [f64; COPIES * RING],
    /// The decimator's last high-rate samples of the phase between the centre's.
    down_odd: [f64; COPIES * RING],
    /// The decimator's samples on the centre's phase, waiting the delay that lines them up with the rest.
    down_even: [f64; COPIES * RING],
    /// Where the newest sample of each ring sits.
    place: usize,
}

impl Default for LinearHalfband {
    fn default() -> Self {
        LinearHalfband {
            taps: odd_taps(),
            up: [0.0; COPIES * RING],
            down_odd: [0.0; COPIES * RING],
            down_even: [0.0; COPIES * RING],
            place: 0,
        }
    }
}

/// A sample written into a ring at a place, and a ring on, so that the ring reads straight from any place; flushed of a
/// value too small to matter as it goes in, so that a dying tail costs no denormal arithmetic.
#[inline]
fn written(ring: &mut [f64; COPIES * RING], place: usize, value: f64) {
    let value = crate::dsp::flushed(value);
    ring[place] = value;
    ring[place + RING] = value;
}

impl LinearHalfband {
    /// The ring's sample an age back from the newest, 0 the newest.
    #[inline]
    fn back(&self, ring: &[f64; COPIES * RING], age: usize) -> f64 {
        ring[self.place + RING - age]
    }

    /// The odd taps across a ring, each pair of samples around the centre: the samples nearest it first.
    #[inline]
    fn between(&self, ring: &[f64; COPIES * RING]) -> f64 {
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
        (self.back(&self.up, SIDE_TAPS), FACTOR * self.between(&self.up))
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
    use crate::dsp::testing::{decibels, sine, RATE, TENTH_SECOND};

    /// What both halfbands do: make a sample two at twice the rate, and two one again.
    trait Doubling: Default {
        fn up(&mut self, input: f64) -> (f64, f64);
        fn down(&mut self, first: f64, second: f64) -> f64;
    }

    impl Doubling for Halfband {
        fn up(&mut self, input: f64) -> (f64, f64) {
            Halfband::up(self, input)
        }
        fn down(&mut self, first: f64, second: f64) -> f64 {
            Halfband::down(self, first, second)
        }
    }

    impl Doubling for LinearHalfband {
        fn up(&mut self, input: f64) -> (f64, f64) {
            LinearHalfband::up(self, input)
        }
        fn down(&mut self, first: f64, second: f64) -> f64 {
            LinearHalfband::down(self, first, second)
        }
    }

    /// A sine's level through a halfband up and down, by the settled stretch's RMS, since a sine of few samples a cycle
    /// rarely lands one on its peak.
    fn level_through<Doubler: Doubling>(frequency: f64) -> f64 {
        let mut halfband = Doubler::default();
        let (samples, settled) = (TENTH_SECOND + TENTH_SECOND, TENTH_SECOND);
        let mut power = 0.0;
        for place in 0..samples {
            let (first, second) = halfband.up(sine(frequency, 1.0, place));
            let out = halfband.down(first, second);
            if place >= settled {
                power += out * out;
            }
        }
        // A sine's mean square is half its peak's square.
        (FACTOR * power / settled as f64).sqrt()
    }

    /// Both halfbands pass a sine up and down at its level: the all-pass one to near the top of the band, the
    /// linear-phase one across the low and middle band.
    #[test]
    fn every_halfband_passes_a_sine_at_its_level() {
        let (low, middle, top, nearest, near_enough) = (1_000.0, 8_000.0, 20_000.0, 0.01, 0.02);
        for (frequency, near) in [(low, nearest), (middle, near_enough), (top, near_enough)] {
            let level = level_through::<Halfband>(frequency);
            assert!((level - 1.0).abs() < near, "all-pass at {frequency}: {level}");
        }
        for (frequency, near) in [(low, nearest), (middle, near_enough)] {
            let level = level_through::<LinearHalfband>(frequency);
            assert!((level - 1.0).abs() < near, "linear-phase at {frequency}: {level}");
        }
    }

    /// The interpolator's image of a tone, mirrored into the doubled rate's upper half, is far down.
    #[test]
    fn the_interpolators_image_is_far_down() {
        let frequency = 3_000.0;
        let mut halfband = Halfband::default();
        let mut high = Vec::new();
        for place in 0..TENTH_SECOND {
            let (first, second) = halfband.up(sine(frequency, 1.0, place));
            high.push(first);
            high.push(second);
        }
        // The image sits at the rate less the tone, mirrored about the rate's half, measured over the settled stretch.
        let image = RATE - frequency;
        let doubled = FACTOR * RATE;
        let (settling, far_down) = (1000, -60.0);
        let (mut real, mut imaginary, mut tone_real, mut tone_imaginary) = (0.0, 0.0, 0.0, 0.0);
        for (place, value) in high.iter().enumerate().skip(settling) {
            let t = place as f64 / doubled;
            real += value * (TAU * image * t).cos();
            imaginary += value * (TAU * image * t).sin();
            tone_real += value * (TAU * frequency * t).cos();
            tone_imaginary += value * (TAU * frequency * t).sin();
        }
        let below_db = decibels((real * real + imaginary * imaginary).sqrt() / (tone_real * tone_real + tone_imaginary * tone_imaginary).sqrt());
        assert!(below_db < far_down, "{below_db}");
    }
}

/// The steep decimator's length, odd so that its centre falls on a sample; where its pass band ends and its stop band
/// begins, as shares of the doubled rate; and its window's shape, some 80 dB down.
const STEEP_TAPS: usize = 121;
const STEEP_PASS_SHARE: f64 = 20.0 / 96.0;
const STEEP_STOP_SHARE: f64 = 24.0 / 96.0;
const STEEP_KAISER_BETA: f64 = 7.9;

/// The steep decimator's taps: a windowed sinc cut midway between its pass and stop bands, scaled to unity gain.
fn steep_taps() -> [f64; STEEP_TAPS] {
    let cut = (STEEP_PASS_SHARE + STEEP_STOP_SHARE) / FACTOR;
    let middle = (STEEP_TAPS / CHAINS) as f64;
    let mut taps: [f64; STEEP_TAPS] = std::array::from_fn(|place| {
        let distance = place as f64 - middle;
        let sinc = if distance == 0.0 {
            FACTOR * cut
        } else {
            (TAU * cut * distance).sin() / (PI * distance)
        };
        let x = distance / middle;
        sinc * bessel_i0(STEEP_KAISER_BETA * (1.0 - x * x).max(0.0).sqrt()) / bessel_i0(STEEP_KAISER_BETA)
    });
    let sum: f64 = taps.iter().sum();
    for tap in taps.iter_mut() {
        *tap /= sum;
    }
    taps
}

/// Two samples at twice the rate made one by a linear-phase low pass whose stop band begins at the lower rate's half,
/// rather than straddling it as a halfband's does, so that nothing above that half folds back down into the top octave.
/// It is longer than a halfband and every tap counts, so it is kept for the last step down of a curve that makes strong
/// harmonics up there, such as Drive's. Textbook Kaiser-window design, our own implementation.
#[derive(Clone, Copy, Debug)]
pub struct SteepDecimator {
    taps: [f64; STEEP_TAPS],
    /// The last samples at the doubled rate, written twice over so that reading needs no wrapping.
    ring: [f64; COPIES * STEEP_TAPS],
    /// Where the newest sample sits.
    place: usize,
}

impl Default for SteepDecimator {
    fn default() -> Self {
        SteepDecimator {
            taps: steep_taps(),
            ring: [0.0; COPIES * STEEP_TAPS],
            place: 0,
        }
    }
}

impl SteepDecimator {
    /// A sample at the doubled rate kept, flushed of a value too small to matter.
    #[inline]
    fn push(&mut self, value: f64) {
        self.place = (self.place + 1) % STEEP_TAPS;
        let value = crate::dsp::flushed(value);
        self.ring[self.place] = value;
        self.ring[self.place + STEEP_TAPS] = value;
    }

    /// Two samples at twice the rate, in order of time, made one at the rate.
    #[inline]
    pub fn down(&mut self, first: f64, second: f64) -> f64 {
        self.push(first);
        self.push(second);
        // The newest sample sits at place + STEEP_TAPS, so the window of the last STEEP_TAPS reads straight from place + 1.
        let window = &self.ring[self.place + 1..self.place + 1 + STEEP_TAPS];
        window.iter().zip(self.taps.iter()).map(|(sample, tap)| sample * tap).sum()
    }
}
