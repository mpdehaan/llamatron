// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Drive: the mix shaped by a curve. Soft and Warm saturate, Warm leaning to one side for even harmonics; Hard clips;
//! Fold folds back past full scale and Wrap wraps round, the harsh digital sounds of cheap grooveboxes.
//!
//! A curve pushed hard makes harmonics far above half the sample rate, which would fold back down as tones unrelated to
//! the note. Two things keep them out: the curve runs at twice the rate, between a linear-phase halfband interpolator and decimator, whose even phase
//! keeps a jump's peak where a band-limited jump's must be,
//! and at that rate each sample is the curve's average over the sample's span rather than its value at one instant,
//! worked out from the curve's antiderivative. Mix blends the shaped sound with the sound at twice the rate, before the
//! two come down together, so that the two line up.

use crate::voice::oversample::LinearHalfband;
use std::f64::consts::PI;

const MOST_GAIN: f64 = 20.0;
const MOST_FOLDING_GAIN: f64 = 4.0;
const WARM_LEAN: f64 = 0.3;
/// Two inputs closer than this are one: the antiderivative's difference over them would lose its precision, so the
/// curve is read at their middle instead.
const CLOSEST_INPUTS: f64 = 1e-6;

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Curve {
    Soft,
    Warm,
    Hard,
    Fold,
    Wrap,
}

impl Curve {
    /// The curve named, Soft for any other name.
    pub fn named(name: &str) -> Curve {
        match name {
            "warm" => Curve::Warm,
            "hard" => Curve::Hard,
            "fold" => Curve::Fold,
            "wrap" => Curve::Wrap,
            _ => Curve::Soft,
        }
    }
}

/// The log of the hyperbolic cosine, the antiderivative of tanh, written so that it never overflows.
#[inline]
fn log_cosh(x: f64) -> f64 {
    let size = x.abs();
    size + (-2.0 * size).exp().ln_1p() - std::f64::consts::LN_2
}

/// Drive: its curve, how hard it pushes, the scale and offset that keep the curve at full scale and silence silent, the
/// oversampling's halfband, and the last driven input at twice the rate.
pub struct Drive {
    curve: Curve,
    gain: f64,
    scale: f64,
    offset: f64,
    halfband: LinearHalfband,
    previous: f64,
}

impl Drive {
    /// Drive by a curve at an amount from 0 to 1.
    pub fn new(curve: Curve, amount: f64) -> Drive {
        let most = if matches!(curve, Curve::Fold | Curve::Wrap) {
            MOST_FOLDING_GAIN
        } else {
            MOST_GAIN
        };
        let gain = 1.0 + amount * most;
        let mut offset = 0.0;
        let mut scale = 1.0 / gain.tanh();
        if curve == Curve::Warm {
            // Leaning before the curve and taking the lean's own level away again leaves silence silent; the scale is the
            // larger of the two extremes, so that the curve reaches full scale on one side and stays under it on the other.
            offset = WARM_LEAN.tanh();
            scale = 1.0 / ((gain + WARM_LEAN).tanh() - offset).max(offset - (WARM_LEAN - gain).tanh());
        }
        Drive {
            curve,
            gain,
            scale,
            offset,
            halfband: LinearHalfband::default(),
            previous: 0.0,
        }
    }

    /// The curve at a driven input.
    #[inline]
    fn shaped(&self, driven: f64) -> f64 {
        match self.curve {
            Curve::Soft => driven.tanh() * self.scale,
            Curve::Warm => ((driven + WARM_LEAN).tanh() - self.offset) * self.scale,
            Curve::Hard => driven.clamp(-1.0, 1.0),
            Curve::Fold => (driven * PI / 2.0).sin(),
            Curve::Wrap => (driven + 1.0).rem_euclid(2.0) - 1.0,
        }
    }

    /// The curve's antiderivative at a driven input, each continuous, so that its difference over a span is the curve's
    /// area there.
    #[inline]
    fn antiderivative(&self, driven: f64) -> f64 {
        match self.curve {
            Curve::Soft => log_cosh(driven) * self.scale,
            Curve::Warm => (log_cosh(driven + WARM_LEAN) - self.offset * driven) * self.scale,
            Curve::Hard if driven.abs() <= 1.0 => driven * driven / 2.0,
            Curve::Hard => driven.abs() - 0.5,
            Curve::Fold => -(driven * PI / 2.0).cos() * 2.0 / PI,
            // Each cycle of the wrap adds nothing to the area, so only the place in the cycle counts.
            Curve::Wrap => {
                let place = (driven + 1.0).rem_euclid(2.0);
                place * place / 2.0 - place
            }
        }
    }

    // Antiderivative anti-aliasing after Parker, Zavalishin and Le Bivic, "Reducing the aliasing of nonlinear
    // waveshaping using continuous-time convolution" (DAFx 2016), and Bilbao, Esqueda, Parker and Välimäki,
    // "Antiderivative antialiasing for memoryless nonlinearities" (IEEE SPL 2017); our own implementation.
    /// The curve's average over the span from the last driven input to this one.
    #[inline]
    fn averaged(&mut self, input: f64) -> f64 {
        let driven = input * self.gain;
        let span = driven - self.previous;
        let out = if span.abs() < CLOSEST_INPUTS {
            self.shaped((driven + self.previous) / 2.0)
        } else {
            (self.antiderivative(driven) - self.antiderivative(self.previous)) / span
        };
        self.previous = driven;
        out
    }

    /// One sample shaped and blended with the sound by a Mix from 0 to 1.
    #[inline]
    pub fn process(&mut self, dry: f64, mix: f64) -> f64 {
        let (first, second) = self.halfband.up(dry);
        let first_wet = self.averaged(first);
        let second_wet = self.averaged(second);
        let blend = |dry: f64, wet: f64| dry + (wet - dry) * mix;
        self.halfband.down(blend(first, first_wet), blend(second, second_wet))
    }

    /// Back to rest: the halfband and the last input silent.
    pub fn reset(&mut self) {
        self.halfband = LinearHalfband::default();
        self.previous = 0.0;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::dsp::spectrum::stray_decibels;

    const RATE: usize = 48_000;
    const CURVES: [Curve; 5] = [Curve::Soft, Curve::Warm, Curve::Hard, Curve::Fold, Curve::Wrap];

    /// Two seconds of a loud sine at a whole number of hertz.
    fn sine(hertz: usize, amplitude: f64) -> Vec<f64> {
        (0..2 * RATE)
            .map(|place| amplitude * (2.0 * PI * hertz as f64 * place as f64 / RATE as f64).sin())
            .collect()
    }

    /// The same curve read at each sample's instant, as Drive was before it was anti-aliased.
    fn naive(curve: Curve, input: &[f64]) -> Vec<f32> {
        let drive = Drive::new(curve, 1.0);
        input.iter().map(|sample| drive.shaped(sample * drive.gain) as f32).collect()
    }

    fn driven(curve: Curve, input: &[f64]) -> Vec<f32> {
        let mut drive = Drive::new(curve, 1.0);
        input.iter().map(|sample| drive.process(*sample, 1.0) as f32).collect()
    }

    /// At full Amount on a high note, every curve's stray tones, the aliasing folded back between its harmonics, fall
    /// well under what the bare curve makes.
    #[test]
    fn every_curve_pushed_hard_on_a_high_note_folds_far_less_back() {
        let hertz = 2_999;
        let input = sine(hertz, 0.8);
        let least_gain = 15.0;
        for curve in CURVES {
            let before = stray_decibels(&naive(curve, &input), RATE, hertz);
            let after = stray_decibels(&driven(curve, &input), RATE, hertz);
            assert!(after < before - least_gain, "curve {:?}: {after:.1} dB against {before:.1} dB", curve as u8);
        }
    }

    /// Each antiderivative's slope is its curve: the difference over a small span is the curve at its middle.
    #[test]
    fn each_antiderivative_rises_by_its_curve() {
        let span = 1e-4;
        for curve in CURVES {
            let drive = Drive::new(curve, 0.5);
            for place in -40..=40 {
                let x = place as f64 * 0.137;
                let slope = (drive.antiderivative(x + span) - drive.antiderivative(x - span)) / (2.0 * span);
                assert!((slope - drive.shaped(x)).abs() < 1e-3, "curve {:?} at {x}: {slope}", curve as u8);
            }
        }
    }

    /// At no Mix the sound comes through whole, delayed only by the halfband, and silence stays silent at any Mix.
    #[test]
    fn no_mix_passes_the_sound_and_silence_stays_silent() {
        let mut drive = Drive::new(Curve::Hard, 1.0);
        let input = sine(200, 0.5);
        let out: Vec<f64> = input.iter().map(|sample| drive.process(*sample, 0.0)).collect();
        let loudest = out[RATE..].iter().fold(0.0f64, |most, sample| most.max(sample.abs()));
        assert!((loudest - 0.5).abs() < 0.01, "{loudest}");
        for curve in CURVES {
            let mut drive = Drive::new(curve, 1.0);
            let quiet = (0..RATE).map(|_| drive.process(0.0, 1.0)).fold(0.0f64, |most, sample| most.max(sample.abs()));
            assert!(quiet < 1e-9, "curve {:?}: {quiet}", curve as u8);
        }
    }
}
