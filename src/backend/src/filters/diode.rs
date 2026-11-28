// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Diode filter, the acid bass's own circuit, after Open303 by Robin Schmidt; Oh3's oscillator, which feeds it, is in
//! `oscillators/acid.rs`.
//!
//! Open303 (Copyright (c) 2009 Robin Schmidt, www.rs-met.com, released under the MIT license, which is compatible with
//! this program's GPL) is an open emulation of the acid bass machine, its constants measured from the circuit. This module
//! follows its work: the filter, four one-pole stages in a ladder with a
//! high-pass inside its feedback loop, which thins the bass as the resonance rises and keeps the peak singing rather than
//! booming, with Open303's fitted coefficients and its skew of the resonance; the filter run at four times the sample rate;
//! the all-pass, high-pass and notch after the filter that the circuit's coupling makes; and the measured mapping of the
//! cutoff and the Env amount to the envelope's sweep. Where this differs: the decimation after the oversampled filter is
//! two Butterworth sections rather than Open303's elliptic filter, and the oscillator runs at the sample rate, its tables
//! already band-limited.

use crate::dsp::one_pole::{OnePoleAllpass, OnePoleHighpass};
use crate::dsp::saturation::SmoothTanh;
use crate::dsp::{flushed, Biquad, BUTTERWORTH_Q, HIGHEST_SHARE, OCTAVE};
use std::f64::consts::TAU;

/// How many times the sample rate the filter runs at.
pub const OVERSAMPLING: usize = 4;
/// The ladder's four stages, its last stage's place, and the decimation's two sections.
const STAGES: usize = 4;
const LAST_STAGE: usize = STAGES - 1;
const DECIMATION_SECTIONS: usize = 2;
/// Twice, as the first stage and the stages' own taps weigh in the ladder's step, the output is lifted, and a biquad's
/// cosine is doubled; and half, as Open303's notch halves its width's angle.
const TWICE: f64 = 2.0;
const HALF: f64 = 0.5;
/// Open303's fit of the stages' gain to the cutoff, (c0 + c1 fx) / (1 + c2 fx + c3 fx²), and of the loop's gain at full
/// resonance, a polynomial of the sixth degree whose leading coefficient is one, the rest from the top down; and the
/// gain it is divided by to give the output's makeup.
const STAGE_GAIN_FIT: [f64; 4] = [0.00045522346, 6.1922189, 12.358354, 4.4156345];
const LOOP_GAIN_FIT: [f64; 6] = [7198.6997, 5837.7917, 476.47308, 614.95611, 213.87126, 16.998792];
const LOOP_GAIN_DIVISOR: f64 = 17.0;
/// The high-pass inside the filter's feedback loop, the filter's lowest and highest cutoff, and its resonance skew.
const FEEDBACK_HIGHPASS_HZ: f64 = 150.0;
const LOWEST_CUTOFF_HZ: f64 = 200.0;
const HIGHEST_CUTOFF_HZ: f64 = 20000.0;
const RESONANCE_SKEW: f64 = 3.0;
/// The filters after the main one: an all-pass, a high-pass and a band-reject, with the band-reject's width in octaves.
const AFTER_ALLPASS_HZ: f64 = 14.008;
const AFTER_HIGHPASS_HZ: f64 = 24.167;
const AFTER_NOTCH_HZ: f64 = 7.5164;
const AFTER_NOTCH_OCTAVES: f64 = 4.7;
/// The decimation after the oversampled filter cuts above this share of the sample rate.
const DECIMATION_SHARE: f64 = 0.4;
/// The measured mapping of the cutoff and the Env amount: the lowest and highest nominal cutoffs, and the lines the
/// envelope's scale and offset follow.
const LOWEST_NOMINAL_HZ: f64 = 313.8152786059267;
const HIGHEST_NOMINAL_HZ: f64 = 2394.411986817546;
const OFFSET_FACTOR: f64 = 0.048292930943553;
const OFFSET_CONSTANT: f64 = 0.294391201442418;
const SCALE_LOW_FACTOR: f64 = 3.773996325111173;
const SCALE_LOW_CONSTANT: f64 = 0.736965594166206;
const SCALE_HIGH_FACTOR: f64 = 4.194548788411135;
const SCALE_HIGH_CONSTANT: f64 = 0.864344900642434;

/// After Open303 by Robin Schmidt (Copyright (c) 2009, www.rs-met.com), MIT license: its `calculateEnvModScalerAndOffset`,
/// the measured mapping.
/// The envelope's scale, in octaves at full, and its offset, by the cutoff in hertz and the Env amount from 0 to 1, as
/// Open303 measured them: the cutoff's place between the lowest and highest nominal cutoffs blends two lines.
pub fn envelope_mapping(cutoff: f64, amount: f64) -> (f64, f64) {
    let place = ((cutoff / LOWEST_NOMINAL_HZ).ln() / (HIGHEST_NOMINAL_HZ / LOWEST_NOMINAL_HZ).ln()).clamp(0.0, 1.0);
    let amount = amount.clamp(0.0, 1.0);
    let low = SCALE_LOW_FACTOR * amount + SCALE_LOW_CONSTANT;
    let high = SCALE_HIGH_FACTOR * amount + SCALE_HIGH_CONSTANT;
    let scale = (1.0 - place) * low + place * high;
    let offset = OFFSET_FACTOR * place + OFFSET_CONSTANT;
    (scale, offset)
}

/// After Open303 by Robin Schmidt (Copyright (c) 2009, www.rs-met.com), MIT license: its `BiquadFilter` in BANDREJECT mode.
/// A band-reject biquad by its centre and its width in octaves, as Open303 designs its notch.
fn band_reject(centre: f64, octaves: f64, rate: f64) -> Biquad {
    let w = TAU * centre / rate;
    let (sine, cosine) = w.sin_cos();
    let alpha = sine * (HALF * OCTAVE.ln() * octaves * w / sine).sinh();
    let scale = 1.0 / (1.0 + alpha);
    Biquad {
        b0: scale,
        b1: -TWICE * cosine * scale,
        b2: scale,
        a1: -TWICE * cosine * scale,
        a2: (1.0 - alpha) * scale,
        s1: 0.0,
        s2: 0.0,
    }
}

/// What the acid filter keeps from sample to sample: its four stages, its feedback high-pass, its coefficients, the
/// decimation's sections, the filters after it, and the last input, which the oversampled steps run up from.
#[derive(Clone, Copy, Debug)]
pub struct AcidFilterState {
    stages: [f64; STAGES],
    feedback_highpass: OnePoleHighpass,
    b0: f64,
    k: f64,
    g: f64,
    decimation: [Biquad; DECIMATION_SECTIONS],
    allpass: OnePoleAllpass,
    highpass: OnePoleHighpass,
    notch: Biquad,
    last_input: f64,
    /// Drive's curve, anti-aliased, at the fast rate.
    drive_curve: SmoothTanh,
}

impl AcidFilterState {
    /// At rest, for a sample rate.
    pub fn new(rate: f64) -> AcidFilterState {
        let fast = rate * OVERSAMPLING as f64;
        let section = Biquad::low_pass(DECIMATION_SHARE * rate, BUTTERWORTH_Q, fast);
        AcidFilterState {
            stages: [0.0; STAGES],
            feedback_highpass: OnePoleHighpass::new(FEEDBACK_HIGHPASS_HZ, fast),
            b0: 0.0,
            k: 0.0,
            g: 1.0,
            decimation: [section, section],
            allpass: OnePoleAllpass::new(AFTER_ALLPASS_HZ, rate),
            highpass: OnePoleHighpass::new(AFTER_HIGHPASS_HZ, rate),
            notch: band_reject(AFTER_NOTCH_HZ, AFTER_NOTCH_OCTAVES, rate),
            last_input: 0.0,
            drive_curve: SmoothTanh::default(),
        }
    }

    /// After Open303 by Robin Schmidt (Copyright (c) 2009, www.rs-met.com), MIT license: its `TeeBeeFilter`, the TB_303
    /// branch of `calculateCoefficientsApprox4` and its resonance skew.
    /// Work the coefficients out for a cutoff in hertz and a resonance from 0 to 1, by Open303's fitted formulas, at the
    /// oversampled rate.
    pub fn prepare(&mut self, cutoff: f64, resonance: f64, rate: f64) {
        let fast = rate * OVERSAMPLING as f64;
        let cutoff = cutoff.clamp(LOWEST_CUTOFF_HZ, HIGHEST_CUTOFF_HZ.min(HIGHEST_SHARE * fast));
        let skewed = (1.0 - (-RESONANCE_SKEW * resonance.clamp(0.0, 1.0)).exp()) / (1.0 - (-RESONANCE_SKEW).exp());
        let wc = TAU * cutoff / fast;
        let fx = wc * std::f64::consts::FRAC_1_SQRT_2 / TAU;
        // Open303's fits, in its own order: the stages' gain, and the loop's gain at full resonance as a polynomial.
        let [c0, c1, c2, c3] = STAGE_GAIN_FIT;
        self.b0 = (c0 + c1 * fx) / (1.0 + c2 * fx + c3 * fx * fx);
        let [k5, k4, k3, k2, k1, k0] = LOOP_GAIN_FIT;
        let k = fx * (fx * (fx * (fx * (fx * (fx + k5) - k4) - k3) + k2) + k1) + k0;
        let mut g = k / LOOP_GAIN_DIVISOR;
        g = (g - 1.0) * skewed + 1.0;
        g *= 1.0 + skewed;
        self.g = g;
        self.k = k * skewed;
    }

    /// After Open303 by Robin Schmidt (Copyright (c) 2009, www.rs-met.com), MIT license: the order and the sample rates of
    /// `Open303::getSample`, the filter at four times the rate, then the all-pass, high-pass and notch.
    /// One sample through the filter, pushed by Drive's curve at the fast rate: run OVERSAMPLING steps up from the last
    /// input to this one, decimate, and pass the
    /// result through the filters after it.
    #[inline]
    pub fn process(&mut self, input: f64, push: f64) -> f64 {
        let mut out = 0.0;
        for step in 1..=OVERSAMPLING {
            let share = step as f64 / OVERSAMPLING as f64;
            let mut fed = self.last_input + (input - self.last_input) * share;
            if push != 1.0 {
                fed = self.drive_curve.process(fed * push) / push.tanh();
            }
            let mut sample = self.ladder_step(fed);
            for section in &mut self.decimation {
                sample = section.process(sample);
            }
            out = sample;
        }
        self.last_input = input;
        let out = self.allpass.process(out);
        let out = self.highpass.process(out);
        self.notch.process(out)
    }

    /// After Open303 by Robin Schmidt (Copyright (c) 2009, www.rs-met.com), MIT license: its `TeeBeeFilter::getSample`, TB_303
    /// mode, which credits mystran and kunn on the KVR forum for the structure.
    /// One oversampled step of the ladder: the feedback taken from the last stage through the high-pass and subtracted
    /// from the input, then the four stages.
    #[inline]
    fn ladder_step(&mut self, input: f64) -> f64 {
        let b0 = self.b0;
        let [y1, y2, y3, y4] = &mut self.stages;
        let y0 = input - self.feedback_highpass.process(self.k * *y4);
        *y1 += TWICE * b0 * (y0 - *y1 + *y2);
        *y2 += b0 * (*y1 - TWICE * *y2 + *y3);
        *y3 += b0 * (*y2 - TWICE * *y3 + *y4);
        *y4 += b0 * (*y3 - TWICE * *y4);
        for stage in self.stages.iter_mut() {
            *stage = flushed(*stage);
        }
        TWICE * self.g * self.stages[LAST_STAGE]
    }
}
