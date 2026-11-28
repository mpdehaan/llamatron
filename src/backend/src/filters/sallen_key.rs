// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Sallen-Key filter, a resonant two-pole circuit of the early semi-modular monosynths: two one-pole sections and a
//! one-pole high-pass in the feedback loop, which give a two-pole slope whose resonance peaks hard and screams as it is
//! driven, its loop saturating harder as the resonance nears the top, so that it growls rather than sings, stopping just
//! short of self-oscillation.
//!
//! The zero-delay-feedback model is read from sst-filters' K35Filter.h, by the Surge Synth Team, GPL-3.0-or-later,
//! itself adapted from Odin 2 by TheWaveWarden, GPL-3.0-or-later, after Will Pirkle's virtual-analog
//! design of the circuit. The implementation here is our own.

use std::f64::consts::PI;

/// The loop gain at full resonance, as sst-filters has it: just short of two, where the loop would ring on by itself, so
/// that full resonance rings long after a note but never holds a tone with no input to stop it.
const MOST_LOOP_GAIN: f64 = 1.96;
/// How much harder the loop's saturation is pushed at full resonance than at none: the peak at the cutoff, tall near the
/// top, is squashed and grows the circuit's growl as the resonance rises, as the driven circuit screams near oscillation.
const EDGE_PUSH: f64 = 3.0;
/// The power the edge comes in by over the resonance, its cube.
const EDGE_CURVE: i32 = 3;
/// The least loop gain, so that the output, divided by it, stays finite.
const LEAST_LOOP_GAIN: f64 = 0.01;

/// The low-pass and high-pass forms of the circuit.
#[derive(Clone, Copy, PartialEq, Eq, Debug, Default)]
pub enum Form {
    #[default]
    Low,
    High,
}

/// The circuit's coefficients at one cutoff and resonance, and its three one-pole sections' states.
#[derive(Clone, Copy, Debug, Default)]
pub struct SallenKeyState {
    share: f64,
    low_beta: f64,
    high_beta: f64,
    loop_gain: f64,
    edge: f64,
    alpha: f64,
    first: f64,
    feedback_high: f64,
    second: f64,
}

/// One trapezoidal one-pole low-pass section: its output, its state carried for the next sample.
// After sst-filters' K35Filter.h doLpf (Surge Synth Team, GPL-3.0-or-later).
#[inline]
fn low_pass(share: f64, input: f64, state: &mut f64) -> f64 {
    let moved = (input - *state) * share;
    let out = moved + *state;
    *state = moved + out;
    out
}

/// The matching one-pole high-pass: what the low-pass leaves out.
#[inline]
fn high_pass(share: f64, input: f64, state: &mut f64) -> f64 {
    input - low_pass(share, input, state)
}

impl SallenKeyState {
    /// Work out the coefficients for a cutoff in hertz and a resonance from 0 to 1 at a sample rate.
    // After sst-filters' K35Filter.h makeCoefficients (Surge Synth Team, GPL-3.0-or-later), from Odin 2
    // (TheWaveWarden, GPL-3.0-or-later).
    pub fn prepare(&mut self, form: Form, cutoff: f64, resonance: f64, rate: f64) {
        let g = (PI * cutoff / rate).tan();
        let share = g / (1.0 + g);
        let loop_gain = (resonance * MOST_LOOP_GAIN).clamp(LEAST_LOOP_GAIN, MOST_LOOP_GAIN);
        self.share = share;
        self.loop_gain = loop_gain;
        // Cubed, so the edge stays out of the way through the middle of the range and comes in over its top third.
        self.edge = 1.0 + EDGE_PUSH * resonance.clamp(0.0, 1.0).powi(EDGE_CURVE);
        match form {
            Form::Low => {
                self.low_beta = (loop_gain - loop_gain * share) / (1.0 + g);
                self.high_beta = -1.0 / (1.0 + g);
            }
            Form::High => {
                self.low_beta = 1.0 / (1.0 + g);
                self.high_beta = -share / (1.0 + g);
            }
        }
        self.alpha = 1.0 / (1.0 - loop_gain * share + loop_gain * share * share);
    }

    /// One sample through the low-pass form, its loop saturated by `push`, at least 1.
    // After sst-filters' K35Filter.h process_lp (Surge Synth Team, GPL-3.0-or-later).
    #[inline]
    pub fn low(&mut self, input: f64, push: f64) -> f64 {
        let share = self.share;
        let first = low_pass(share, input, &mut self.first);
        let fed_back = self.low_beta * self.second + self.high_beta * self.feedback_high;
        let solved = self.alpha * (first + fed_back);
        let push = push * self.edge;
        let saturated = (solved * push).tanh() / push;
        let out = self.loop_gain * low_pass(share, saturated, &mut self.second);
        high_pass(share, out, &mut self.feedback_high);
        out / self.loop_gain
    }

    /// One sample through the high-pass form, the loop's output saturated by `push`, at least 1.
    // After sst-filters' K35Filter.h process_hp (Surge Synth Team, GPL-3.0-or-later).
    #[inline]
    pub fn high(&mut self, input: f64, push: f64) -> f64 {
        let share = self.share;
        let first = high_pass(share, input, &mut self.feedback_high);
        let fed_back = self.high_beta * self.second + self.low_beta * self.first;
        let solved = self.alpha * (first + fed_back);
        let clean = self.loop_gain * solved;
        let push = push * self.edge;
        let out = (clean * push).tanh() / push;
        let passed = high_pass(share, out, &mut self.second);
        low_pass(share, passed, &mut self.first);
        out / self.loop_gain
    }

    /// The sections' states flushed of values too small to matter, so that silence costs no denormal arithmetic.
    pub fn flush(&mut self, flushed: fn(f64) -> f64) {
        self.first = flushed(self.first);
        self.second = flushed(self.second);
        self.feedback_high = flushed(self.feedback_high);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    use crate::dsp::testing::{sine, EIGHTH_SECOND, QUARTER_SECOND, RATE};

    /// A quiet sine, below where the loop's saturation bends it.
    const QUIET: f64 = 0.1;
    /// The cutoff the tests set, a sine well under it and one well over it, in hertz; and the level a passed sine keeps
    /// at least.
    const CUTOFF: f64 = 1_000.0;
    const LOW_HERTZ: f64 = 100.0;
    const HIGH_HERTZ: f64 = 8_000.0;
    const PASSED: f64 = 0.8;

    /// The loudest a quiet sine comes out of a form of the filter at a resonance, against its own level, over the second
    /// half of a quarter second, once the filter has settled.
    fn settled_level(form: Form, frequency: f64, resonance: f64) -> f64 {
        let mut state = SallenKeyState::default();
        state.prepare(form, CUTOFF, resonance, RATE);
        let mut most: f64 = 0.0;
        for place in 0..QUARTER_SECOND {
            let input = sine(frequency, QUIET, place);
            let out = match form {
                Form::Low => state.low(input, 1.0),
                Form::High => state.high(input, 1.0),
            } / QUIET;
            if place > EIGHTH_SECOND {
                most = most.max(out.abs());
            }
        }
        most
    }

    /// The low-pass passes a low sine and cuts a high one, and at full resonance a click rings long but dies away.
    #[test]
    fn the_low_pass_cuts_above_its_cutoff_and_rings_without_oscillating() {
        let (no_resonance, cut) = (0.0, 0.05);
        assert!(settled_level(Form::Low, LOW_HERTZ, no_resonance) > PASSED, "a low sine passes");
        assert!(settled_level(Form::Low, HIGH_HERTZ, no_resonance) < cut, "a high sine is cut");
        let ringing = |from: f64, to: f64| {
            let mut state = SallenKeyState::default();
            state.prepare(Form::Low, CUTOFF, 1.0, RATE);
            let mut most: f64 = 0.0;
            for place in 0..(RATE * to) as usize {
                let out = state.low(if place == 0 { 1.0 } else { 0.0 }, 1.0);
                if place as f64 > RATE * from {
                    most = most.max(out.abs());
                }
            }
            most
        };
        let (soon, later, long_after, last_tenth) = (0.01, 0.02, 1.0, 0.9);
        let (still_ringing, silent) = (0.001, 1e-6);
        assert!(ringing(soon, later) > still_ringing, "full resonance still rings 10 ms after a click");
        assert!(ringing(last_tenth, long_after) < silent, "and is silent a second later");
    }

    /// The high-pass cuts a low sine and passes a high one.
    #[test]
    fn the_high_pass_cuts_below_its_cutoff() {
        let (lowest_hertz, no_resonance, cut) = (50.0, 0.0, 0.1);
        assert!(settled_level(Form::High, lowest_hertz, no_resonance) < cut, "a low sine is cut");
        assert!(settled_level(Form::High, HIGH_HERTZ, no_resonance) > PASSED, "a high sine passes");
    }
}
