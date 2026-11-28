// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Drive: the mix shaped by a curve. Soft and Warm saturate, Warm leaning to one side for even harmonics; Hard clips;
//! Fold folds back past full scale and Wrap wraps round, the harsh digital sounds of cheap grooveboxes.
//!
//! A curve pushed hard makes harmonics far above half the sample rate, which would fold back down as tones unrelated to
//! the note. Two things keep them out: the curve runs at twice the rate, Fold and Wrap at eight times, since their
//! folds make harmonics far higher than a saturator's, between a linear-phase halfband interpolator and decimator, whose even phase
//! keeps a jump's peak where a band-limited jump's must be,
//! and at that rate each sample is the curve's average over the sample's span rather than its value at one instant,
//! worked out from the curve's antiderivative. Mix blends the shaped sound with the sound at twice the rate, before the
//! two come down together, so that the two line up.
//!
//! Each curve's level is matched: a sine at the reference level comes out as loud as it went in, at every Amount, so
//! that turning Drive up changes the tone rather than the loudness. Amount 0 leaves the sound untouched, and Warm's lean,
//! which makes a steady offset along with its even harmonics, is followed by a DC blocker.

use crate::dsp::oversample::{LinearHalfband, SteepDecimator};
use crate::dsp::saturation::{log_cosh, CLOSEST_INPUTS};
use std::f64::consts::PI;

const MOST_GAIN: f64 = 20.0;
const MOST_FOLDING_GAIN: f64 = 4.0;
const WARM_LEAN: f64 = 0.3;

/// The level a sine keeps through every curve at every Amount, its peak 6 dB under full scale; the points of a cycle
/// its loudness is measured over; and the most and least the matching may scale by.
const REFERENCE_LEVEL: f64 = 0.5;
const LEVEL_POINTS: usize = 256;
const MOST_LEVEL: f64 = 4.0;
const LEAST_LEVEL: f64 = 0.25;
/// How many times the rate Fold and Wrap run at, as three halfbands in a row, and the others at, as one.
const FOLDING_STAGES: usize = 3;
const SATURATING_STAGES: usize = 1;
/// The DC blocker's pole after Warm, its corner near 5 Hz at 48 kHz.
const DC_POLE: f64 = 0.9993;

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

/// Drive: its curve, how hard it pushes, the scale and offset that keep the curve at full scale and silence silent, the
/// oversampling's halfband, and the last driven input at twice the rate.
pub struct Drive {
    curve: Curve,
    gain: f64,
    scale: f64,
    offset: f64,
    /// What the shaped sound is scaled by so that a sine at the reference level keeps its loudness.
    level: f64,
    /// Whether Amount is 0, when the sound passes untouched.
    bypassed: bool,
    /// The halfbands, each doubling the rate, and how many are used.
    halfbands: [LinearHalfband; FOLDING_STAGES],
    stages: usize,
    /// The last step down to the rate, steeper than a halfband, so that nothing above half the rate folds back.
    last_step_down: Box<SteepDecimator>,
    previous: f64,
    /// The DC blocker's last input and output, used after Warm.
    blocked_in: f64,
    blocked_out: f64,
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
        let stages = if matches!(curve, Curve::Fold | Curve::Wrap) {
            FOLDING_STAGES
        } else {
            SATURATING_STAGES
        };
        let mut drive = Drive {
            curve,
            gain,
            scale,
            offset,
            level: 1.0,
            bypassed: amount <= 0.0,
            halfbands: [LinearHalfband::default(); FOLDING_STAGES],
            stages,
            last_step_down: Box::default(),
            previous: 0.0,
            blocked_in: 0.0,
            blocked_out: 0.0,
        };
        drive.level = drive.matched_level();
        drive
    }

    /// What the shaped sound is scaled by so that a sine at the reference level comes out as loud as it went in: the
    /// sine's loudness over the shaped sine's, across one cycle, held between the least and the most.
    fn matched_level(&self) -> f64 {
        let (mut sine_power, mut shaped_power) = (0.0, 0.0);
        for point in 0..LEVEL_POINTS {
            let sine = REFERENCE_LEVEL * (2.0 * PI * point as f64 / LEVEL_POINTS as f64).sin();
            sine_power += sine * sine;
            shaped_power += self.shaped(sine * self.gain).powi(2);
        }
        if shaped_power <= 0.0 {
            return 1.0;
        }
        (sine_power / shaped_power).sqrt().clamp(LEAST_LEVEL, MOST_LEVEL)
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
        if self.bypassed {
            return dry;
        }
        let out = self.oversampled(0, dry, mix);
        if self.curve == Curve::Warm {
            return self.without_dc(out);
        }
        out
    }

    /// A sample shaped at the rate the halfbands from this one on give: made two by this halfband, each made more by the
    /// next or shaped and blended at the last, then brought back down by this halfband.
    // Recursion over at most three stages keeps one path for the 2x and the 8x curves; it is inlined into a fixed chain.
    #[inline]
    fn oversampled(&mut self, stage: usize, dry: f64, mix: f64) -> f64 {
        let (first, second) = self.halfbands[stage].up(dry);
        let (first, second) = if stage + 1 < self.stages {
            (self.oversampled(stage + 1, first, mix), self.oversampled(stage + 1, second, mix))
        } else {
            (self.blended(first, mix), self.blended(second, mix))
        };
        if stage == 0 {
            return self.last_step_down.down(first, second);
        }
        self.halfbands[stage].down(first, second)
    }

    /// A sample at the top rate shaped, its level matched, and blended with itself by Mix.
    #[inline]
    fn blended(&mut self, dry: f64, mix: f64) -> f64 {
        let wet = self.averaged(dry) * self.level;
        dry + (wet - dry) * mix
    }

    /// A sample with its steady offset taken away by a one-pole DC blocker.
    #[inline]
    fn without_dc(&mut self, input: f64) -> f64 {
        let out = input - self.blocked_in + DC_POLE * self.blocked_out;
        self.blocked_in = input;
        self.blocked_out = crate::dsp::flushed(out);
        self.blocked_out
    }

    /// Back to rest: the halfbands, the last input and the DC blocker silent.
    pub fn reset(&mut self) {
        self.halfbands = [LinearHalfband::default(); FOLDING_STAGES];
        *self.last_step_down = SteepDecimator::default();
        self.previous = 0.0;
        self.blocked_in = 0.0;
        self.blocked_out = 0.0;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::dsp::spectrum::stray_decibels_under;

    const RATE: usize = 48_000;
    const CURVES: [Curve; 5] = [Curve::Soft, Curve::Warm, Curve::Hard, Curve::Fold, Curve::Wrap];

    /// Two seconds of a loud sine at a whole number of hertz.
    fn sine(hertz: usize, amplitude: f64) -> Vec<f64> {
        (0..2 * RATE)
            .map(|place| amplitude * (2.0 * PI * hertz as f64 * place as f64 / RATE as f64).sin())
            .collect()
    }

    fn driven(curve: Curve, input: &[f64]) -> Vec<f32> {
        let mut drive = Drive::new(curve, 1.0);
        input.iter().map(|sample| drive.process(*sample, 1.0) as f32).collect()
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

    /// Every curve pushed hard on a high note stays clean where it is heard: on a 5 kHz note at full Amount, its stray
    /// tones under 18 kHz lie 40 dB under its harmonics.
    #[test]
    fn every_curve_on_a_high_note_stays_clean_where_it_is_heard() {
        let hertz = 5_003;
        let heard_under = 18_000;
        let input = sine(hertz, 0.8);
        for curve in CURVES {
            let stray = stray_decibels_under(&driven(curve, &input), RATE, hertz, heard_under);
            assert!(stray < -40.0, "curve {:?}: {stray:.1} dB", curve as u8);
        }
    }

    /// The loudness of a second of sound, as the root of its mean square.
    fn loudness(samples: &[f32]) -> f64 {
        (samples.iter().map(|sample| (*sample as f64).powi(2)).sum::<f64>() / samples.len() as f64).sqrt()
    }

    /// Every curve at every Amount keeps a sine at the reference level as loud as it went in, within a decibel, so that
    /// turning Drive up changes the tone rather than the loudness.
    #[test]
    fn every_curve_keeps_the_reference_level() {
        let hertz = 220;
        let input = sine(hertz, REFERENCE_LEVEL);
        let kept = loudness(&input.iter().map(|sample| *sample as f32).collect::<Vec<f32>>());
        for curve in CURVES {
            for amount in [0.1, 0.5, 1.0] {
                let mut drive = Drive::new(curve, amount);
                let out: Vec<f32> = input.iter().map(|sample| drive.process(*sample, 1.0) as f32).collect();
                let decibels = 20.0 * (loudness(&out[RATE..]) / kept).log10();
                assert!(decibels.abs() < 1.0, "curve {:?} at {amount}: {decibels:.2} dB", curve as u8);
            }
        }
    }

    /// At Amount 0 Drive leaves the sound untouched, whatever its curve.
    #[test]
    fn amount_zero_leaves_the_sound_alone() {
        let input = sine(220, 0.9);
        for curve in CURVES {
            let mut drive = Drive::new(curve, 0.0);
            assert!(input.iter().all(|sample| drive.process(*sample, 1.0) == *sample), "curve {:?}", curve as u8);
        }
    }

    /// Warm's lean makes even harmonics but leaves no steady offset: a loud sine through it averages to nothing.
    #[test]
    fn warm_leaves_no_offset() {
        let input = sine(220, 0.9);
        let mut drive = Drive::new(Curve::Warm, 1.0);
        let out: Vec<f64> = input.iter().map(|sample| drive.process(*sample, 1.0)).collect();
        let late = &out[RATE..];
        let offset = late.iter().sum::<f64>() / late.len() as f64;
        assert!(offset.abs() < 1e-3, "{offset}");
    }
}
