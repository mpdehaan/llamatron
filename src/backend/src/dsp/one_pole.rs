// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! One-pole filters every part may use: a high-pass and an all-pass, as Open303 makes them (Robin Schmidt, Copyright (c)
//! 2009, www.rs-met.com, MIT license).

use crate::dsp::flushed;
use std::f64::consts::PI;

/// After Open303 by Robin Schmidt (Copyright (c) 2009, www.rs-met.com), MIT license: its `OnePoleFilter` in HIGHPASS mode.
/// A one-pole high-pass, as Open303 makes one: its coefficients and what it keeps.
#[derive(Clone, Copy, Default, Debug)]
pub struct OnePoleHighpass {
    gain: f64,
    pole: f64,
    last_in: f64,
    last_out: f64,
}

impl OnePoleHighpass {
    pub fn new(cutoff: f64, rate: f64) -> OnePoleHighpass {
        let pole = (-2.0 * PI * cutoff / rate).exp();
        OnePoleHighpass {
            gain: 0.5 * (1.0 + pole),
            pole,
            last_in: 0.0,
            last_out: 0.0,
        }
    }

    #[inline]
    pub fn process(&mut self, input: f64) -> f64 {
        let out = self.gain * (input - self.last_in) + self.pole * self.last_out;
        self.last_in = input;
        self.last_out = flushed(out);
        self.last_out
    }
}

/// After Open303 by Robin Schmidt (Copyright (c) 2009, www.rs-met.com), MIT license: its `OnePoleFilter` in ALLPASS mode.
/// A one-pole all-pass, which moves the phase of the low end and leaves its level.
#[derive(Clone, Copy, Default, Debug)]
pub struct OnePoleAllpass {
    coefficient: f64,
    last_in: f64,
    last_out: f64,
}

impl OnePoleAllpass {
    pub fn new(cutoff: f64, rate: f64) -> OnePoleAllpass {
        let t = (PI * cutoff / rate).tan();
        OnePoleAllpass {
            coefficient: (t - 1.0) / (t + 1.0),
            last_in: 0.0,
            last_out: 0.0,
        }
    }

    #[inline]
    pub fn process(&mut self, input: f64) -> f64 {
        let out = self.coefficient * input + self.last_in - self.coefficient * self.last_out;
        self.last_in = input;
        self.last_out = flushed(out);
        self.last_out
    }
}
