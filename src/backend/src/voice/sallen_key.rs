// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Sallen-Key filter, after the resonant two-pole circuit of the early semi-modular monosynth: two one-pole sections and a
//! one-pole high-pass in the feedback loop, which give a two-pole slope whose resonance peaks hard and screams as it is
//! driven, its loop saturating so that it self-oscillates into a growl rather than a clean sine.
//!
//! The zero-delay-feedback model is read from sst-filters' K35Filter.h, by the Surge Synth Team, GPL-3.0-or-later,
//! itself adapted from Odin 2 by TheWaveWarden, GPL-3.0-or-later, after Will Pirkle's virtual-analog
//! design of the circuit. The implementation here is our own.

use std::f64::consts::PI;

/// The loop gain at full resonance, just past two, where the loop rings on by itself: the circuit self-oscillates at its
/// top resonance, its saturation holding the sine at about a quarter of full level. (sst-filters stops at 1.96, short of
/// oscillating; the original circuit does not.)
const MOST_LOOP_GAIN: f64 = 2.05;
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

    const RATE: f64 = 48_000.0;
    /// A quiet sine, below where the loop's saturation bends it.
    const QUIET: f64 = 0.1;

    /// The low-pass passes a low sine and cuts a high one, and at full resonance a click rings on at the cutoff.
    #[test]
    fn the_low_pass_cuts_above_its_cutoff_and_rings_at_full_resonance() {
        let cutoff = 1_000.0;
        let level = |frequency: f64, resonance: f64| {
            let mut state = SallenKeyState::default();
            state.prepare(Form::Low, cutoff, resonance, RATE);
            let samples = RATE as usize / 4;
            let mut most: f64 = 0.0;
            for place in 0..samples {
                let out = state.low(QUIET * (2.0 * PI * frequency * place as f64 / RATE).sin(), 1.0) / QUIET;
                if place > samples / 2 {
                    most = most.max(out.abs());
                }
            }
            most
        };
        let (low, high, quiet) = (100.0, 8_000.0, 0.0);
        assert!(level(low, quiet) > 0.8, "a low sine passes");
        assert!(level(high, quiet) < 0.05, "a high sine is cut");
        let mut state = SallenKeyState::default();
        state.prepare(Form::Low, cutoff, 1.0, RATE);
        let mut tail: f64 = 0.0;
        for place in 0..(RATE as usize / 10) {
            let out = state.low(if place == 0 { 1.0 } else { 0.0 }, 1.0);
            if place > RATE as usize / 20 {
                tail = tail.max(out.abs());
            }
        }
        assert!(tail > 0.001, "full resonance still rings 50 ms after a click");
    }

    /// The high-pass cuts a low sine and passes a high one.
    #[test]
    fn the_high_pass_cuts_below_its_cutoff() {
        let cutoff = 1_000.0;
        let level = |frequency: f64| {
            let mut state = SallenKeyState::default();
            state.prepare(Form::High, cutoff, 0.0, RATE);
            let samples = RATE as usize / 4;
            let mut most: f64 = 0.0;
            for place in 0..samples {
                let out = state.high(QUIET * (2.0 * PI * frequency * place as f64 / RATE).sin(), 1.0) / QUIET;
                if place > samples / 2 {
                    most = most.max(out.abs());
                }
            }
            most
        };
        assert!(level(50.0) < 0.1, "a low sine is cut");
        assert!(level(8_000.0) > 0.8, "a high sine passes");
    }
}
