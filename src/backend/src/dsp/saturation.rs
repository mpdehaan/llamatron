// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The curves several parts saturate through, and their anti-aliased forms: the log of the hyperbolic cosine, the
//! antiderivative of tanh, and a tanh averaged over each sample's span by it.

/// Two inputs closer than this are one: the antiderivative's difference over them would lose its precision, so the
/// curve is read at their middle instead.
pub const CLOSEST_INPUTS: f64 = 1e-6;

/// The log of the hyperbolic cosine, the antiderivative of tanh, written so that it never overflows.
#[inline]
pub fn log_cosh(x: f64) -> f64 {
    let size = x.abs();
    size + (-2.0 * size).exp().ln_1p() - std::f64::consts::LN_2
}

/// A tanh whose output is its average over the span from the last input to this one, by its antiderivative, so that a
/// curve pushed hard folds far less back down; what a filter's Drive runs on.
// Antiderivative anti-aliasing after Parker, Zavalishin and Le Bivic (DAFx 2016); our own implementation.
#[derive(Clone, Copy, Debug, Default)]
pub struct SmoothTanh {
    previous: f64,
}

impl SmoothTanh {
    /// The tanh's average from the last input to this one.
    #[inline]
    pub fn process(&mut self, input: f64) -> f64 {
        let span = input - self.previous;
        let out = if span.abs() < CLOSEST_INPUTS {
            ((input + self.previous) / 2.0).tanh()
        } else {
            (log_cosh(input) - log_cosh(self.previous)) / span
        };
        self.previous = input;
        out
    }
}
